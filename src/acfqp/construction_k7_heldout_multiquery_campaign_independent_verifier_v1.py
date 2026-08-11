"""Producer-free replay of the two-occurrence held-out model campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp.accounting_v1 import SHARED_AXES
from acfqp import (
    construction_k7_heldout_abstract_campaign_independent_verifier_v1
    as occurrence_verifier_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_heldout_multiquery_campaign_independent_verifier_v1"
CAMPAIGN_PROFILE_KEY = "construction_k7_heldout_multiquery_campaign_v1"
CONTRACT_VERSION = "2.0.126"
EXPECTED_OCCURRENCE_COUNT = 2

PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
)
ROW_DOMAIN = CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
CLOSURE_DOMAIN = CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_CLOSURE_V1_DOMAIN
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out multiquery verification domain is not central")


class ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error(
    RuntimeError
):
    """The physical multiquery campaign does not replay exactly."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _read(path: Path, label: str) -> dict[str, Any]:
    try:
        info = path.stat()
        raw = path.read_bytes()
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error(
            f"{label} is unreadable or noncanonical"
        ) from error
    if (
        path.is_symlink()
        or not path.is_file()
        or stat.S_IMODE(info.st_mode) & 0o177
        or type(document) is not dict
        or canonical_json_bytes(document) != raw
    ):
        _fail(f"{label} is not one private canonical object")
    return document


def _content(
    document: dict[str, Any], *, id_field: str, domain: str, label: str
) -> tuple[str, dict[str, Any]]:
    if id_field not in document:
        _fail(f"{label} content ID is absent")
    payload = dict(document)
    observed = _cid(payload.pop(id_field), f"{label} content ID")
    if content_id(domain, payload) != observed:
        _fail(f"{label} content ID mismatch")
    return observed, payload


def _row_filename(index: int) -> str:
    return f"{index + 1:04d}_OCCURRENCE_{index:04d}.json"


def _occurrence_directory(index: int) -> str:
    return f"occurrence-{index:04d}"


def _query_spec(query: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "occurrence_index": index,
        "logical_occurrence_id": query["logical_occurrence_id"],
        "occurrence_ordinal": query["occurrence_ordinal"],
        "frozen_query_id": query["query_id"],
        "expected_route_kind": "ABSTRACT_ONLY_CERTIFICATE",
        "expected_terminal_class": "PLAN_CERTIFICATE",
        "expected_terminal_code": "ABSTRACT_CERTIFIED",
    }


@dataclass(frozen=True, slots=True)
class HeldoutMultiqueryCampaignIndependentVerificationV1:
    preregistration_id: str
    occurrence_row_ids: tuple[str, str]
    occurrence_verification_ids: tuple[str, str]
    closure_id: str
    source_result_id: str
    source_overlay_id: str
    quotient_model_id: str
    cumulative_comparison_values: tuple[tuple[str, int], ...]
    output_bytes: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.preregistration_id, "campaign preregistration"),
            (self.closure_id, "campaign closure"),
            (self.source_result_id, "campaign source"),
            (self.source_overlay_id, "campaign overlay"),
            (self.quotient_model_id, "campaign model"),
        ):
            _cid(value, label)
        for value in self.occurrence_row_ids:
            _cid(value, "campaign row")
        for value in self.occurrence_verification_ids:
            _cid(value, "occurrence verification")
        if (
            len(set(self.occurrence_row_ids)) != EXPECTED_OCCURRENCE_COUNT
            or len(set(self.occurrence_verification_ids))
            != EXPECTED_OCCURRENCE_COUNT
            or tuple(axis for axis, _value in self.cumulative_comparison_values)
            != SHARED_AXES
            or type(self.output_bytes) is not int
            or self.output_bytes <= 0
        ):
            _fail("multiquery independent verification values changed")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_multiquery_campaign_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_id": self.preregistration_id,
            "ordered_occurrence_row_ids": list(self.occurrence_row_ids),
            "ordered_occurrence_verification_ids": list(
                self.occurrence_verification_ids
            ),
            "campaign_closure_id": self.closure_id,
            "source_result_id": self.source_result_id,
            "source_overlay_id": self.source_overlay_id,
            "quotient_model_id": self.quotient_model_id,
            "cumulative_comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.cumulative_comparison_values
            ],
            "io.output_bytes": self.output_bytes,
            "registered_logical_occurrence_count": EXPECTED_OCCURRENCE_COUNT,
            "closed_logical_occurrence_count": EXPECTED_OCCURRENCE_COUNT,
            "closure_denominator": EXPECTED_OCCURRENCE_COUNT,
            "certificate_coverage_denominator": EXPECTED_OCCURRENCE_COUNT,
            "future_economics_cost_denominator": EXPECTED_OCCURRENCE_COUNT,
            "plan_certificate_count": EXPECTED_OCCURRENCE_COUNT,
            "noncertificate_count": 0,
            "single_query_neutral_overlay_reused": True,
            "producer_modules_imported": False,
            "all_occurrences_independently_replayed": True,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        current = content_id(VERIFICATION_DOMAIN, self._payload())
        if current != self._verification_id:
            _fail("multiquery independent verification changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "heldout_multiquery_campaign_independent_verification_id": self.verification_id,
        }


def verify_heldout_multiquery_campaign_directory_bytes_v1(
    *,
    campaign_directory: str | Path,
    expected_preregistration_id: str,
    expected_closure_id: str,
) -> HeldoutMultiqueryCampaignIndependentVerificationV1:
    root = Path(campaign_directory)
    expected_inventory = {
        "0001_PREREGISTRATION.json",
        _row_filename(1),
        _row_filename(2),
        "0004_CAMPAIGN_CLOSURE.json",
        _occurrence_directory(1),
        _occurrence_directory(2),
    }
    if (
        root.is_symlink()
        or not root.is_dir()
        or stat.S_IMODE(root.stat().st_mode) & 0o077
        or {path.name for path in root.iterdir()} != expected_inventory
    ):
        _fail("multiquery campaign directory inventory changed")
    preregistration_document = _read(
        root / "0001_PREREGISTRATION.json", "multiquery preregistration"
    )
    row_documents = tuple(
        _read(root / _row_filename(index), f"multiquery row {index}")
        for index in range(1, EXPECTED_OCCURRENCE_COUNT + 1)
    )
    closure_document = _read(
        root / "0004_CAMPAIGN_CLOSURE.json", "multiquery closure"
    )
    # Denominator and cheap terminal claims are checked before either numerical
    # model or 202-record occurrence replay.
    if (
        preregistration_document.get("registered_logical_occurrence_count") != 2
        or preregistration_document.get("official_execution_allowed") is not False
        or any(row.get("route_kind") != "ABSTRACT_ONLY_CERTIFICATE" for row in row_documents)
        or any(row.get("terminal_code") != "ABSTRACT_CERTIFIED" for row in row_documents)
        or closure_document.get("registered_logical_occurrence_count") != 2
        or closure_document.get("closed_logical_occurrence_count") != 2
        or closure_document.get("closure_denominator") != 2
        or closure_document.get("certificate_coverage_denominator") != 2
        or closure_document.get("future_economics_cost_denominator") != 2
        or closure_document.get("plan_certificate_count") != 2
        or closure_document.get("noncertificate_count") != 0
        or closure_document.get("official_execution_allowed") is not False
    ):
        _fail("multiquery campaign cheap denominator gate changed")

    row_ids: list[str] = []
    occurrence_verifications = []
    reuse_documents: list[dict[str, Any]] = []
    for index, row_document in enumerate(row_documents, start=1):
        row_id, row_payload = _content(
            row_document,
            id_field="campaign_occurrence_row_id",
            domain=ROW_DOMAIN,
            label=f"multiquery row {index}",
        )
        try:
            reuse_document = row_payload["reuse_result"]
            bundle_document = row_payload["occurrence_accounting_bundle"]
            fixed_document = row_payload["output_bytes_fixed_point_result"]
            commit_document = row_payload["output_commit"]
        except KeyError as error:
            raise ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error(
                "multiquery portable occurrence evidence is incomplete"
            ) from error
        if any(
            type(item) is not dict
            for item in (
                reuse_document,
                bundle_document,
                fixed_document,
                commit_document,
            )
        ):
            _fail("multiquery portable occurrence evidence changed type")
        try:
            verification = occurrence_verifier_v1.verify_heldout_abstract_occurrence_directory_bytes_v1(
                reuse_result_bytes=canonical_json_bytes(reuse_document),
                occurrence_directory=root / _occurrence_directory(index),
                occurrence_bundle_document=bundle_document,
                fixed_point_result_document=fixed_document,
                output_commit_document=commit_document,
            )
        except Exception as error:
            raise ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error(
                f"multiquery occurrence {index} failed independent replay"
            ) from error
        query = reuse_document["query"]
        plan = reuse_document["plan"]
        expected_row = {
            "schema": "acfqp.construction_k7_heldout_multiquery_campaign_occurrence_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": CAMPAIGN_PROFILE_KEY,
            "campaign_preregistration_id": preregistration_document[
                "campaign_preregistration_id"
            ],
            "occurrence_index": index,
            "occurrence_id": query["logical_occurrence_id"],
            "occurrence_ordinal": query["occurrence_ordinal"],
            "frozen_query_id": query["query_id"],
            "reuse_result_id": reuse_document["result_id"],
            "fresh_plan_id": plan["plan_id"],
            "quotient_model_id": query["quotient_model_id"],
            "source_overlay_id": query["source_overlay_id"],
            "occurrence_accounting_bundle_id": verification.occurrence_bundle_id,
            "work_vector_id": verification.work_vector_id,
            "comparison_vector_id": verification.comparison_vector_id,
            "actual_projection_proof_id": verification.projection_proof_id,
            "output_commit_id": verification.output_commit_id,
            "reuse_result": reuse_document,
            "occurrence_accounting_bundle": bundle_document,
            "output_bytes_fixed_point_result": fixed_document,
            "output_commit": commit_document,
            "comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in verification.comparison_values
            ],
            "route_kind": "ABSTRACT_ONLY_CERTIFICATE",
            "terminal_class": "PLAN_CERTIFICATE",
            "terminal_code": "ABSTRACT_CERTIFIED",
            "fresh_planner_invocations": 1,
            "accounting_planner_replay_invocations": 0,
            "fresh_ground_or_observer_event_count": 0,
            "portable_occurrence_evidence_embedded": True,
            "closure_denominator_contribution": 1,
            "certificate_coverage_denominator_contribution": 1,
            "future_economics_denominator_contribution": 1,
            "plan_certificate_count_contribution": 1,
            "noncertificate_count_contribution": 0,
            "official_execution_allowed": False,
        }
        if row_payload != expected_row:
            _fail(f"multiquery row {index} differs from independent replay")
        row_ids.append(row_id)
        reuse_documents.append(reuse_document)
        occurrence_verifications.append(verification)

    first, second = reuse_documents
    if (
        canonical_json_bytes(first["source_result"])
        != canonical_json_bytes(second["source_result"])
        or canonical_json_bytes(first["final_quotient_model"])
        != canonical_json_bytes(second["final_quotient_model"])
        or canonical_json_bytes(first["threshold"])
        != canonical_json_bytes(second["threshold"])
        or first["query_id"] == second["query_id"]
        or first["plan_id"] == second["plan_id"]
        or first["replanned_audit_id"] != second["replanned_audit_id"]
    ):
        _fail("multiquery rows did not reuse one query-neutral world model")

    preregistration_id, preregistration_payload = _content(
        preregistration_document,
        id_field="campaign_preregistration_id",
        domain=PREREGISTRATION_DOMAIN,
        label="multiquery preregistration",
    )
    queries = tuple(document["query"] for document in reuse_documents)
    expected_preregistration = {
        "schema": "acfqp.construction_k7_heldout_multiquery_campaign_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": CONTRACT_VERSION,
        "profile_key": CAMPAIGN_PROFILE_KEY,
        "source_result_id": first["source_result_id"],
        "source_overlay_id": first["source_overlay_id"],
        "quotient_model_id": queries[0]["quotient_model_id"],
        "threshold_profile_id": queries[0]["threshold_profile_id"],
        "ordered_occurrence_specs": [
            _query_spec(query, index)
            for index, query in enumerate(queries, start=1)
        ],
        "registered_logical_occurrence_count": 2,
        "source_verified_before_preregistration": True,
        "all_query_specs_frozen_before_preregistration": True,
        "fresh_query_planner_invocations_before_preregistration": 0,
        "one_owner_accounted_planner_call_required_per_occurrence": True,
        "denominator_row_deletion_allowed": False,
        "official_execution_allowed": False,
    }
    if (
        preregistration_payload != expected_preregistration
        or preregistration_id
        != _cid(expected_preregistration_id, "expected preregistration")
    ):
        _fail("multiquery preregistration differs from independent replay")

    cumulative = tuple(
        (
            axis,
            sum(
                dict(verification.comparison_values)[axis]
                for verification in occurrence_verifications
            ),
        )
        for axis in SHARED_AXES
    )
    closure_id, closure_payload = _content(
        closure_document,
        id_field="campaign_closure_id",
        domain=CLOSURE_DOMAIN,
        label="multiquery closure",
    )
    expected_closure = {
        "schema": "acfqp.construction_k7_heldout_multiquery_campaign_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": CONTRACT_VERSION,
        "profile_key": CAMPAIGN_PROFILE_KEY,
        "campaign_preregistration_id": preregistration_id,
        "ordered_occurrence_row_ids": row_ids,
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
        "shared_source_overlay_count": 1,
        "shared_quotient_model_count": 1,
        "fresh_query_count": 2,
        "fresh_plan_count": 2,
        "fresh_owner_accounted_planner_invocation_count": 2,
        "accounting_planner_replay_invocation_count": 0,
        "fresh_ground_or_observer_event_count": 0,
        "all_registered_occurrences_retained": True,
        "campaign_construction_closed": True,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    if (
        closure_payload != expected_closure
        or closure_id != _cid(expected_closure_id, "expected closure")
    ):
        _fail("multiquery closure differs from independent replay")
    return HeldoutMultiqueryCampaignIndependentVerificationV1(
        preregistration_id,
        (row_ids[0], row_ids[1]),
        (
            occurrence_verifications[0].verification_id,
            occurrence_verifications[1].verification_id,
        ),
        closure_id,
        first["source_result_id"],
        first["source_overlay_id"],
        queries[0]["quotient_model_id"],
        cumulative,
        sum(row.output_bytes for row in occurrence_verifications),
    )


__all__ = (
    "ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error",
    "HeldoutMultiqueryCampaignIndependentVerificationV1",
    "LOCAL_DOMAINS",
    "verify_heldout_multiquery_campaign_directory_bytes_v1",
)
