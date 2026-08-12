"""Compose independently verified W5 and K6 abstract-first campaigns.

The two child campaigns already contain their own preregistration, owner-bound
planner execution, nine-path accounting, and physical output closure.  This
module preregisters their exact identities before invoking either expensive
producer-free verifier, retains one row per structural context, and closes a
two-occurrence construction campaign.

No model is transferred between W5 and K6.  Each recovered query-neutral model
serves only its own fresh multi-step query.  The aggregate therefore certifies
the shared *strategy* -- certificate-gated local recovery followed by zero-
ground abstract reuse -- without claiming a cross-structural model, automatic
coordinate-language invention, an official Gate, or scalar economics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
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
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.134"
PROFILE_KEY = "construction_k7_heldout_cross_structural_campaign_v1"

PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
)
CHILD_ROW_DOMAIN = CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CHILD_ROW_V1_DOMAIN
CLOSURE_DOMAIN = CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CLOSURE_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {PREREGISTRATION_DOMAIN, CHILD_ROW_DOMAIN, CLOSURE_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("cross-structural campaign domains are not central")

PREREGISTRATION_FILENAME = "0001_PREREGISTRATION.json"
W5_ROW_FILENAME = "0002_W5_CHILD_ROW.json"
K6_ROW_FILENAME = "0003_K6_CHILD_ROW.json"
CLOSURE_FILENAME = "0004_CAMPAIGN_CLOSURE.json"
EXPECTED_FILENAMES = (
    PREREGISTRATION_FILENAME,
    W5_ROW_FILENAME,
    K6_ROW_FILENAME,
    CLOSURE_FILENAME,
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


class ConstructionK7HeldoutCrossStructuralCampaignV1Error(RuntimeError):
    """A child identity, structural join, denominator, or commit changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutCrossStructuralCampaignV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCrossStructuralCampaignV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} must be canonical bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCrossStructuralCampaignV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _read_child_id(directory: Path, filename: str, id_field: str) -> str:
    target = directory / filename
    if target.is_symlink() or not target.is_file():
        _fail(f"child campaign {filename} is absent or non-regular")
    document = _canonical_document(target.read_bytes(), f"child campaign {filename}")
    return _cid(document.get(id_field), f"child campaign {id_field}")


@dataclass(frozen=True, slots=True)
class HeldoutCrossStructuralChildSpecV1:
    family_key: str
    target_context_key: str
    target_vertex_count: int
    reuse_result_id: str
    reuse_bytes_sha256: str
    reuse_byte_count: int
    child_campaign_preregistration_id: str
    child_campaign_closure_id: str

    def __post_init__(self) -> None:
        expected = _FAMILY_SPECS.get(self.family_key)
        if (
            expected is None
            or (self.target_context_key, self.target_vertex_count) != expected[:2]
            or type(self.reuse_byte_count) is not int
            or self.reuse_byte_count <= 0
        ):
            _fail("cross-structural child spec is not exactly registered")
        for value, label in (
            (self.reuse_result_id, "child reuse result"),
            (self.reuse_bytes_sha256, "child reuse bytes digest"),
            (self.child_campaign_preregistration_id, "child preregistration"),
            (self.child_campaign_closure_id, "child closure"),
        ):
            _cid(value, label)

    def to_document(self) -> dict[str, Any]:
        return {
            "family_key": self.family_key,
            "source_vertex_counts": [4],
            "target_context_key": self.target_context_key,
            "target_vertex_count": self.target_vertex_count,
            "reuse_result_id": self.reuse_result_id,
            "reuse_bytes_sha256": self.reuse_bytes_sha256,
            "reuse_byte_count": self.reuse_byte_count,
            "child_campaign_preregistration_id": (
                self.child_campaign_preregistration_id
            ),
            "child_campaign_closure_id": self.child_campaign_closure_id,
            "expected_route_kind": "ABSTRACT_ONLY_CERTIFICATE",
            "expected_terminal_class": "PLAN_CERTIFICATE",
            "expected_terminal_code": "ABSTRACT_CERTIFIED",
        }


@dataclass(frozen=True, slots=True)
class HeldoutCrossStructuralCampaignPreregistrationV1:
    child_specs: tuple[HeldoutCrossStructuralChildSpecV1, ...]

    def __post_init__(self) -> None:
        specs = tuple(self.child_specs)
        object.__setattr__(self, "child_specs", specs)
        if (
            len(specs) != 2
            or tuple(item.family_key for item in specs) != ("W5", "K6")
            or len({item.target_context_key for item in specs}) != 2
            or len({item.target_vertex_count for item in specs}) != 2
            or len({item.reuse_result_id for item in specs}) != 2
        ):
            _fail("cross-structural preregistration children changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_cross_structural_campaign_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "ordered_child_specs": [item.to_document() for item in self.child_specs],
            "registered_structural_context_count": 2,
            "registered_logical_occurrence_count": 2,
            "preregistration_committed_before_child_independent_replay": True,
            "child_operational_execution_preexists_this_aggregate": True,
            "denominator_row_deletion_allowed": False,
            "cross_structural_model_transfer_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def preregistration_id(self) -> str:
        return content_id(PREREGISTRATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_preregistration_id": self.preregistration_id,
        }


def _child_spec(
    family_key: str,
    reuse_bytes: bytes,
    campaign_directory: Path,
) -> HeldoutCrossStructuralChildSpecV1:
    context_key, vertex_count, reuse_schema, _source_schema = _FAMILY_SPECS[family_key]
    document = _canonical_document(reuse_bytes, f"{family_key} reuse result")
    if document.get("schema") != reuse_schema:
        _fail(f"{family_key} reuse result schema changed")
    reuse_result_id = _cid(document.get("result_id"), f"{family_key} reuse result")
    return HeldoutCrossStructuralChildSpecV1(
        family_key,
        context_key,
        vertex_count,
        reuse_result_id,
        hashlib.sha256(reuse_bytes).hexdigest(),
        len(reuse_bytes),
        _read_child_id(
            campaign_directory,
            "0001_PREREGISTRATION.json",
            "campaign_preregistration_id",
        ),
        _read_child_id(
            campaign_directory,
            "0003_CAMPAIGN_CLOSURE.json",
            "campaign_closure_id",
        ),
    )


def _structural_facts(
    family_key: str,
    reuse_document: Mapping[str, Any],
) -> dict[str, Any]:
    context_key, vertex_count, reuse_schema, source_schema = _FAMILY_SPECS[family_key]
    if reuse_document.get("schema") != reuse_schema:
        _fail(f"{family_key} reuse schema changed after verification")
    source = reuse_document.get("source_result")
    query = reuse_document.get("query")
    plan = reuse_document.get("plan")
    model = reuse_document.get("final_quotient_model")
    if not all(type(item) is dict for item in (source, query, plan, model)):
        _fail(f"{family_key} reuse structural evidence is incomplete")
    preregistration = source.get("preregistration")
    if type(preregistration) is not dict:
        _fail(f"{family_key} source preregistration is absent")
    source_overlay_id = _cid(
        reuse_document.get("source_overlay_id"), f"{family_key} source overlay"
    )
    source_result_id = _cid(
        reuse_document.get("source_result_id"), f"{family_key} source result"
    )
    query_id = _cid(reuse_document.get("query_id"), f"{family_key} query")
    plan_id = _cid(reuse_document.get("plan_id"), f"{family_key} plan")
    model_id = _cid(query.get("quotient_model_id"), f"{family_key} model")
    audit_id = _cid(
        reuse_document.get("replanned_audit_id"), f"{family_key} audit"
    )
    expected_fresh_zero_fields = (
        "fresh_occurrence_new_ground_draw_count",
        "fresh_occurrence_observer_call_count",
        "fresh_occurrence_ground_solver_invocations",
        "fresh_occurrence_evaluation_exact_kernel_calls",
    )
    if (
        source.get("schema") != source_schema
        or source.get("result_id") != source_result_id
        or source.get("target_vertex_count") != vertex_count
        or source.get("source_vertex_counts") != [4]
        or preregistration.get("target_context_key") != context_key
        or source.get("target_context_id") != query.get("context_id")
        or source.get("final_overlay_id") != source_overlay_id
        or source.get("final_quotient_model_id") != model_id
        or model.get("model_id") != model_id
        or query.get("source_result_id") != source_result_id
        or query.get("source_overlay_id") != source_overlay_id
        or query.get("query_id") != query_id
        or plan.get("query_id") != query_id
        or plan.get("plan_id") != plan_id
        or plan.get("replanned_audit_id") != audit_id
        or plan.get("audit_status") != "CERTIFIED"
        or source.get("multi_step_plan_formed_in_abstract_model") is not True
        or source.get("local_ground_restoration_only_after_certificate_failure")
        is not True
        or source.get("query_neutral_overlay_reusable") is not True
        or reuse_document.get("fresh_occurrence_directly_abstract_certified")
        is not True
        or reuse_document.get("certificate_failure_triggered_local_recovery")
        is not False
        or reuse_document.get(
            "source_local_recovery_reused_as_query_neutral_overlay"
        )
        is not True
        or reuse_document.get("fresh_occurrence_abstract_planner_invocations") != 1
        or any(reuse_document.get(key) != 0 for key in expected_fresh_zero_fields)
        or (
            family_key == "K6"
            and reuse_document.get("fresh_occurrence_model_build_invocations") != 0
        )
    ):
        _fail(f"{family_key} abstract-first structural chain changed")
    changed_row_count = source.get("changed_row_count")
    incremental_draw_count = source.get("incremental_local_ground_draw_count")
    if (
        type(changed_row_count) is not int
        or changed_row_count <= 0
        or type(incremental_draw_count) is not int
        or incremental_draw_count <= 0
        or (family_key == "W5" and (changed_row_count, incremental_draw_count) != (2, 4096))
        or (family_key == "K6" and (changed_row_count, incremental_draw_count) != (1, 8192))
    ):
        _fail(f"{family_key} registered local recovery cardinality changed")
    return {
        "source_result_id": source_result_id,
        "source_overlay_id": source_overlay_id,
        "target_context_id": _cid(
            source.get("target_context_id"), f"{family_key} target context"
        ),
        "quotient_model_id": model_id,
        "query_id": query_id,
        "plan_id": plan_id,
        "audit_id": audit_id,
        "changed_row_count": changed_row_count,
        "incremental_local_ground_draw_count": incremental_draw_count,
    }


@dataclass(frozen=True, slots=True)
class HeldoutCrossStructuralCampaignChildRowV1:
    preregistration_id: str
    spec: HeldoutCrossStructuralChildSpecV1
    child_verification_bytes: bytes = field(repr=False)
    source_result_id: str
    source_overlay_id: str
    target_context_id: str
    quotient_model_id: str
    query_id: str
    plan_id: str
    audit_id: str
    work_vector_id: str
    comparison_vector_id: str
    comparison_values: tuple[tuple[str, int], ...]
    output_bytes: int
    changed_row_count: int
    incremental_local_ground_draw_count: int

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "cross-structural preregistration")
        for value, label in (
            (self.source_result_id, "source result"),
            (self.source_overlay_id, "source overlay"),
            (self.target_context_id, "target context"),
            (self.quotient_model_id, "quotient model"),
            (self.query_id, "fresh query"),
            (self.plan_id, "fresh plan"),
            (self.audit_id, "fresh audit"),
            (self.work_vector_id, "child WorkVector"),
            (self.comparison_vector_id, "child ComparisonVector"),
        ):
            _cid(value, label)
        verification = _canonical_document(
            self.child_verification_bytes, "child independent verification"
        )
        expected_id_field = (
            "heldout_abstract_campaign_independent_verification_id"
            if self.spec.family_key == "W5"
            else "heldout_k6_abstract_campaign_independent_verification_id"
        )
        if (
            tuple(axis for axis, _value in self.comparison_values) != SHARED_AXES
            or any(type(value) is not int or value < 0 for _axis, value in self.comparison_values)
            or type(self.output_bytes) is not int
            or self.output_bytes <= 0
            or type(self.changed_row_count) is not int
            or self.changed_row_count <= 0
            or type(self.incremental_local_ground_draw_count) is not int
            or self.incremental_local_ground_draw_count <= 0
            or verification.get(expected_id_field) is None
            or verification.get("campaign_preregistration_id")
            != self.spec.child_campaign_preregistration_id
            or verification.get("campaign_closure_id")
            != self.spec.child_campaign_closure_id
            or verification.get("work_vector_id") != self.work_vector_id
            or verification.get("comparison_vector_id") != self.comparison_vector_id
            or verification.get("io.output_bytes") != self.output_bytes
            or verification.get("valid") is not True
        ):
            _fail("cross-structural child row evidence changed")

    def _payload(self) -> dict[str, Any]:
        verification = loads_canonical_json(self.child_verification_bytes)
        return {
            "schema": "acfqp.construction_k7_heldout_cross_structural_campaign_child_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "child_spec": self.spec.to_document(),
            "child_independent_verification": verification,
            "source_result_id": self.source_result_id,
            "source_overlay_id": self.source_overlay_id,
            "target_context_id": self.target_context_id,
            "quotient_model_id": self.quotient_model_id,
            "query_id": self.query_id,
            "plan_id": self.plan_id,
            "audit_id": self.audit_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.comparison_values
            ],
            "io.output_bytes": self.output_bytes,
            "historical_source_changed_row_count": self.changed_row_count,
            "historical_source_incremental_local_ground_draw_count": (
                self.incremental_local_ground_draw_count
            ),
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

    @property
    def row_id(self) -> str:
        return content_id(CHILD_ROW_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cross_structural_child_row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class HeldoutCrossStructuralCampaignClosureV1:
    preregistration_id: str
    rows: tuple[HeldoutCrossStructuralCampaignChildRowV1, ...]
    cumulative_comparison_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "cross-structural closure preregistration")
        rows = tuple(self.rows)
        object.__setattr__(self, "rows", rows)
        if (
            len(rows) != 2
            or tuple(row.spec.family_key for row in rows) != ("W5", "K6")
            or any(row.preregistration_id != self.preregistration_id for row in rows)
            or tuple(axis for axis, _value in self.cumulative_comparison_values)
            != SHARED_AXES
            or any(
                type(value) is not int or value < 0
                for _axis, value in self.cumulative_comparison_values
            )
        ):
            _fail("cross-structural closure rows or vector changed")
        expected = tuple(
            (
                axis,
                sum(dict(row.comparison_values)[axis] for row in rows),
            )
            for axis in SHARED_AXES
        )
        if self.cumulative_comparison_values != expected:
            _fail("cross-structural cumulative comparison vector changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_cross_structural_campaign_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "ordered_child_row_ids": [row.row_id for row in self.rows],
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
                {"axis": axis, "value": value}
                for axis, value in self.cumulative_comparison_values
            ],
            "distinct_source_result_count": len(
                {row.source_result_id for row in self.rows}
            ),
            "distinct_source_overlay_count": len(
                {row.source_overlay_id for row in self.rows}
            ),
            "distinct_quotient_model_count": len(
                {row.quotient_model_id for row in self.rows}
            ),
            "distinct_fresh_query_count": len({row.query_id for row in self.rows}),
            "distinct_fresh_plan_count": len({row.plan_id for row in self.rows}),
            "historical_source_changed_row_count": sum(
                row.changed_row_count for row in self.rows
            ),
            "historical_source_incremental_local_ground_draw_count": sum(
                row.incremental_local_ground_draw_count for row in self.rows
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

    @property
    def closure_id(self) -> str:
        return content_id(CLOSURE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_closure_id": self.closure_id}


@dataclass(frozen=True, slots=True)
class HeldoutCrossStructuralCampaignFileCommitV1:
    filename: str
    byte_count: int
    bytes_sha256: str

    def __post_init__(self) -> None:
        if (
            self.filename not in EXPECTED_FILENAMES
            or type(self.byte_count) is not int
            or self.byte_count <= 0
        ):
            _fail("cross-structural file commit changed")
        _cid(self.bytes_sha256, "cross-structural file digest")

    def to_document(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "byte_count": self.byte_count,
            "bytes_sha256": self.bytes_sha256,
            "regular_file": True,
            "file_fsync_completed": True,
        }


@dataclass(frozen=True, slots=True)
class HeldoutCrossStructuralCampaignResultV1:
    preregistration: HeldoutCrossStructuralCampaignPreregistrationV1
    rows: tuple[HeldoutCrossStructuralCampaignChildRowV1, ...]
    closure: HeldoutCrossStructuralCampaignClosureV1
    file_commits: tuple[HeldoutCrossStructuralCampaignFileCommitV1, ...]

    def __post_init__(self) -> None:
        rows = tuple(self.rows)
        commits = tuple(self.file_commits)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "file_commits", commits)
        if (
            type(self.preregistration)
            is not HeldoutCrossStructuralCampaignPreregistrationV1
            or len(rows) != 2
            or self.closure.rows != rows
            or self.closure.preregistration_id
            != self.preregistration.preregistration_id
            or tuple(row.filename for row in commits) != EXPECTED_FILENAMES
        ):
            _fail("cross-structural campaign result is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_cross_structural_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration.preregistration_id,
            "ordered_child_row_ids": [row.row_id for row in self.rows],
            "campaign_closure_id": self.closure.closure_id,
            "campaign_file_commits": [row.to_document() for row in self.file_commits],
            "registered_structural_context_count": 2,
            "registered_logical_occurrence_count": 2,
            "plan_certificate_count": 2,
            "noncertificate_count": 0,
            "cross_structural_strategy_evidence_present": True,
            "cross_structural_model_transfer_attempted": False,
            "producer_free_aggregate_verification_present": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return content_id(RESULT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cross_structural_campaign_result_id": self.result_id,
        }


def _write_file(
    directory: Path,
    filename: str,
    document: Mapping[str, Any],
) -> HeldoutCrossStructuralCampaignFileCommitV1:
    raw = canonical_json_bytes(document)
    target = directory / filename
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail("cross-structural file write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    info = target.stat()
    if (
        target.is_symlink()
        or not target.is_file()
        or stat.S_IMODE(info.st_mode) & 0o177
        or info.st_size != len(raw)
    ):
        _fail("cross-structural file identity changed")
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return HeldoutCrossStructuralCampaignFileCommitV1(
        filename,
        len(raw),
        hashlib.sha256(raw).hexdigest(),
    )


def _row(
    preregistration: HeldoutCrossStructuralCampaignPreregistrationV1,
    spec: HeldoutCrossStructuralChildSpecV1,
    reuse_document: Mapping[str, Any],
    verification: Any,
) -> HeldoutCrossStructuralCampaignChildRowV1:
    facts = _structural_facts(spec.family_key, reuse_document)
    return HeldoutCrossStructuralCampaignChildRowV1(
        preregistration.preregistration_id,
        spec,
        canonical_json_bytes(verification.to_document()),
        facts["source_result_id"],
        facts["source_overlay_id"],
        facts["target_context_id"],
        facts["quotient_model_id"],
        facts["query_id"],
        facts["plan_id"],
        facts["audit_id"],
        verification.work_vector_id,
        verification.comparison_vector_id,
        verification.comparison_values,
        verification.output_bytes,
        facts["changed_row_count"],
        facts["incremental_local_ground_draw_count"],
    )


def _cumulative(
    rows: tuple[HeldoutCrossStructuralCampaignChildRowV1, ...],
) -> tuple[tuple[str, int], ...]:
    return tuple(
        (axis, sum(dict(row.comparison_values)[axis] for row in rows))
        for axis in SHARED_AXES
    )


def run_heldout_cross_structural_campaign_v1(
    *,
    w5_reuse_result_bytes: bytes,
    w5_campaign_directory: str | Path,
    k6_reuse_result_bytes: bytes,
    k6_campaign_directory: str | Path,
    campaign_directory: str | Path,
) -> HeldoutCrossStructuralCampaignResultV1:
    """Preregister, replay, and retain one W5 and one K6 child campaign."""

    w5_root = Path(w5_campaign_directory)
    k6_root = Path(k6_campaign_directory)
    output = Path(campaign_directory)
    if output.exists():
        _fail("cross-structural campaign directory must be absent")
    specs = (
        _child_spec("W5", w5_reuse_result_bytes, w5_root),
        _child_spec("K6", k6_reuse_result_bytes, k6_root),
    )
    preregistration = HeldoutCrossStructuralCampaignPreregistrationV1(specs)
    output.mkdir(mode=0o700, parents=False)
    commits = [
        _write_file(
            output,
            PREREGISTRATION_FILENAME,
            preregistration.to_document(),
        )
    ]
    w5_verification = w5_verifier_v1.verify_heldout_abstract_campaign_directory_bytes_v1(
        reuse_result_bytes=w5_reuse_result_bytes,
        campaign_directory=w5_root,
        expected_preregistration_id=specs[0].child_campaign_preregistration_id,
        expected_closure_id=specs[0].child_campaign_closure_id,
    )
    k6_verification = k6_verifier_v1.verify_heldout_k6_abstract_campaign_directory_bytes_v1(
        reuse_result_bytes=k6_reuse_result_bytes,
        campaign_directory=k6_root,
        expected_preregistration_id=specs[1].child_campaign_preregistration_id,
        expected_closure_id=specs[1].child_campaign_closure_id,
    )
    rows = (
        _row(
            preregistration,
            specs[0],
            _canonical_document(w5_reuse_result_bytes, "W5 reuse result"),
            w5_verification,
        ),
        _row(
            preregistration,
            specs[1],
            _canonical_document(k6_reuse_result_bytes, "K6 reuse result"),
            k6_verification,
        ),
    )
    if (
        len({row.source_result_id for row in rows}) != 2
        or len({row.source_overlay_id for row in rows}) != 2
        or len({row.target_context_id for row in rows}) != 2
        or len({row.quotient_model_id for row in rows}) != 2
        or len({row.query_id for row in rows}) != 2
        or len({row.plan_id for row in rows}) != 2
    ):
        _fail("W5 and K6 identities were crossed or collapsed")
    commits.extend(
        (
            _write_file(output, W5_ROW_FILENAME, rows[0].to_document()),
            _write_file(output, K6_ROW_FILENAME, rows[1].to_document()),
        )
    )
    closure = HeldoutCrossStructuralCampaignClosureV1(
        preregistration.preregistration_id,
        rows,
        _cumulative(rows),
    )
    commits.append(_write_file(output, CLOSURE_FILENAME, closure.to_document()))
    return verify_heldout_cross_structural_campaign_v1(
        HeldoutCrossStructuralCampaignResultV1(
            preregistration,
            rows,
            closure,
            tuple(commits),
        )
    )


def verify_heldout_cross_structural_campaign_v1(
    result: HeldoutCrossStructuralCampaignResultV1,
) -> HeldoutCrossStructuralCampaignResultV1:
    """Replay the aggregate graph without rerunning either child verifier."""

    if type(result) is not HeldoutCrossStructuralCampaignResultV1:
        _fail("cross-structural verifier rejects foreign values")
    expected_preregistration = HeldoutCrossStructuralCampaignPreregistrationV1(
        result.preregistration.child_specs
    )
    expected_rows = tuple(
        HeldoutCrossStructuralCampaignChildRowV1(
            row.preregistration_id,
            row.spec,
            row.child_verification_bytes,
            row.source_result_id,
            row.source_overlay_id,
            row.target_context_id,
            row.quotient_model_id,
            row.query_id,
            row.plan_id,
            row.audit_id,
            row.work_vector_id,
            row.comparison_vector_id,
            row.comparison_values,
            row.output_bytes,
            row.changed_row_count,
            row.incremental_local_ground_draw_count,
        )
        for row in result.rows
    )
    expected_closure = HeldoutCrossStructuralCampaignClosureV1(
        expected_preregistration.preregistration_id,
        expected_rows,
        _cumulative(expected_rows),
    )
    documents = (
        expected_preregistration.to_document(),
        expected_rows[0].to_document(),
        expected_rows[1].to_document(),
        expected_closure.to_document(),
    )
    expected_commits = tuple(
        HeldoutCrossStructuralCampaignFileCommitV1(
            filename,
            len(raw := canonical_json_bytes(document)),
            hashlib.sha256(raw).hexdigest(),
        )
        for filename, document in zip(EXPECTED_FILENAMES, documents)
    )
    if (
        result.preregistration != expected_preregistration
        or result.rows != expected_rows
        or result.closure != expected_closure
        or result.file_commits != expected_commits
    ):
        _fail("cross-structural campaign differs from exact aggregate replay")
    result.result_id
    return result


__all__ = (
    "ConstructionK7HeldoutCrossStructuralCampaignV1Error",
    "EXPECTED_FILENAMES",
    "HeldoutCrossStructuralCampaignChildRowV1",
    "HeldoutCrossStructuralCampaignClosureV1",
    "HeldoutCrossStructuralCampaignFileCommitV1",
    "HeldoutCrossStructuralCampaignPreregistrationV1",
    "HeldoutCrossStructuralCampaignResultV1",
    "HeldoutCrossStructuralChildSpecV1",
    "LOCAL_DOMAINS",
    "run_heldout_cross_structural_campaign_v1",
    "verify_heldout_cross_structural_campaign_v1",
)
