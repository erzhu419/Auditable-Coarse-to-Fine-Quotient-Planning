from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_campaign_measurement_independent_verifier_v180r12r3r2 as verifier,
)
from acfqp import construction_k7_campaign_measurement_ledger_v180r12r3r2 as ledger
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r3r2 as protocol
from acfqp import (
    construction_k7_campaign_measurement_supervisor_v180r12r3r2 as supervisor,
)
from acfqp import construction_k7_domain_registry_extension_v180r12r3r2 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r3r2e as subdomains
from acfqp.phase3e_ids import canonical_json_bytes
from tests import test_construction_k7_campaign_measurement_finalizer_v180r12r3r2 as finalizer_fixture
from tests import test_construction_k7_campaign_measurement_ledger_v180r12r3r2 as ledger_fixture


def _regular_observation(raw: bytes) -> dict:
    return {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _success_cgroup_rows(campaign_attempt_id: str) -> list[dict]:
    return [
        {
            "phase": phase,
            "applicable": True,
            "campaign_attempt_id": campaign_attempt_id,
            "root_name": f"v180r12r3r2-{campaign_attempt_id}",
            "ownership_acquired": True,
            "root_state": "ABSENT",
            "root_mode": None,
            "root_nlink": None,
            "root_device": None,
            "root_inode": None,
            "root_populated": None,
            "root_process_count": None,
            "supervisor_state": "ABSENT",
            "worker_state": "ABSENT",
            "kill_attempted": False,
            "kill_succeeded": False,
            "wait_empty_attempted": False,
            "wait_empty_succeeded": False,
            "remove_attempted": False,
            "remove_succeeded": False,
            "residual_tree_or_process_possible": False,
            "error_type": None,
            "error_message": None,
        }
        for phase in verifier.MEASUREMENT_CGROUP_OBSERVATION_PHASES
    ]


def _measurement_launch_documents(terminal) -> tuple[bytes, bytes]:
    attempt = ledger_fixture._measurement_launch_attempt_document()
    attempt_raw = canonical_json_bytes(attempt)
    artifacts = terminal.success_artifact_bytes
    origin_ns = 1_000_000_000_000_000
    hard_deadline_ns = origin_ns + 14_400 * 1_000_000_000
    campaign_deadline_ns = hard_deadline_ns - 600 * 1_000_000_000
    payload = {
        "schema": "acfqp.v180r12r3r2_prelaunch_launch_receipt.v1",
        "launch_rule_id": ledger_fixture.PRELAUNCH_LAUNCH_RULE_ID,
        "launch_attempt_id": attempt["launch_attempt_id"],
        "target": "measurement",
        "return_code": 0,
        "timed_out": False,
        "child_stdout": {
            "byte_count": 0,
            "sha256": hashlib.sha256(b"").hexdigest(),
            "retained_prefix_hex": "",
            "retained_prefix_truncated": False,
        },
        "child_stderr": {
            "byte_count": 0,
            "sha256": hashlib.sha256(b"").hexdigest(),
            "retained_prefix_hex": "",
            "retained_prefix_truncated": False,
        },
        "progress_observations": {
            "attempt": _regular_observation(attempt_raw),
            "receipt": {"presence": "ABSENT"},
            "launch_failure": {"presence": "ABSENT"},
            "runtime_cas": {"presence": "ABSENT"},
            "output_root": {"presence": "DIRECTORY", "mode": 0o700},
            "terminal": _regular_observation(terminal.canonical_bytes),
            "evidence_inventory": _regular_observation(
                artifacts["evidence_inventory"]
            ),
            "execution_closure": _regular_observation(
                artifacts["execution_closure"]
            ),
            "os_receipt": _regular_observation(artifacts["os_receipt"]),
            "ledger_closure": _regular_observation(artifacts["ledger_closure"]),
            "measurement_failure": {"presence": "ABSENT"},
            "verification": {"presence": "ABSENT"},
            "verification_failure": {"presence": "ABSENT"},
            "retained_replay": {"presence": "ABSENT"},
        },
        "same_target_identity_rerun_forbidden": True,
        "attempt_lock_preserved": True,
        "address_space_hard_cap_bytes": 16 * 1024 * 1024 * 1024,
        "wall_timeout_seconds": 14_400,
        "monotonic_origin_ns": origin_ns,
        "hard_deadline_ns": hard_deadline_ns,
        "campaign_deadline_ns": campaign_deadline_ns,
        "campaign_cleanup_grace_seconds": 600,
        "termination_grace_seconds": 10,
        "measurement_cgroup_cleanup_observations": _success_cgroup_rows(
            terminal.document["attempt_id"]
        ),
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "authorized_child_measurement_execution_attempted": True,
        "authorized_child_measurement_execution_completed": True,
        "producer_free_verification_attempted": False,
        "producer_free_verification_completed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": True,
        "failure_type": None,
        "failure_message": None,
    }
    receipt = {
        **payload,
        "launch_receipt_id": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }
    return attempt_raw, canonical_json_bytes(receipt)


def _bundle():
    inputs = finalizer_fixture._closed_inputs()
    terminal = finalizer_fixture._finalize(inputs)
    fixture = inputs["fixture"]
    state = fixture["state"]
    measurement_attempt_raw, measurement_receipt_raw = (
        _measurement_launch_documents(terminal)
    )
    arguments = {
        "campaign_evidence_inventory_bundle_bytes": (
            terminal.evidence_inventory_bundle_bytes
        ),
        "campaign_execution_closure_bytes": terminal.execution_closure_bytes,
        "campaign_os_receipt_bundle_bytes": terminal.os_receipt_bundle_bytes,
        "campaign_ledger_closure_bytes": terminal.ledger_closure_bytes,
        "measurement_launch_attempt_bytes": measurement_attempt_raw,
        "measurement_launch_receipt_bytes": measurement_receipt_raw,
        "expected_protocol_id": state.protocol_id,
        "expected_authorization_id": state.authorization_id,
        "expected_authorization_evidence_id": (
            terminal.document["authorization_evidence_id"]
        ),
        "expected_attempt_id": state.attempt_id,
        "expected_prelaunch_materialization_terminal_id": terminal.document[
            "prelaunch_materialization_terminal_id"
        ],
        "expected_prelaunch_launch_manifest_sha256": terminal.document[
            "prelaunch_launch_manifest_sha256"
        ],
        "expected_precompiled_source_bundle_sha256": terminal.document[
            "precompiled_source_bundle_sha256"
        ],
        "expected_native_zero_precompiled_source_rows": (
            ledger_fixture._precompiled_source_rows()
        ),
        "expected_prelaunch_launch_rule_id": terminal.document[
            "prelaunch_launch_rule_id"
        ],
        "expected_measurement_launch_attempt_id": terminal.document[
            "measurement_launch_attempt_id"
        ],
        "expected_subject_id": fixture["subject_id"],
        "expected_native_zero_source_manifest_id": fixture["source_manifest_id"],
        "expected_native_zero_import_inventory_id": fixture[
            "import_inventory_id"
        ],
        "expected_max_event_count": state.max_event_count,
        "expected_max_event_byte_count": state.max_event_byte_count,
        "expected_max_ledger_byte_count": state.max_ledger_byte_count,
    }
    return terminal, arguments


def _resign_closure(document: dict) -> None:
    closure = document["campaign_measurement_ledger"]
    payload = dict(closure)
    payload.pop("campaign_ledger_closure_id", None)
    closure_id = subdomains.extension_content_id_v180r12r3r2e(
        subdomains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_CLOSURE_V180R12R3R2E_DOMAIN,
        payload,
    )
    closure["campaign_ledger_closure_id"] = closure_id
    closure_bytes = canonical_json_bytes(closure)
    document["campaign_ledger_closure_id"] = closure_id
    document["campaign_ledger_closure_byte_count"] = len(closure_bytes)
    document["campaign_ledger_closure_sha256"] = hashlib.sha256(
        closure_bytes
    ).hexdigest()


def _resign_terminal(document: dict) -> bytes:
    fixed_point = 0
    for _iteration in range(32):
        document["output_bytes_fixed_point"] = fixed_point
        payload = dict(document)
        payload.pop("campaign_measurement_terminal_id", None)
        document["campaign_measurement_terminal_id"] = (
            domains.extension_content_id_v180r12r3r2(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R3R2_DOMAIN,
                payload,
            )
        )
        raw = canonical_json_bytes(document)
        if len(raw) == fixed_point:
            return raw
        fixed_point = len(raw)
    raise AssertionError("test terminal fixed point did not converge")


def _verify(raw: bytes, arguments: dict):
    return verifier.verify_campaign_measurement_terminal_independently_v180r12r3r2(
        raw,
        **arguments,
    )


def test_independent_verifier_is_the_only_counter_pass_authority() -> None:
    terminal, arguments = _bundle()
    assert terminal.document["COUNTER_COMPLETENESS_GATE"] == (
        "PENDING_INDEPENDENT_REPLAY"
    )
    result = _verify(terminal.canonical_bytes, arguments)
    document = result.document

    assert document["V180R12R3R2_CAMPAIGN_COUNTER_CLOSURE_STATUS"] == "PASS"
    assert document["COUNTER_COMPLETENESS_GATE"] == "PASS"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert document["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert document["scientific_success_claimed"] is False
    assert document["event_count"] == 625
    assert document["evidence_document_count"] == 328
    assert document["os_receipt_document_count"] == 12
    assert document["campaign_path_receipt_count"] == 9
    assert document["campaign_counter_record_count"] == 9
    assert document["combined_successor_authoritative_receipt_count"] == 99
    assert document["exact_625_event_schedule_independently_replayed"] is True
    assert document["exact_328_evidence_inventory_independently_replayed"] is True
    assert document[
        "four_separate_durable_success_artifacts_independently_replayed"
    ] is True
    assert document["exact_eight_io_transfer_graph_independently_replayed"] is True
    assert document["bounded_native_zero_attestation_independently_rederived"] is True
    assert document["native_zero_is_not_an_os_syscall_count"] is True
    assert document["open_world_absence_claimed"] is False
    assert frozenset(document) == verifier.VERIFICATION_FIELDS
    terminal_document = terminal.document
    for field_name in (
        "authorization_evidence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    ):
        assert document[field_name] == terminal_document[field_name]

    payload = dict(document)
    verification_id = payload.pop("campaign_measurement_verification_id")
    assert verification_id == domains.extension_content_id_v180r12r3r2(
        domains.CONSTRUCTION_K7_VERIFICATION_V180R12R3R2_DOMAIN,
        payload,
    )


@pytest.mark.parametrize(
    "argument_name",
    (
        "campaign_evidence_inventory_bundle_bytes",
        "campaign_execution_closure_bytes",
        "campaign_os_receipt_bundle_bytes",
        "campaign_ledger_closure_bytes",
    ),
)
def test_independent_verifier_rejects_each_separate_artifact_mutation(
    argument_name: str,
) -> None:
    terminal, arguments = _bundle()
    raw = arguments[argument_name]
    arguments[argument_name] = raw[:-1] + bytes([raw[-1] ^ 1])
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error
    ):
        _verify(terminal.canonical_bytes, arguments)


@pytest.mark.parametrize(
    "field_name",
    (
        "authorization_evidence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    ),
)
def test_independent_verifier_rejects_resigned_foreign_terminal_provenance(
    field_name: str,
) -> None:
    terminal, arguments = _bundle()
    document = copy.deepcopy(terminal.document)
    document[field_name] = "f" * 64
    raw = _resign_terminal(document)
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error,
        match="one-shot context",
    ):
        _verify(raw, arguments)


def test_independent_verifier_has_an_ast_enforced_producer_free_boundary() -> None:
    source_path = Path(verifier.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = (
        "campaign_measurement_finalizer_v180r12r3r2",
        "campaign_measurement_supervisor_v180r12r3r2",
        "campaign_measurement_worker_v180r12r3r2",
        "campaign_measurement_ledger_v180r12r3r2",
    )
    assert all(
        all(fragment not in imported_name for fragment in forbidden)
        for imported_name in imported
    )
    assert all(
        not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"open", "exec", "eval", "compile", "__import__"}
        )
        for node in ast.walk(tree)
    )


def test_independent_verifier_schema_manifest_matches_runtime_and_full_fixture() -> None:
    assert verifier.TERMINAL_FIELDS == finalizer_fixture.finalizer.TERMINAL_FIELDS
    assert verifier.EVIDENCE_INVENTORY_BUNDLE_FIELDS == (
        finalizer_fixture.finalizer.EVIDENCE_INVENTORY_BUNDLE_FIELDS
    )
    assert verifier.OS_RECEIPT_BUNDLE_FIELDS == (
        finalizer_fixture.finalizer.OS_RECEIPT_BUNDLE_FIELDS
    )
    assert verifier.SUCCESS_ARTIFACT_SCHEMA_ROWS == (
        finalizer_fixture.finalizer.SUCCESS_ARTIFACT_SCHEMA_ROWS
    )
    verifier_rows = verifier.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS
    runtime_rows = supervisor.RUNTIME_EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS
    producer_rows = (*runtime_rows, *ledger.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS)
    assert len(verifier_rows) == 18
    assert len(runtime_rows) == 10
    assert producer_rows == verifier_rows

    fixture = finalizer_fixture._runtime_shaped_fixture()
    observed = {
        schema: frozenset(document)
        for document in fixture["docs"].values()
        for schema in (document["schema"],)
    }
    assert set(observed) == {row[1] for row in verifier_rows}
    assert all(observed[schema] == fields for _, schema, _, fields in verifier_rows)
    assert verifier.SEMANTIC_RECEIPT_AUXILIARY_NAME_BY_KIND == {
        kind: name
        for kind, name, _semantics, _count
        in protocol.SEMANTIC_RECEIPT_AUXILIARY_ROWS
    }
    semantics = [
        document
        for document in fixture["docs"].values()
        if document["schema"]
        == "acfqp.campaign_semantic_operation_receipt.v180r12r3r2"
    ]
    assert len(semantics) == 297
    assert all(len(document["auxiliary_values"]) == 1 for document in semantics)
    transport_boundary = verifier.SNAPSHOT_TRANSPORT_INDEPENDENT_VERIFIER_BOUNDARY
    assert transport_boundary == {
        "ephemeral_transport_artifact_replayed": False,
        "resultant_stable_input_snapshot_receipt_count": 2,
        "resultant_snapshot_receipt_canonical_identity_replayed": True,
        "resultant_snapshot_role_byte_count_sha256_and_content_id_replayed": True,
        "transport_is_not_an_additional_measured_read": True,
        "transport_is_not_part_of_the_328_document_inventory": True,
    }
    prelaunch = protocol.prelaunch_contract_v180r12r3r2()
    assert prelaunch[
        "independent_verifier_validates_resultant_snapshot_receipts_not_ephemeral_transport_attachment"
    ] is True


def test_independent_cgroup_join_accepts_observer_outside_delegation_but_rejects_foreign_parent() -> None:
    fixture = finalizer_fixture._runtime_shaped_fixture()
    topology = next(
        copy.deepcopy(document)
        for document in fixture["docs"].values()
        if document["schema"]
        == "acfqp.campaign_cgroup_topology_receipt.v180r12r3r2"
    )
    parent = topology["cgroup_parent_fact"]
    delegated = topology["delegated_parent"]
    assert parent["self_membership"] == "0::/"
    assert parent["self_membership"] != f"0::{delegated['membership_path']}"
    verifier._validate_cgroup_topology(topology)

    for field, value in (
        ("parent_path", "/sys/fs/cgroup/foreign"),
        ("parent_device", delegated["device"] + 1),
    ):
        mutated = copy.deepcopy(topology)
        mutated["cgroup_parent_fact"][field] = value
        mutated["cgroup_parent_fact_sha256"] = hashlib.sha256(
            canonical_json_bytes(mutated["cgroup_parent_fact"])
        ).hexdigest()
        with pytest.raises(
            verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error,
            match="sibling-leaf topology join",
        ):
            verifier._validate_cgroup_topology(mutated)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    (
        ("counter_records", "value", 138),
        ("campaign_native_zero_attestation", "comparison_axis_value", 1),
        ("campaign_projection_proof", "projection_term_count", 8),
    ),
)
def test_independent_verifier_rejects_resigned_accounting_mutations(
    section: str,
    field: str,
    value: int,
) -> None:
    terminal, arguments = _bundle()
    document = copy.deepcopy(terminal.document)
    closure = document["campaign_measurement_ledger"]
    target = closure[section][0] if section == "counter_records" else closure[section]
    target[field] = value
    _resign_closure(document)
    raw = _resign_terminal(document)
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error
    ):
        _verify(raw, arguments)


def test_independent_verifier_rejects_pending_terminal_claiming_pass() -> None:
    terminal, arguments = _bundle()
    document = copy.deepcopy(terminal.document)
    document["COUNTER_COMPLETENESS_GATE"] = "PASS"
    document["V180R12R3R2_CAMPAIGN_COUNTER_CLOSURE_STATUS"] = "PASS"
    raw = _resign_terminal(document)
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error,
        match="terminal differs",
    ):
        _verify(raw, arguments)


def test_independent_verifier_rejects_os_inventory_substitution() -> None:
    terminal, arguments = _bundle()
    document = copy.deepcopy(terminal.document)
    document["os_receipt_documents"][0] = copy.deepcopy(
        document["os_receipt_documents"][1]
    )
    document["os_receipt_ids"][0] = document["os_receipt_ids"][1]
    raw = _resign_terminal(document)
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error,
        match="OS receipts",
    ):
        _verify(raw, arguments)


def test_independent_verifier_rejects_tampered_raw_evidence_even_if_outer_ids_are_resigned() -> None:
    terminal, arguments = _bundle()
    document = copy.deepcopy(terminal.document)
    closure = document["campaign_measurement_ledger"]
    cgroup = next(
        row
        for row in closure["evidence_documents"]
        if row["schema"]
        == "acfqp.campaign_cgroup_observation_receipt.v180r12r3r2"
    )
    cgroup["pids_peak"] = 1
    _resign_closure(document)
    raw = _resign_terminal(document)
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error,
        match="content identity",
    ):
        _verify(raw, arguments)


def test_independent_verifier_rejects_noncanonical_terminal_bytes() -> None:
    terminal, arguments = _bundle()
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R3R2Error,
        match="canonical",
    ):
        _verify(terminal.canonical_bytes + b"\n", arguments)
