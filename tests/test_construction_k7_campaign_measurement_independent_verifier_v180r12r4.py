from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_campaign_measurement_independent_verifier_v180r12r4 as verifier,
)
from acfqp import construction_k7_campaign_measurement_ledger_v180r12r4 as ledger
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp import (
    construction_k7_campaign_measurement_supervisor_v180r12r4 as supervisor,
)
from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r4e as subdomains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests import test_construction_k7_campaign_measurement_finalizer_v180r12r4 as finalizer_fixture
from tests import test_construction_k7_campaign_measurement_ledger_v180r12r4 as ledger_fixture


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
            "root_name": f"v180r12r4-{campaign_attempt_id}",
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


def _pre_attempt_host_conformance_raw(
    *, campaign_attempt_id: str, source_membership: str,
    observed_socket_updates: dict[str, object] | None = None,
) -> bytes:
    expected_parent = copy.deepcopy(
        protocol.SERVICE_CONTEXT_CAPTURE_CGROUP_PARENT_FACT
    )
    expected_runtime = copy.deepcopy(
        protocol.SERVICE_CONTEXT_CAPTURE_RUNTIME_CAPABILITY_FACT
    )
    observed_parent = copy.deepcopy(expected_parent)
    observed_parent["self_membership"] = source_membership
    expected_socket = copy.deepcopy(verifier.SOCKET_BUFFER_CAPABILITY_EXPECTED)
    observed_socket = copy.deepcopy(expected_socket)
    if observed_socket_updates is not None:
        observed_socket.update(observed_socket_updates)
    document = {
        "schema": verifier.PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA,
        "phase": "PRE_CAMPAIGN_ATTEMPT_HOST_CONFORMANCE",
        "campaign_attempt_id": campaign_attempt_id,
        "expected": {
            "cgroup_parent_fact": expected_parent,
            "runtime_capability_fact": expected_runtime,
            "socket_buffer_capability": expected_socket,
        },
        "observed": {
            "cgroup_parent_fact": observed_parent,
            "runtime_capability_fact": copy.deepcopy(expected_runtime),
            "socket_buffer_capability": observed_socket,
        },
        "cgroup_parent_compared_fields": [
            field for field in verifier.CGROUP_PARENT_FACT_FIELDS
            if field != "self_membership"
        ],
        "cgroup_parent_excluded_fields": ["self_membership"],
        "runtime_capability_compared_fields": list(
            verifier.RUNTIME_CAPABILITY_FACT_FIELDS
        ),
        "socket_buffer_capability_exact_fields": list(
            verifier.SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
        ),
        "socket_buffer_capability_at_least_fields": list(
            verifier.SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
        ),
        "mismatch_rows": [],
        "mismatch_count": 0,
        "cause": None,
        "full_host_conformance": True,
        "working_tree_source_conformance_joined": False,
        "production_unit_ownership_t1_joined": False,
        "campaign_event_or_counter_record_issued": False,
        "campaign_attempt_created": False,
    }
    return canonical_json_bytes(document)


def _measurement_launch_attempt_document() -> dict:
    attempt = copy.deepcopy(ledger_fixture._measurement_launch_attempt_document())
    # The outer ``dispatch`` command enters the transient service; the command
    # recorded inside that service is the retained launcher's ``service-entry``
    # subcommand.  Keep this verifier fixture aligned with that producer
    # boundary even though the shared ledger-only fixture predates it.
    invocation = attempt["production_systemd_service_invocation"]
    old_command = list(invocation["launcher_command"])
    command = [*old_command[:-2], "service-entry", *old_command[-2:]]
    invocation["launcher_command"] = command
    invocation["systemd_run_argv"] = [
        *invocation["systemd_run_argv"][: -len(old_command)],
        *command,
    ]
    attempt.pop("launch_attempt_id")
    attempt["launch_attempt_id"] = hashlib.sha256(
        canonical_json_bytes(attempt)
    ).hexdigest()
    return attempt


def test_host_authority_accepts_socket_values_above_frozen_minimum() -> None:
    campaign_attempt_id = "a" * 64
    raw = _pre_attempt_host_conformance_raw(
        campaign_attempt_id=campaign_attempt_id,
        source_membership="0::/app.slice/formal-measurement.service",
        observed_socket_updates={
            field: verifier.SOCKET_BUFFER_CAPABILITY_EXPECTED[field] + 1_048_576
            for field in verifier.SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
        },
    )
    document = verifier._validate_pre_attempt_host_conformance_authority(
        raw,
        expected_cgroup_parent_fact=copy.deepcopy(
            protocol.SERVICE_CONTEXT_CAPTURE_CGROUP_PARENT_FACT
        ),
        expected_runtime_capability_fact=copy.deepcopy(
            protocol.SERVICE_CONTEXT_CAPTURE_RUNTIME_CAPABILITY_FACT
        ),
        expected_campaign_attempt_id=campaign_attempt_id,
    )
    assert document["full_host_conformance"] is True


def _measurement_launch_documents(
    terminal, *, host_conformance_raw: bytes, attempt: dict | None = None
) -> tuple[bytes, bytes]:
    attempt = (
        _measurement_launch_attempt_document()
        if attempt is None
        else copy.deepcopy(attempt)
    )
    attempt_raw = canonical_json_bytes(attempt)
    artifacts = terminal.success_artifact_bytes
    topology = next(
        row
        for row in terminal.document["campaign_measurement_ledger"][
            "evidence_documents"
        ]
        if row.get("schema")
        == "acfqp.campaign_cgroup_topology_receipt.v180r12r4"
    )
    origin_ns = 1_000_000_000_000_000
    hard_deadline_ns = origin_ns + 14_400 * 1_000_000_000
    campaign_deadline_ns = hard_deadline_ns - 600 * 1_000_000_000
    payload = {
        "schema": "acfqp.v180r12r4_prelaunch_launch_receipt.v1",
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
            "host_conformance": _regular_observation(host_conformance_raw),
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
        "production_systemd_service_invocation": attempt[
            "production_systemd_service_invocation"
        ],
        "production_runtime_placement_t1": topology[
            "production_runtime_placement_t1"
        ],
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


def _domain_document(
    payload: dict, *, identity_field: str, domain: str
) -> bytes:
    document = {
        **payload,
        identity_field: hashlib.sha256(
            domain.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    return canonical_json_bytes(document)


def _measurement_service_launch_documents(
    measurement_attempt_raw: bytes,
    measurement_receipt_raw: bytes,
) -> tuple[bytes, bytes]:
    measurement_attempt = loads_canonical_json(measurement_attempt_raw)
    measurement_receipt = loads_canonical_json(measurement_receipt_raw)
    invocation = measurement_attempt["production_systemd_service_invocation"]
    origin_ns = 900_000_000_000_000
    hard_deadline_ns = origin_ns + 14_400 * 1_000_000_000
    campaign_deadline_ns = hard_deadline_ns - 600 * 1_000_000_000
    environment = {
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        "LC_CTYPE": "C.UTF-8",
        "XDG_RUNTIME_DIR": "/run/user/1000",
    }
    empty_stream = {
        "byte_count": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "retained_prefix_hex": "",
        "retained_prefix_truncated": False,
    }
    not_found_stream = {
        "byte_count": len(b"not-found\n"),
        "sha256": hashlib.sha256(b"not-found\n").hexdigest(),
        "retained_prefix_hex": b"not-found\n".hex(),
        "retained_prefix_truncated": False,
    }
    unit_absence = {
        "systemctl_argv": [
            "/usr/bin/systemctl", "--user", "show",
            "--property=LoadState", "--value", invocation["unit_name"],
        ],
        "systemctl_environment": environment,
        "return_code": 0,
        "timed_out": False,
        "stdout": not_found_stream,
        "stderr": empty_stream,
        "expected_load_state": "not-found",
        "unit_absent_after_wait_collect": True,
    }
    attempt_payload = {
        "schema": verifier.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_SCHEMA,
        "target": "measurement",
        "token": invocation["token"],
        "unit_name": invocation["unit_name"],
        "materialization_terminal_id": measurement_attempt[
            "materialization_terminal_id"
        ],
        "materialization_terminal_sha256": measurement_attempt[
            "materialization_terminal_sha256"
        ],
        "launch_rule_id": measurement_attempt["launch_rule_id"],
        "production_systemd_service_invocation": invocation,
        "systemd_run_argv": invocation["systemd_run_argv"],
        "systemd_run_environment": environment,
        "pre_attempt_unit_absence_observation": copy.deepcopy(unit_absence),
        "inner_launch_artifact_paths": dict(
            verifier.MEASUREMENT_INNER_LAUNCH_ARTIFACT_PATHS
        ),
        "monotonic_origin_ns": origin_ns,
        "hard_deadline_ns": hard_deadline_ns,
        "campaign_deadline_ns": campaign_deadline_ns,
        "attempt_o_excl_before_systemd_run": True,
        "same_target_identity_rerun_forbidden": True,
        "pre_scientific_outer_dispatch": True,
        "campaign_event_or_evidence_document": False,
    }
    attempt_raw = _domain_document(
        attempt_payload,
        identity_field="service_launch_attempt_id",
        domain=verifier.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_DOMAIN,
    )
    attempt = loads_canonical_json(attempt_raw)
    receipt_payload = {
        "schema": verifier.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_SCHEMA,
        "target": "measurement",
        "service_launch_attempt_id": attempt["service_launch_attempt_id"],
        "token": invocation["token"],
        "unit_name": invocation["unit_name"],
        "production_systemd_service_invocation": invocation,
        "systemd_run_return_code": 0,
        "systemd_run_timed_out": False,
        "systemd_run_stdout": empty_stream,
        "systemd_run_stderr": empty_stream,
        "collected_unit_absence_observation": copy.deepcopy(unit_absence),
        "inner_launch_attempt_fact": _regular_observation(
            measurement_attempt_raw
        ),
        "inner_launch_receipt_fact": _regular_observation(
            measurement_receipt_raw
        ),
        "inner_launch_failure_fact": {"presence": "ABSENT"},
        "inner_launch_attempt_id": measurement_attempt["launch_attempt_id"],
        "inner_launch_terminal_kind": "RECEIPT",
        "inner_launch_terminal_id": measurement_receipt["launch_receipt_id"],
        "exact_attempt_terminal_join": True,
        "attempt_lock_preserved": True,
        "same_target_identity_rerun_forbidden": True,
        "pre_scientific_outer_dispatch": True,
        "campaign_event_or_evidence_document": False,
        "success": True,
        "failure_type": None,
        "failure_message": None,
    }
    receipt_raw = _domain_document(
        receipt_payload,
        identity_field="service_launch_receipt_id",
        domain=verifier.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_DOMAIN,
    )
    return attempt_raw, receipt_raw


def _bundle():
    measurement_attempt = _measurement_launch_attempt_document()
    inputs = finalizer_fixture._closed_inputs(
        measurement_launch_attempt_id=measurement_attempt["launch_attempt_id"]
    )
    terminal = finalizer_fixture._finalize(inputs)
    fixture = inputs["fixture"]
    state = fixture["state"]
    topology = next(
        row
        for row in terminal.document["campaign_measurement_ledger"][
            "evidence_documents"
        ]
        if row.get("schema")
        == "acfqp.campaign_cgroup_topology_receipt.v180r12r4"
    )
    host_conformance_raw = _pre_attempt_host_conformance_raw(
        campaign_attempt_id=state.attempt_id,
        source_membership=topology["production_runtime_placement_t1"][
            "source_membership"
        ],
    )
    measurement_attempt_raw, measurement_receipt_raw = (
        _measurement_launch_documents(
            terminal,
            host_conformance_raw=host_conformance_raw,
            attempt=measurement_attempt,
        )
    )
    measurement_service_attempt_raw, measurement_service_receipt_raw = (
        _measurement_service_launch_documents(
            measurement_attempt_raw, measurement_receipt_raw
        )
    )
    arguments = {
        "campaign_evidence_inventory_bundle_bytes": (
            terminal.evidence_inventory_bundle_bytes
        ),
        "campaign_execution_closure_bytes": terminal.execution_closure_bytes,
        "campaign_os_receipt_bundle_bytes": terminal.os_receipt_bundle_bytes,
        "campaign_ledger_closure_bytes": terminal.ledger_closure_bytes,
        "measurement_service_launch_attempt_bytes": (
            measurement_service_attempt_raw
        ),
        "measurement_service_launch_receipt_bytes": (
            measurement_service_receipt_raw
        ),
        "measurement_launch_attempt_bytes": measurement_attempt_raw,
        "measurement_launch_receipt_bytes": measurement_receipt_raw,
        "pre_attempt_host_conformance_bytes": host_conformance_raw,
        "expected_cgroup_parent_fact": copy.deepcopy(
            protocol.SERVICE_CONTEXT_CAPTURE_CGROUP_PARENT_FACT
        ),
        "expected_runtime_capability_fact": copy.deepcopy(
            protocol.SERVICE_CONTEXT_CAPTURE_RUNTIME_CAPABILITY_FACT
        ),
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
    closure_id = subdomains.extension_content_id_v180r12r4e(
        subdomains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_CLOSURE_V180R12R4E_DOMAIN,
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
            domains.extension_content_id_v180r12r4(
                domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R4_DOMAIN,
                payload,
            )
        )
        raw = canonical_json_bytes(document)
        if len(raw) == fixed_point:
            return raw
        fixed_point = len(raw)
    raise AssertionError("test terminal fixed point did not converge")


def _verify(raw: bytes, arguments: dict):
    return verifier.verify_campaign_measurement_terminal_independently_v180r12r4(
        raw,
        **arguments,
    )


def test_host_membership_must_exact_join_formal_measurement_t1() -> None:
    terminal, arguments = _bundle()
    host_document = loads_canonical_json(
        arguments["pre_attempt_host_conformance_bytes"]
    )
    host_document["observed"]["cgroup_parent_fact"]["self_membership"] = (
        "0::/app.slice/another-valid-looking.service"
    )
    host_raw = canonical_json_bytes(host_document)
    measurement_attempt_raw, measurement_receipt_raw = (
        _measurement_launch_documents(
            terminal,
            host_conformance_raw=host_raw,
            attempt=loads_canonical_json(
                arguments["measurement_launch_attempt_bytes"]
            ),
        )
    )
    service_attempt_raw, service_receipt_raw = (
        _measurement_service_launch_documents(
            measurement_attempt_raw,
            measurement_receipt_raw,
        )
    )
    arguments.update(
        pre_attempt_host_conformance_bytes=host_raw,
        measurement_launch_attempt_bytes=measurement_attempt_raw,
        measurement_launch_receipt_bytes=measurement_receipt_raw,
        measurement_service_launch_attempt_bytes=service_attempt_raw,
        measurement_service_launch_receipt_bytes=service_receipt_raw,
    )
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="host membership does not join measurement T1",
    ):
        _verify(terminal.canonical_bytes, arguments)


def test_independent_verifier_is_the_only_counter_pass_authority() -> None:
    terminal, arguments = _bundle()
    assert terminal.document["COUNTER_COMPLETENESS_GATE"] == (
        "PENDING_INDEPENDENT_REPLAY"
    )
    result = _verify(terminal.canonical_bytes, arguments)
    document = result.document

    assert document["V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS"] == "PASS"
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
    assert document[
        "production_systemd_service_invocation_independently_replayed"
    ] is True
    assert document[
        "production_runtime_placement_t1_t2_t3_independently_replayed"
    ] is True
    assert document[
        "pre_scientific_outer_service_launch_join_independently_replayed"
    ] is True
    assert document["pre_attempt_host_conformance_independently_replayed"] is True
    assert document["pre_attempt_host_conformance_relative_path"] == (
        verifier.PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH
    )
    host_raw = arguments["pre_attempt_host_conformance_bytes"]
    assert document["pre_attempt_host_conformance_byte_count"] == len(host_raw)
    assert document["pre_attempt_host_conformance_sha256"] == hashlib.sha256(
        host_raw
    ).hexdigest()
    assert document["pre_attempt_host_conformance_mode"] == 0o400
    assert document[
        "pre_attempt_host_conformance_cgroup_runtime_exact_except_self_membership"
    ] is True
    assert document[
        "pre_attempt_host_conformance_socket_buffer_minimums_met"
    ] is True
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
    for kind in ("attempt", "receipt"):
        raw = arguments[f"measurement_service_launch_{kind}_bytes"]
        outer = loads_canonical_json(raw)
        assert document[f"measurement_service_launch_{kind}_id"] == outer[
            f"service_launch_{kind}_id"
        ]
        assert document[f"measurement_service_launch_{kind}_byte_count"] == len(raw)
        assert document[f"measurement_service_launch_{kind}_sha256"] == (
            hashlib.sha256(raw).hexdigest()
        )

    payload = dict(document)
    verification_id = payload.pop("campaign_measurement_verification_id")
    assert verification_id == domains.extension_content_id_v180r12r4(
        domains.CONSTRUCTION_K7_VERIFICATION_V180R12R4_DOMAIN,
        payload,
    )


def test_independent_verifier_binds_ordinal14_service_lineage() -> None:
    attempt = _measurement_launch_attempt_document()
    invocation = attempt["production_systemd_service_invocation"]
    materialization_sha256 = attempt["materialization_terminal_sha256"]
    assert verifier._validate_production_systemd_service_invocation(
        invocation,
        repository_root=ledger_fixture.MEASUREMENT_LAUNCH_REPOSITORY_ROOT,
        materialization_terminal_sha256=materialization_sha256,
    ) == invocation
    assert invocation["token"] == (
        "5bfee9fa85834621b4947c1b68d32e96b7c53e260336d0815fd18bf59522dc72"
    )
    assert invocation["token_input"] == {
        "failed_predecessor_freeze_id": (
            "89562134029a69da93ce1dda6e9ec70abb238050fda1f530a8c5c2f557b5eb60"
        ),
        "failed_inner_launch_failure_id": (
            "7a1b8496f89378f5b2131a096c17fb9f7ed43ac64b544eacdfb3ea2802a65e82"
        ),
        "failed_outer_service_failure_id": (
            "aa3ee86dee489383a43a868180bd555a21978fc923c106e06e5b017adb4101bc"
        ),
        "repair_scope": "TARGET_AWARE_RUNNER_GIT_PROCESS_CONFORMANCE",
        "purpose": "MEASUREMENT",
    }

    for field_name, foreign_value in {
        "failed_predecessor_freeze_id": "0" * 64,
        "failed_inner_launch_failure_id": "0" * 64,
        "failed_outer_service_failure_id": "0" * 64,
        "repair_scope": "FOREIGN_REPAIR_SCOPE",
    }.items():
        foreign = copy.deepcopy(invocation)
        foreign["token_input"][field_name] = foreign_value
        with pytest.raises(
            verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
            match="authority changed",
        ):
            verifier._validate_production_systemd_service_invocation(
                foreign,
                repository_root=(
                    ledger_fixture.MEASUREMENT_LAUNCH_REPOSITORY_ROOT
                ),
                materialization_terminal_sha256=materialization_sha256,
            )


@pytest.mark.parametrize(
    "mutation",
    (
        "T2_PARENT_PID",
        "T2_PARENT_PID_FLOAT",
        "T2_PARENT_PID_BOOL",
        "T2_SELF_EQUALS_T1",
        "T2_PARENT_OUTSIDE_SOURCE",
        "T3_PARENT_PID",
        "T3_PARENT_PID_FLOAT",
    ),
)
def test_independent_placement_replay_rejects_t2_role_and_t3_stability_drift(
    mutation: str,
) -> None:
    fixture = ledger_fixture._fixture()
    topology = copy.deepcopy(
        next(
            row
            for row in fixture["docs"].values()
            if row["schema"]
            == "acfqp.campaign_cgroup_topology_receipt.v180r12r4"
        )
    )
    births = {
        row["process_role"]: copy.deepcopy(row)
        for row in fixture["docs"].values()
        if row["schema"] == "acfqp.campaign_pidfd_birth_receipt.v180r12r4"
    }
    node_rows = {
        "MEASUREMENT_ROOT": topology["measurement_root"],
        "SUPERVISOR": topology["supervisor_leaf"],
        "WORKER": topology["worker_leaf"],
    }
    verifier._validate_production_runtime_placement_chain(
        topology,
        node_rows=node_rows,
        supervisor_birth=births["SUPERVISOR"],
        worker_birth=births["WORKER"],
    )

    if mutation == "T2_PARENT_PID":
        topology["production_runtime_placement_t2"]["parent_pid"] += 1
    elif mutation == "T2_PARENT_PID_FLOAT":
        topology["production_runtime_placement_t2"]["parent_pid"] = float(
            topology["production_runtime_placement_t2"]["parent_pid"]
        )
    elif mutation == "T2_PARENT_PID_BOOL":
        topology["production_runtime_placement_t2"]["parent_pid"] = True
    elif mutation == "T2_SELF_EQUALS_T1":
        topology["production_runtime_placement_t2"]["self_pid"] = topology[
            "production_runtime_placement_t1"
        ]["self_pid"]
    elif mutation == "T2_PARENT_OUTSIDE_SOURCE":
        topology["production_runtime_placement_t2"][
            "parent_pid_in_source_cgroup_procs"
        ] = False
    else:
        for checkpoint in (
            "before_getrandom",
            "immediately_before_clone3",
        ):
            parent_pid = births["SUPERVISOR"][
                "production_runtime_placement_t3"
            ][checkpoint]["parent_pid"]
            births["SUPERVISOR"]["production_runtime_placement_t3"][checkpoint][
                "parent_pid"
            ] = (
                parent_pid + 1
                if mutation == "T3_PARENT_PID"
                else float(parent_pid)
            )

    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="placement",
    ):
        verifier._validate_production_runtime_placement_chain(
            topology,
            node_rows=node_rows,
            supervisor_birth=births["SUPERVISOR"],
            worker_birth=births["WORKER"],
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
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error
    ):
        _verify(terminal.canonical_bytes, arguments)


@pytest.mark.parametrize(
    "argument_name",
    (
        "measurement_service_launch_attempt_bytes",
        "measurement_service_launch_receipt_bytes",
    ),
)
def test_independent_verifier_rejects_each_outer_service_artifact_mutation(
    argument_name: str,
) -> None:
    terminal, arguments = _bundle()
    raw = arguments[argument_name]
    arguments[argument_name] = raw[:-1] + bytes([raw[-1] ^ 1])
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error
    ):
        _verify(terminal.canonical_bytes, arguments)


def test_independent_verifier_rejects_resigned_outer_inner_fact_substitution() -> None:
    terminal, arguments = _bundle()
    receipt = loads_canonical_json(
        arguments["measurement_service_launch_receipt_bytes"]
    )
    payload = copy.deepcopy(receipt)
    payload.pop("service_launch_receipt_id")
    payload["inner_launch_receipt_fact"]["sha256"] = "f" * 64
    arguments["measurement_service_launch_receipt_bytes"] = _domain_document(
        payload,
        identity_field="service_launch_receipt_id",
        domain=verifier.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_DOMAIN,
    )
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="receipt/inner join",
    ):
        _verify(terminal.canonical_bytes, arguments)


def test_independent_verifier_rejects_resigned_pre_attempt_absence_substitution() -> None:
    terminal, arguments = _bundle()
    attempt = loads_canonical_json(
        arguments["measurement_service_launch_attempt_bytes"]
    )
    payload = copy.deepcopy(attempt)
    payload.pop("service_launch_attempt_id")
    payload["pre_attempt_unit_absence_observation"][
        "unit_absent_after_wait_collect"
    ] = False
    arguments["measurement_service_launch_attempt_bytes"] = _domain_document(
        payload,
        identity_field="service_launch_attempt_id",
        domain=verifier.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_DOMAIN,
    )
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="pre-attempt",
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
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
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
        "campaign_measurement_finalizer_v180r12r4",
        "campaign_measurement_supervisor_v180r12r4",
        "campaign_measurement_worker_v180r12r4",
        "campaign_measurement_ledger_v180r12r4",
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
    assert verifier.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS == frozenset(
        protocol.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_DOMAIN == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_DOMAIN
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_DOMAIN == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_RECEIPT_DOMAIN
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_FAILURE_DOMAIN == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_FAILURE_DOMAIN
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_FIELDS == frozenset(
        protocol.PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_FIELDS
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_FIELDS == frozenset(
        protocol.PRELAUNCH_SERVICE_LAUNCH_RECEIPT_FIELDS
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_FAILURE_FIELDS == frozenset(
        protocol.PRELAUNCH_SERVICE_LAUNCH_FAILURE_FIELDS
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_FAILURE_PUBLICATION_FIELDS == (
        frozenset(protocol.PRELAUNCH_LAUNCH_FAILURE_PUBLICATION_FIELDS)
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_PUBLICATION_STAGES == (
        protocol.PRELAUNCH_SERVICE_LAUNCH_PUBLICATION_STAGES
    )
    assert verifier.MEASUREMENT_SERVICE_LAUNCH_PUBLICATION_STATES == (
        protocol.PRELAUNCH_LAUNCH_PUBLICATION_STATES
    )
    assert verifier.MEASUREMENT_LAUNCH_FAILURE_PUBLICATION_FIELDS == frozenset(
        protocol.PRELAUNCH_LAUNCH_FAILURE_PUBLICATION_FIELDS
    )
    assert verifier.MEASUREMENT_LAUNCH_PUBLICATION_STAGES == (
        protocol.PRELAUNCH_LAUNCH_PUBLICATION_STAGES
    )
    assert verifier.MEASUREMENT_LAUNCH_PUBLICATION_STATES == (
        protocol.PRELAUNCH_LAUNCH_PUBLICATION_STATES
    )
    assert tuple(map(len, (
        verifier.MEASUREMENT_LAUNCH_ATTEMPT_FIELDS,
        verifier.MEASUREMENT_LAUNCH_RECEIPT_FIELDS,
        verifier.MEASUREMENT_LAUNCH_FAILURE_FIELDS,
        verifier.MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_FIELDS,
        verifier.MEASUREMENT_SERVICE_LAUNCH_RECEIPT_FIELDS,
        verifier.MEASUREMENT_SERVICE_LAUNCH_FAILURE_FIELDS,
    ))) == (24, 36, 41, 20, 26, 31)
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
        == "acfqp.campaign_semantic_operation_receipt.v180r12r4"
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
    prelaunch = protocol.prelaunch_contract_v180r12r4()
    assert prelaunch[
        "independent_verifier_validates_resultant_snapshot_receipts_not_ephemeral_transport_attachment"
    ] is True


def test_independent_cgroup_join_accepts_observer_outside_delegation_but_rejects_foreign_parent() -> None:
    fixture = finalizer_fixture._runtime_shaped_fixture()
    topology = next(
        copy.deepcopy(document)
        for document in fixture["docs"].values()
        if document["schema"]
        == "acfqp.campaign_cgroup_topology_receipt.v180r12r4"
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
            verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
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
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error
    ):
        _verify(raw, arguments)


def test_independent_verifier_rejects_pending_terminal_claiming_pass() -> None:
    terminal, arguments = _bundle()
    document = copy.deepcopy(terminal.document)
    document["COUNTER_COMPLETENESS_GATE"] = "PASS"
    document["V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS"] = "PASS"
    raw = _resign_terminal(document)
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
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
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
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
        == "acfqp.campaign_cgroup_observation_receipt.v180r12r4"
    )
    cgroup["pids_peak"] = 1
    _resign_closure(document)
    raw = _resign_terminal(document)
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="content identity",
    ):
        _verify(raw, arguments)


def test_independent_verifier_rejects_noncanonical_terminal_bytes() -> None:
    terminal, arguments = _bundle()
    with pytest.raises(
        verifier.ConstructionK7CampaignMeasurementIndependentVerifierV180R12R4Error,
        match="canonical",
    ):
        _verify(terminal.canonical_bytes + b"\n", arguments)
