from __future__ import annotations

import copy
from pathlib import Path
import pickle

import pytest

from acfqp import construction_k7_domain_registry_extension_v180r12r2e as domains
from acfqp import (
    construction_k7_ten_terminal_aggregation_campaign_accounting_v180r12r2
    as accounting,
)


PROTOCOL_ID = "a" * 64
AUTHORIZATION_ID = "b" * 64
SUBJECT_ID = "c" * 64
SOURCE_IDS = tuple(f"{value:064x}" for value in range(1, 6))
VALUES = {
    "common.hash_invocations": 15,
    "common.integrity_checks": 10,
    "common.protocol_checks": 10,
    "io.mounted_bytes_peak": 0,
    "io.output_bytes": 12_345,
    "io.read_bytes": 15_496_039,
    "io.staged_bytes": 0,
    "memory.working_bytes_peak": 16 * 1024 * 1024 * 1024,
    "process.launches": 0,
}
ROW_FIELDS = {
    "path",
    "declared_quantity",
    "quantity_semantics",
    "authority_class",
    "actual_measurement_present",
    "counter_gate_eligible",
    "economics_gate_eligible",
}


def _declarations():
    return accounting.record_campaign_scope_structural_declarations_v180r12r2(
        aggregation_protocol_id=PROTOCOL_ID,
        execution_authorization_id=AUTHORIZATION_ID,
        subject_id=SUBJECT_ID,
        source_receipt_ids=SOURCE_IDS,
        values=VALUES,
    )


def _boundary():
    return accounting.derive_campaign_scope_structural_boundary_v180r12r2(
        _declarations()
    )


def _resign(document: dict) -> None:
    payload = dict(document)
    payload.pop("campaign_scope_structural_boundary_id", None)
    document["campaign_scope_structural_boundary_id"] = (
        domains.extension_content_id_v180r12r2e(
            domains.CONSTRUCTION_K7_CAMPAIGN_STRUCTURAL_BOUNDARY_V180R12R2E_DOMAIN,
            payload,
        )
    )


def _contains_key(value, key: str) -> bool:
    if type(value) is dict:
        return key in value or any(_contains_key(item, key) for item in value.values())
    if type(value) is list:
        return any(_contains_key(item, key) for item in value)
    return False


def test_campaign_rows_are_exact_structural_declarations_not_records() -> None:
    declarations = _declarations()
    assert len(declarations) == accounting.CAMPAIGN_STRUCTURAL_DECLARATION_COUNT == 9
    assert accounting.CAMPAIGN_SHARED_RESOURCE_RECEIPT_COUNT == 0
    documents = [row.to_document() for row in declarations]
    assert tuple(row["path"] for row in documents) == (
        accounting.CAMPAIGN_STRUCTURAL_PATHS
    )
    assert all(set(row) == ROW_FIELDS for row in documents)
    assert all(row["actual_measurement_present"] is False for row in documents)
    assert all(row["counter_gate_eligible"] is False for row in documents)
    assert all(row["economics_gate_eligible"] is False for row in documents)
    assert all("counter_record" not in key for row in documents for key in row)


def test_obligations_denominators_cap_and_absences_are_typed_exactly() -> None:
    rows = {row.to_document()["path"]: row.to_document() for row in _declarations()}
    for path, quantity in {
        "common.hash_invocations": 15,
        "common.integrity_checks": 10,
        "common.protocol_checks": 10,
    }.items():
        assert rows[path]["declared_quantity"] == quantity
        assert rows[path]["quantity_semantics"] == "DECLARED_OBLIGATION_CARDINALITY"
        assert rows[path]["authority_class"] == (
            "PRECOMMITTED_ORCHESTRATION_OBLIGATION"
        )
    assert rows["io.read_bytes"]["quantity_semantics"] == (
        "DERIVED_INPUT_BYTE_DENOMINATOR"
    )
    assert rows["io.read_bytes"]["authority_class"] == (
        "DERIVED_FROM_FROZEN_RETAINED_INPUT_BYTES"
    )
    assert rows["io.output_bytes"]["quantity_semantics"] == (
        "DERIVED_OUTPUT_BYTE_DENOMINATOR"
    )
    assert rows["io.output_bytes"]["authority_class"] == (
        "DERIVED_FROM_CANONICAL_AGGREGATE_BYTES"
    )
    working = rows["memory.working_bytes_peak"]
    assert working["declared_quantity"] == 16 * 1024 * 1024 * 1024
    assert working["quantity_semantics"] == "AUTHORIZATION_CAP_NOT_OBSERVED_PEAK"
    for path in (
        "io.mounted_bytes_peak",
        "io.staged_bytes",
        "process.launches",
    ):
        assert rows[path]["declared_quantity"] == 0
        assert rows[path]["quantity_semantics"] == (
            "DECLARED_ABSENCE_OBLIGATION_NOT_NATIVE_ZERO"
        )


def test_boundary_has_zero_actual_chain_and_only_ninety_authoritative_receipts() -> None:
    boundary = _boundary()
    document = boundary.to_document()
    assert document["schema"] == "acfqp.campaign_scope_structural_boundary.v180r12r2"
    assert document["structural_declaration_count"] == 9
    assert document["actual_counter_record_count"] == 0
    assert document["actual_work_vector_present"] is False
    assert document["actual_comparison_vector_present"] is False
    assert document["actual_projection_proof_present"] is False
    assert document["actual_native_zero_attestation_present"] is False
    assert document["campaign_scope_authoritative_receipt_count"] == 0
    assert document["authoritative_occurrence_receipt_count"] == 90
    assert document["authoritative_receipt_total"] == 90
    assert document["working_bytes_peak_measurement_present"] is False
    assert document["zero_absence_obligation_count"] == 3
    assert document["native_zero_claim_count"] == 0
    assert document["counter_gate_eligible"] is False
    assert document["economics_gate_eligible"] is False
    assert _contains_key(document, "work_vector_id") is False
    assert _contains_key(document, "comparison_vector_id") is False
    assert _contains_key(document, "projection_proof_id") is False
    assert _contains_key(document, "native_zero_attestation_id") is False


def test_boundary_is_deterministic_and_exactly_replayable() -> None:
    first = _boundary()
    second = _boundary()
    assert first.canonical_bytes == second.canonical_bytes
    assert (
        first.campaign_scope_structural_boundary_id
        == second.campaign_scope_structural_boundary_id
    )
    document = first.to_document()
    payload = dict(document)
    identity = payload.pop("campaign_scope_structural_boundary_id")
    assert identity == domains.extension_content_id_v180r12r2e(
        domains.CONSTRUCTION_K7_CAMPAIGN_STRUCTURAL_BOUNDARY_V180R12R2E_DOMAIN,
        payload,
    )
    replayed = accounting.verify_campaign_scope_structural_boundary_v180r12r2(
        first.canonical_bytes
    )
    assert replayed.canonical_bytes == first.canonical_bytes


def test_legacy_function_names_are_structural_only_compatibility_shims() -> None:
    declarations = accounting.record_campaign_scope_shared_resources_v180r12r2(
        aggregation_protocol_id=PROTOCOL_ID,
        execution_authorization_id=AUTHORIZATION_ID,
        subject_id=SUBJECT_ID,
        source_receipt_ids=SOURCE_IDS,
        values=VALUES,
    )
    assert all(
        type(row) is accounting.CampaignScopeStructuralDeclarationV180R12R2
        for row in declarations
    )
    boundary = accounting.derive_campaign_scope_accounting_v180r12r2(declarations)
    assert type(boundary) is accounting.CampaignScopeStructuralBoundaryV180R12R2
    assert (
        accounting.verify_campaign_scope_accounting_v180r12r2(
            boundary.to_document()
        ).canonical_bytes
        == boundary.canonical_bytes
    )


def test_claim_gates_remain_ineligible_and_not_run() -> None:
    document = _boundary().to_document()
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert document["scientific_success_claimed"] is False


@pytest.mark.parametrize(
    "field",
    ("actual_measurement_present", "counter_gate_eligible", "economics_gate_eligible"),
)
def test_resigned_observed_or_eligible_declaration_attack_fails(field: str) -> None:
    document = _boundary().to_document()
    document["structural_declarations"][0][field] = True
    _resign(document)
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="declaration semantics changed",
    ):
        accounting.verify_campaign_scope_structural_boundary_v180r12r2(document)


def test_resigned_native_zero_inflation_attack_fails() -> None:
    document = _boundary().to_document()
    for row in document["structural_declarations"]:
        if row["path"] in {
            "io.mounted_bytes_peak",
            "io.staged_bytes",
            "process.launches",
        }:
            row["quantity_semantics"] = "OBSERVED_NATIVE_ZERO"
    document["native_zero_claim_count"] = 3
    _resign(document)
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="declaration semantics changed",
    ):
        accounting.verify_campaign_scope_structural_boundary_v180r12r2(document)


def test_resigned_ninety_nine_authoritative_receipt_attack_fails() -> None:
    document = _boundary().to_document()
    document["campaign_scope_authoritative_receipt_count"] = 9
    document["authoritative_receipt_total"] = 99
    _resign(document)
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="changed under exact replay",
    ):
        accounting.verify_campaign_scope_structural_boundary_v180r12r2(document)


def test_unknown_fields_or_actual_work_vector_injection_fail_closed() -> None:
    document = _boundary().to_document()
    document["actual_work_vector"] = {"records": []}
    _resign(document)
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="field set mismatch",
    ):
        accounting.verify_campaign_scope_structural_boundary_v180r12r2(document)

    document = _boundary().to_document()
    document["structural_declarations"][0]["unknown"] = False
    _resign(document)
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="declaration field set mismatch",
    ):
        accounting.verify_campaign_scope_structural_boundary_v180r12r2(document)


@pytest.mark.parametrize(
    "path,value",
    (
        ("common.hash_invocations", 16),
        ("io.mounted_bytes_peak", 1),
        ("memory.working_bytes_peak", 16 * 1024 * 1024 * 1024 - 1),
    ),
)
def test_obligation_absence_or_cap_quantity_change_is_rejected(
    path: str,
    value: int,
) -> None:
    values = dict(VALUES)
    values[path] = value
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="obligation, absence, or authorization-cap quantity changed",
    ):
        accounting.record_campaign_scope_structural_declarations_v180r12r2(
            PROTOCOL_ID,
            AUTHORIZATION_ID,
            SUBJECT_ID,
            SOURCE_IDS,
            values,
        )


def test_incomplete_bool_and_mixed_context_fail_closed() -> None:
    missing = dict(VALUES)
    missing.pop("process.launches")
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="exactly cover",
    ):
        accounting.record_campaign_scope_structural_declarations_v180r12r2(
            PROTOCOL_ID,
            AUTHORIZATION_ID,
            SUBJECT_ID,
            SOURCE_IDS,
            missing,
        )
    boolean = dict(VALUES)
    boolean["io.output_bytes"] = False
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="exact integer",
    ):
        accounting.record_campaign_scope_structural_declarations_v180r12r2(
            PROTOCOL_ID,
            AUTHORIZATION_ID,
            SUBJECT_ID,
            SOURCE_IDS,
            boolean,
        )
    mixed = list(_declarations())
    other = accounting.record_campaign_scope_structural_declarations_v180r12r2(
        PROTOCOL_ID,
        AUTHORIZATION_ID,
        "d" * 64,
        SOURCE_IDS,
        VALUES,
    )
    mixed[-1] = other[-1]
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="one context",
    ):
        accounting.derive_campaign_scope_structural_boundary_v180r12r2(mixed)


def test_noncanonical_copy_pickle_and_old_actual_import_surface_fail_closed() -> None:
    boundary = _boundary()
    with pytest.raises(
        accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
        match="not canonical JSON",
    ):
        accounting.verify_campaign_scope_structural_boundary_v180r12r2(
            b" " + boundary.canonical_bytes
        )
    for artifact in (_declarations()[0], boundary):
        with pytest.raises(
            accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
            match="cannot be copied",
        ):
            copy.copy(artifact)
        with pytest.raises(
            accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
            match="cannot be deep-copied",
        ):
            copy.deepcopy(artifact)
        with pytest.raises(
            accounting.ConstructionK7TenTerminalCampaignAccountingV180R12R2Error,
            match="cannot be pickled",
        ):
            pickle.dumps(artifact)
    source = Path(accounting.__file__).read_text(encoding="utf-8")
    assert "from acfqp.accounting_v1 import" not in source
    assert "from acfqp.actual_accounting_v1 import" not in source
