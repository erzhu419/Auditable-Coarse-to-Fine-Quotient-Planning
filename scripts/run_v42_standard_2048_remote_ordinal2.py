#!/usr/bin/env python3
"""One-shot remote runner and network-free result collector for V42 ordinal-2.

No function in this module invokes SSH, SCP, rsync, or a scheduler.  External
transport must first create a durable local launch attempt, then explicitly
invoke ``--launch-remote`` on the fixed host.  If that invocation disconnects,
the same identity is never retried; ``--collect-only-from-local-mirror`` only
reads a separately synchronized mirror and records what exists.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from types import SimpleNamespace
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp import construction_k7_standard_2048_process_supervision_v42r1 as processio
from acfqp import construction_k7_standard_2048_remote_execution_authority_v42r1 as authority
from acfqp import construction_k7_standard_2048_fresh_terminal_preregistration_v42 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SUPERVISOR_RELATIVE = "scripts/supervise_v42_standard_2048_remote_ordinal2.py"
# The outer supervisor deadline deliberately exceeds each producer/verifier
# deadline, so the nested helper has time to kill its own fresh process group
# and report a typed failure before the outer group can time out.
WORKER_TIMEOUT_SECONDS = 7 * 24 * 60 * 60 + 10 * 60
MAX_SUPERVISOR_STDOUT_BYTES = 576 * 1024 * 1024
MAX_SUPERVISOR_STDERR_BYTES = 1024 * 1024
MAX_COLLECTION_ARTIFACT_BYTES = 1024 * 1024 * 1024
MAX_SOURCE_CAPSULE_BYTES = 2 * 1024 * 1024 * 1024
MAX_TRANSPORT_STDOUT_BYTES = 4 * 1024 * 1024
MAX_TRANSPORT_STDERR_BYTES = 4 * 1024 * 1024

LOCAL_CONTROL_ROOT_RELATIVE = (
    ".tmp/exact-freeze/v42-standard-2048-remote-ordinal2-local-control"
)
LOCAL_PREPARE_RECEIPT_NAME = "REMOTE_PREPARE_RECEIPT.json"
LOCAL_LAUNCH_ATTEMPT_NAME = authority.LOCAL_LAUNCH_ATTEMPT_NAME
LOCAL_TRANSPORT_AMBIGUITY_NAME = "TRANSPORT_AMBIGUITY.json"
LOCAL_COLLECTION_ATTEMPTS_NAME = "COLLECTION_ATTEMPTS"
LOCAL_COLLECTION_SNAPSHOTS_NAME = "COLLECTION_SNAPSHOTS"

LOCAL_LAUNCH_ATTEMPT_SCHEMA = authority.LOCAL_LAUNCH_ATTEMPT_SCHEMA
TRANSPORT_AMBIGUITY_SCHEMA = "acfqp.v42_remote_ordinal2_transport_ambiguity.v42r1"
COLLECTION_MANIFEST_SCHEMA = "acfqp.v42_remote_ordinal2_collection_manifest.v42r1"
COLLECTION_ATTEMPT_SCHEMA = "acfqp.v42_remote_ordinal2_collection_attempt.v42r1"
COLLECTION_FAILURE_SCHEMA = "acfqp.v42_remote_ordinal2_collection_failure.v42r1"
COLLECTION_RECOVERY_MANIFEST_SCHEMA = (
    "acfqp.v42_remote_ordinal2_collection_recovery_manifest.v42r1"
)
COLLECTION_RECOVERY_MANIFEST_PREFIX = "COLLECTION_RECOVERY_MANIFEST."
COLLECTION_FAILURE_STATUS = "LOCAL_COLLECTION_FAILURE_CLOSED"
COLLECTION_UNOBSERVED_STATE = "UNOBSERVED_DUE_TO_LOCAL_COLLECTION_FAILURE"
TRANSPORT_AMBIGUITY_CLASSIFICATIONS = frozenset(
    {
        "SSH_DISCONNECT_AFTER_LAUNCH_EFFECT_POSSIBLE",
        "TRANSPORT_TIMEOUT_AFTER_LAUNCH_EFFECT_POSSIBLE",
        "TRANSPORT_EXIT_STATUS_UNAVAILABLE_AFTER_LAUNCH_EFFECT_POSSIBLE",
        "TRANSPORT_OTHER_AMBIGUOUS_AFTER_LAUNCH_EFFECT_POSSIBLE",
    }
)


class V42RemoteOrdinal2RunnerError(RuntimeError):
    """Prepare, launch, publication, or read-only collection changed."""


class V42RemoteOrdinal2SupervisorResultError(V42RemoteOrdinal2RunnerError):
    def __init__(
        self,
        message: str,
        *,
        returncode: int | None,
        stdout: bytes,
        stderr: bytes,
        classification: str,
    ) -> None:
        super().__init__(processio.bounded_message(message))
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.classification = classification


def _fail(message: str) -> NoReturn:
    raise V42RemoteOrdinal2RunnerError(processio.bounded_message(message))


def _content_id(domain: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V42RemoteOrdinal2RunnerError(f"{label} is not canonical JSON") from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} canonical bytes changed")
    return document


def _ensure_fixed_container(root: Path) -> None:
    if root != authority.REMOTE_SOURCE_ROOT:
        _fail("remote prepare/launch root differs from fixed source root")
    current = root
    for component in (".tmp", "exact-freeze"):
        child = current / component
        try:
            observed = child.lstat()
        except FileNotFoundError:
            previous_umask = os.umask(0o077)
            try:
                os.mkdir(child, 0o700)
            finally:
                os.umask(previous_umask)
            os.chmod(child, 0o700)
            processio.fsync_directory(child)
            processio.fsync_directory(current)
            observed = child.lstat()
        if (
            not stat.S_ISDIR(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o700
            or observed.st_uid != authority.REMOTE_UID
            or child.resolve(strict=True) != child
        ):
            _fail("remote fixed container component is redirected, misowned, or unsafe")
        current = child


def _read_control_manifests() -> tuple[dict[str, Any], dict[str, Any]]:
    phase = authority.verify_remote_control_phase_inventory_v42r1(
        "POST_MATERIALIZATION_PREPARE"
    )
    return phase["source_manifest"], phase["transport_manifest"]


def _journal(
    *, schema: str, domain: str, id_key: str, fields: dict[str, Any]
) -> dict[str, Any]:
    payload = {
        "schema": schema,
        "schema_version": authority.SCHEMA_VERSION,
        **fields,
    }
    return {**payload, id_key: _content_id(domain, payload)}


def _path_state(path: Path) -> str:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    if stat.S_ISREG(observed.st_mode):
        return "REGULAR_FILE"
    if stat.S_ISDIR(observed.st_mode):
        return "DIRECTORY"
    return "NONREGULAR"


def _prepare_remote() -> int:
    processio.require_isolated_python()
    if ROOT != authority.REMOTE_SOURCE_ROOT:
        _fail("remote prepare may run only from the fixed materialized source root")
    history = pre._freshness()  # noqa: SLF001
    source_manifest, transport_manifest = _read_control_manifests()
    attempt = _journal(
        schema="acfqp.v42_remote_ordinal2_prepare_attempt_journal.v42r1",
        domain="acfqp:v42-remote-ordinal2:prepare-journal",
        id_key="prepare_attempt_journal_id",
        fields={
            "formal_identity": authority.FORMAL_IDENTITY,
            "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "source_commit": source_manifest["source_commit"],
            "source_tree": source_manifest["source_tree"],
            "source_manifest_id": source_manifest["source_manifest_id"],
            "transport_manifest_id": transport_manifest["transport_manifest_id"],
            "remote_host_alias": authority.REMOTE_HOST_ALIAS,
            "remote_hostname": authority.REMOTE_HOSTNAME,
            "prepare_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "outcome_or_tape_materialized": False,
            "formal_execution_performed": False,
            "same_identity_prepare_retry_forbidden": True,
        },
    )
    attempt_raw = canonical_json_bytes(attempt)
    receipt: dict[str, Any] | None = None
    receipt_raw: bytes | None = None
    stage = "PREPARE_ATTEMPT_PUBLICATION"
    prepare_attempt_published = False
    try:
        # First mutable act of formal prepare.
        processio.write_once(
            ROOT / authority.PREPARE_ATTEMPT_JOURNAL_NAME, attempt_raw
        )
        prepare_attempt_published = True
        stage = "PREDECESSOR_AND_TRANSPORT_PREFLIGHT"
        predecessor = authority.verify_predecessor_retention_ready_v42r1(ROOT)
        materialization = authority.verify_fixed_materialization_success_v42r1(
            ROOT, transport_manifest, source_manifest
        )
        authority.verify_live_source_matches_manifest_v42(ROOT, source_manifest)
        stage = "PREPARE_HOST_ATTESTATION"
        host = authority.observe_host_attestation_v42r1(
            ROOT,
            transport_target_alias=authority.REMOTE_HOST_ALIAS,
            attestation_stage="PREPARE",
        )
        processio.write_once(
            authority.REMOTE_ROOT / authority.PREPARE_HOST_ATTESTATION_NAME,
            canonical_json_bytes(host),
        )
        authority.verify_host_attestation_v42r1(
            host, expected_stage="PREPARE", require_pass=True
        )
        stage = "FIXED_AUTHORITY_ROOT_CREATION"
        _ensure_fixed_container(ROOT)
        authority_root = authority.fixed_authority_root_v42(ROOT)
        processio.create_one_shot_root(
            authority_root, expected_parent=authority_root.parent
        )
        bootstrap_raw = processio.read_fixed_artifact(
            ROOT / "scripts/bootstrap_v42_standard_2048_remote_ordinal2.py",
            4 * 1024 * 1024,
        )
        receipt = authority.build_remote_prepare_receipt_v42r1(
            source_manifest=source_manifest,
            transport_manifest=transport_manifest,
            predecessor_retention_binding=predecessor,
            prepare_host_attestation=host,
            fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
            history_freshness_manifest_id=history["history_freshness_manifest_id"],
            remote_bootstrap_sha256=hashlib.sha256(bootstrap_raw).hexdigest(),
            remote_bootstrap_runtime_binding=materialization[
                "remote_bootstrap_runtime_binding"
            ],
        )
        receipt_raw = canonical_json_bytes(receipt)
        stage = "PREPARE_RECEIPT_PUBLICATION"
        processio.write_once(
            authority_root / authority.PREPARE_RECEIPT_NAME, receipt_raw
        )
        authority.verify_remote_control_phase_inventory_v42r1(
            "POST_PREPARE_AWAITING_LOCAL_LAUNCH", prepare_receipt=receipt
        )
    except BaseException as error:
        if not prepare_attempt_published:
            raise
        failure = _journal(
            schema="acfqp.v42_remote_ordinal2_prepare_failure_journal.v42r1",
            domain="acfqp:v42-remote-ordinal2:prepare-journal",
            id_key="prepare_failure_journal_id",
            fields={
                "formal_identity": authority.FORMAL_IDENTITY,
                "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
                "prepare_attempt_journal_id": attempt["prepare_attempt_journal_id"],
                "failure_stage": stage,
                "failure_type": type(error).__name__,
                "failure_message": processio.bounded_message(error),
                "authority_root_state": _path_state(
                    authority.fixed_authority_root_v42(ROOT)
                ),
                "evidence_root_state": _path_state(
                    authority.fixed_evidence_root_v42(ROOT)
                ),
                "prepare_receipt_state": authority.classify_artifact_bytes_v42(
                    authority.fixed_authority_root_v42(ROOT)
                    / authority.PREPARE_RECEIPT_NAME,
                    receipt_raw,
                ),
                "outcome_or_tape_materialized": False,
                "formal_execution_performed": False,
                "same_identity_prepare_retry_forbidden": True,
            },
        )
        processio.write_once(
            ROOT / authority.PREPARE_FAILURE_JOURNAL_NAME,
            canonical_json_bytes(failure),
        )
        raise
    if receipt_raw is None:
        raise AssertionError("successful ordinal-2 prepare omitted its receipt")
    sys.stdout.buffer.write(receipt_raw + b"\n")
    return 0


def _supervisor_command() -> tuple[str, ...]:
    return (
        authority.REMOTE_PYTHON,
        "-I",
        "-S",
        "-B",
        str(ROOT / SUPERVISOR_RELATIVE),
        "--formal-supervisor",
    )


def _parse_supervisor_envelope(
    completed: Any, *, receipt: dict[str, Any], attempt: dict[str, Any]
) -> tuple[bytes, bytes, bool]:
    if completed.returncode not in (0, 2):
        classification = processio.typed_failure_classification(
            completed.stderr,
            processio.child_classification("SUPERVISOR", completed.returncode),
        )
        raise V42RemoteOrdinal2SupervisorResultError(
            "remote ordinal-2 supervisor exited nonzero operationally",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            classification=classification,
        )
    if completed.stderr:
        raise V42RemoteOrdinal2SupervisorResultError(
            "remote ordinal-2 supervisor emitted unexpected stderr",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            classification="SUPERVISOR_UNEXPECTED_STDERR",
        )
    raw = processio.one_canonical_stdout(completed, "supervisor")
    envelope = _canonical_document(raw, "remote ordinal-2 supervisor envelope")
    exact_fields = {
        "schema", "schema_version", "formal_identity", "global_execution_ordinal",
        "prepare_receipt_id", "runner_attempt_id", "worker_start_id",
        "authority_consumption_id", "source_manifest_id", "transport_manifest_id",
        "predecessor_binding_id", "prepare_host_attestation_id",
        "launch_host_attestation_id", "local_launch_attempt_id",
        "producer_process_isolated",
        "verifier_process_isolated", "isolated_python_flags",
        "frozen_authority_import_resolved_to_ordinal2_source",
        "ordinal1_authority_source_loaded",
        "ordinal1_authority_runner_or_supervisor_source_loaded",
        "fresh_terminal_campaign",
        "fresh_terminal_independent_verification", "all_registered_episodes_terminal",
        "scientific_exit_code",
    }
    if (
        set(envelope) != exact_fields
        or envelope.get("schema") != "acfqp.v42_remote_ordinal2_supervised_result.v42r1"
        or envelope.get("schema_version") != authority.SCHEMA_VERSION
        or envelope.get("formal_identity") != authority.FORMAL_IDENTITY
        or envelope.get("global_execution_ordinal") != authority.GLOBAL_EXECUTION_ORDINAL
        or envelope.get("prepare_receipt_id") != receipt["prepare_receipt_id"]
        or envelope.get("runner_attempt_id") != attempt["runner_attempt_id"]
        or envelope.get("source_manifest_id") != receipt["source_manifest_id"]
        or envelope.get("transport_manifest_id") != receipt["transport_manifest_id"]
        or envelope.get("predecessor_binding_id") != receipt["predecessor_binding_id"]
        or envelope.get("prepare_host_attestation_id")
        != receipt["prepare_host_attestation_id"]
        or envelope.get("launch_host_attestation_id")
        != attempt["launch_host_attestation_id"]
        or envelope.get("local_launch_attempt_id")
        != attempt["local_launch_attempt_id"]
        or envelope.get("producer_process_isolated") is not True
        or envelope.get("verifier_process_isolated") is not True
        or envelope.get("isolated_python_flags") != ["-I", "-S", "-B"]
        or envelope.get("frozen_authority_import_resolved_to_ordinal2_source") is not True
        or envelope.get("ordinal1_authority_source_loaded") is not False
        or envelope.get(
            "ordinal1_authority_runner_or_supervisor_source_loaded"
        ) is not False
        or type(envelope.get("all_registered_episodes_terminal")) is not bool
        or envelope.get("scientific_exit_code") != completed.returncode
    ):
        _fail("remote ordinal-2 supervisor envelope semantics changed")
    campaign = envelope["fresh_terminal_campaign"]
    verification = envelope["fresh_terminal_independent_verification"]
    if type(campaign) is dict:
        campaign_payload = {
            key: value
            for key, value in campaign.items()
            if key != "fresh_terminal_campaign_id"
        }
        expected_campaign_id = domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN, campaign_payload
        )
    else:
        expected_campaign_id = None
    if type(verification) is dict:
        verification_payload = {
            key: value
            for key, value in verification.items()
            if key != "fresh_terminal_verification_id"
        }
        expected_verification_id = domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_VERIFICATION_V42_DOMAIN,
            verification_payload,
        )
    else:
        expected_verification_id = None
    if (
        type(campaign) is not dict
        or type(verification) is not dict
        or campaign.get("fresh_terminal_campaign_id") != expected_campaign_id
        or verification.get("fresh_terminal_verification_id")
        != expected_verification_id
        or verification.get("fresh_terminal_campaign_id")
        != campaign.get("fresh_terminal_campaign_id")
        or verification.get("prepare_receipt_id") != receipt["prepare_receipt_id"]
        or verification.get("runner_attempt_id") != attempt["runner_attempt_id"]
        or verification.get("worker_start_id") != envelope["worker_start_id"]
        or verification.get("authority_consumption_id")
        != envelope["authority_consumption_id"]
        or verification.get("producer_or_runner_module_imported") is not False
        or campaign.get("all_registered_episodes_terminal")
        is not envelope["all_registered_episodes_terminal"]
    ):
        _fail("remote ordinal-2 campaign/verifier join changed")
    return (
        canonical_json_bytes(campaign),
        canonical_json_bytes(verification),
        envelope["all_registered_episodes_terminal"],
    )


def _stream_fact(raw: bytes, cap: int) -> dict[str, Any]:
    return {
        "captured_byte_count": len(raw),
        "capture_cap_bytes": cap,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "capture_was_bounded": True,
    }


def _launch_remote() -> int:
    processio.require_isolated_python()
    if ROOT != authority.REMOTE_SOURCE_ROOT:
        _fail("remote launch may run only from the fixed materialized source root")
    history = pre._freshness()  # noqa: SLF001
    authority_root = authority.fixed_authority_root_v42(ROOT)
    evidence_root = authority.fixed_evidence_root_v42(ROOT)
    receipt_raw = processio.read_fixed_artifact(
        authority_root / authority.PREPARE_RECEIPT_NAME, 64 * 1024 * 1024
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_raw,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=history["history_freshness_manifest_id"],
        root=ROOT,
        require_live_source=True,
    )
    # This exact local-side O_EXCL publication and every preceding fixed
    # control are re-read before any remote launch-side mutation.
    prelaunch_phase = authority.verify_remote_control_phase_inventory_v42r1(
        "POST_PREPARE_PRELAUNCH", prepare_receipt=receipt
    )
    local_attempt_raw = prelaunch_phase["local_launch_attempt_raw"]
    local_attempt = prelaunch_phase["local_launch_attempt"]
    launch_host = authority.observe_host_attestation_v42r1(
        ROOT,
        transport_target_alias=authority.REMOTE_HOST_ALIAS,
        attestation_stage="LAUNCH",
    )
    attempt = authority.build_runner_attempt_v42(
        receipt,
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
        launch_host_attestation=launch_host,
        local_launch_attempt_id=local_attempt["local_launch_attempt_id"],
    )
    attempt_raw = canonical_json_bytes(attempt)
    launch_journal = _journal(
        schema="acfqp.v42_remote_ordinal2_launch_attempt_journal.v42r1",
        domain="acfqp:v42-remote-ordinal2:launch-journal",
        id_key="launch_attempt_journal_id",
        fields={
            "formal_identity": authority.FORMAL_IDENTITY,
            "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "prepare_receipt_id": receipt["prepare_receipt_id"],
            "runner_attempt_id": attempt["runner_attempt_id"],
            "source_commit": receipt["source_commit"],
            "source_tree": receipt["source_tree"],
            "source_manifest_id": receipt["source_manifest_id"],
            "transport_manifest_id": receipt["transport_manifest_id"],
            "predecessor_binding_id": receipt["predecessor_binding_id"],
            "launch_host_attestation_id": launch_host["host_attestation_id"],
            "local_launch_attempt_id": local_attempt["local_launch_attempt_id"],
            "launch_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "formal_execution_performed": False,
            "outcome_fields_present": False,
            "same_identity_launch_retry_forbidden": True,
        },
    )
    launch_journal_raw = canonical_json_bytes(launch_journal)
    stage = "LAUNCH_ATTEMPT_JOURNAL_PUBLICATION"
    supervisor_stdout = b""
    supervisor_stderr = b""
    captures_written = False
    launch_attempt_published = False
    published_terminal_raw: bytes | None = None
    published_terminal_returncode: int | None = None
    try:
        # First remote mutable act.  A local O_EXCL attempt is required by the
        # external transport protocol before this command may be invoked.
        processio.write_once(
            ROOT / authority.LAUNCH_ATTEMPT_JOURNAL_NAME, launch_journal_raw
        )
        launch_attempt_published = True
        stage = "LAUNCH_HOST_ATTESTATION_PUBLICATION"
        processio.write_once(
            authority.REMOTE_ROOT / authority.LAUNCH_HOST_ATTESTATION_NAME,
            canonical_json_bytes(launch_host),
        )
        launch_phase = authority.verify_remote_control_phase_inventory_v42r1(
            "POST_LAUNCH", prepare_receipt=receipt
        )
        if launch_phase["launch_host_attestation"] != launch_host:
            _fail("published launch host attestation changed before supervision")
        stage = "EVIDENCE_ROOT_CREATION"
        processio.create_one_shot_root(
            evidence_root, expected_parent=evidence_root.parent
        )
        stage = "RUNNER_ATTEMPT_PUBLICATION"
        attempt_fact = processio.write_once(
            evidence_root / authority.ATTEMPT_NAME, attempt_raw
        )
        stage = "SUPERVISOR_INVOCATION"
        completed = processio.run_capped_child(
            role="SUPERVISOR",
            command=_supervisor_command(),
            stdout_cap=MAX_SUPERVISOR_STDOUT_BYTES,
            stderr_cap=MAX_SUPERVISOR_STDERR_BYTES,
            timeout_seconds=WORKER_TIMEOUT_SECONDS,
            cwd=ROOT,
        )
        supervisor_stdout = completed.stdout
        supervisor_stderr = completed.stderr
        stage = "SUPERVISOR_STREAM_PUBLICATION"
        stdout_fact = processio.write_once(
            evidence_root / authority.SUPERVISOR_STDOUT_NAME, supervisor_stdout
        )
        stderr_fact = processio.write_once(
            evidence_root / authority.SUPERVISOR_STDERR_NAME, supervisor_stderr
        )
        captures_written = True
        stage = "SUPERVISOR_RESULT_VALIDATION"
        campaign_raw, verification_raw, all_terminal = _parse_supervisor_envelope(
            completed, receipt=receipt, attempt=attempt
        )
        stage = "SCIENTIFIC_ARTIFACT_PUBLICATION"
        campaign_fact = processio.write_once(
            evidence_root / authority.CAMPAIGN_NAME, campaign_raw
        )
        verification_fact = processio.write_once(
            evidence_root / authority.VERIFICATION_NAME, verification_raw
        )
        worker_start_fact = {
            **_stream_fact(
                processio.read_fixed_artifact(
                    evidence_root / authority.WORKER_START_NAME, 1024 * 1024
                ),
                1024 * 1024,
            ),
            "relative_name": authority.WORKER_START_NAME,
        }
        consumption_fact = {
            **_stream_fact(
                processio.read_fixed_artifact(
                    evidence_root / authority.AUTHORITY_CONSUMPTION_NAME,
                    1024 * 1024,
                ),
                1024 * 1024,
            ),
            "relative_name": authority.AUTHORITY_CONSUMPTION_NAME,
        }
        terminal_payload = {
            "schema": "acfqp.v42_remote_ordinal2_runner_terminal.v42r1",
            "schema_version": authority.SCHEMA_VERSION,
            "formal_identity": authority.FORMAL_IDENTITY,
            "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "prepare_receipt_id": receipt["prepare_receipt_id"],
            "runner_attempt_id": attempt["runner_attempt_id"],
            "launch_attempt_journal_id": launch_journal["launch_attempt_journal_id"],
            "source_manifest_id": receipt["source_manifest_id"],
            "transport_manifest_id": receipt["transport_manifest_id"],
            "predecessor_binding_id": receipt["predecessor_binding_id"],
            "local_launch_attempt_id": local_attempt["local_launch_attempt_id"],
            "attempt_artifact": attempt_fact,
            "worker_start_artifact": worker_start_fact,
            "authority_consumption_artifact": consumption_fact,
            "campaign_artifact": campaign_fact,
            "verification_artifact": verification_fact,
            "supervisor_stdout_artifact": stdout_fact,
            "supervisor_stderr_artifact": stderr_fact,
            "status": (
                "PASS_FRESH_FROM_INITIAL_TO_TERMINAL"
                if all_terminal
                else "FAIL_CLOSED_ACTIVE_AT_2048_DECISION_CAP"
            ),
            "scientific_success": all_terminal,
            "all_registered_episodes_terminal": all_terminal,
            "same_identity_rerun_forbidden": True,
            "official_execution_allowed": False,
        }
        terminal = {
            **terminal_payload,
            "runner_terminal_id": _content_id(
                "acfqp:v42-remote-ordinal2:runner-terminal", terminal_payload
            ),
        }
        published_terminal_raw = canonical_json_bytes(terminal)
        processio.write_once(
            evidence_root / authority.TERMINAL_NAME, published_terminal_raw
        )
        published_terminal_returncode = 0 if all_terminal else 2
    except BaseException as error:
        if not launch_attempt_published:
            raise
        if isinstance(error, processio.V42RemoteOrdinal2ChildError):
            supervisor_stdout = error.stdout
            supervisor_stderr = error.stderr
            classification = error.classification
            returncode = error.returncode
            group_teardown = error.group_teardown
        elif isinstance(error, V42RemoteOrdinal2SupervisorResultError):
            supervisor_stdout = error.stdout
            supervisor_stderr = error.stderr
            classification = error.classification
            returncode = error.returncode
            group_teardown = "NOT_REQUESTED"
        else:
            classification = None
            returncode = None
            group_teardown = "NOT_REQUESTED"
        if _path_state(evidence_root) == "DIRECTORY" and not captures_written:
            try:
                processio.write_once(
                    evidence_root / authority.SUPERVISOR_STDOUT_NAME,
                    supervisor_stdout,
                )
                processio.write_once(
                    evidence_root / authority.SUPERVISOR_STDERR_NAME,
                    supervisor_stderr,
                )
            except BaseException:
                pass
        failure_payload = {
            "schema": "acfqp.v42_remote_ordinal2_runner_failure.v42r1",
            "schema_version": authority.SCHEMA_VERSION,
            "formal_identity": authority.FORMAL_IDENTITY,
            "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
            "prepare_receipt_id": receipt["prepare_receipt_id"],
            "runner_attempt_id": attempt["runner_attempt_id"],
            "launch_attempt_journal_id": launch_journal["launch_attempt_journal_id"],
            "local_launch_attempt_id": local_attempt["local_launch_attempt_id"],
            "failure_stage": stage,
            "failure_type": type(error).__name__,
            "failure_message": processio.bounded_message(error),
            "supervisor_failure_classification": classification,
            "supervisor_returncode": returncode,
            "supervisor_group_teardown": group_teardown,
            "supervisor_stdout": _stream_fact(
                supervisor_stdout, MAX_SUPERVISOR_STDOUT_BYTES
            ),
            "supervisor_stderr": _stream_fact(
                supervisor_stderr, MAX_SUPERVISOR_STDERR_BYTES
            ),
            "evidence_root_state": _path_state(evidence_root),
            "scientific_success": False,
            "same_identity_rerun_forbidden": True,
            "transport_disconnect_retry_authorized": False,
            "official_execution_allowed": False,
        }
        failure = {
            **failure_payload,
            "runner_failure_id": _content_id(
                "acfqp:v42-remote-ordinal2:runner-failure", failure_payload
            ),
        }
        failure_raw = canonical_json_bytes(failure)
        processio.write_once(
            ROOT / authority.LAUNCH_FAILURE_JOURNAL_NAME, failure_raw
        )
        if _path_state(evidence_root) == "DIRECTORY":
            try:
                processio.write_once(evidence_root / authority.FAILURE_NAME, failure_raw)
            except BaseException:
                pass
        raise
    # Terminal publication is the irreversible success cut.  A downstream SSH
    # pipe closing after this point may make this process nonzero, but it must
    # never publish a contradictory launch failure for the retained terminal.
    if published_terminal_raw is None or published_terminal_returncode is None:
        _fail("published terminal return state was not retained")
    sys.stdout.buffer.write(published_terminal_raw + b"\n")
    return published_terminal_returncode


def build_local_launch_attempt_v42r1(
    *, prepare_receipt: dict[str, Any], transport_target_alias: str
) -> dict[str, Any]:
    return authority.build_local_launch_attempt_v42r1(
        prepare_receipt=prepare_receipt,
        transport_target_alias=transport_target_alias,
    )


def verify_local_launch_attempt_v42r1(
    raw_or_document: bytes | dict[str, Any], *, prepare_receipt: dict[str, Any]
) -> dict[str, Any]:
    return authority.verify_local_launch_attempt_v42r1(
        raw_or_document, prepare_receipt=prepare_receipt
    )


def _read_exact_local_control_observed(
    path: Path, maximum: int
) -> tuple[bytes, os.stat_result]:
    parent = path.parent
    parent_observed = parent.lstat()
    if (
        not path.is_absolute()
        or not stat.S_ISDIR(parent_observed.st_mode)
        or parent_observed.st_uid != os.geteuid()
        or parent.resolve(strict=True) != parent
    ):
        _fail("local control artifact parent is redirected or misowned")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o400
            or before.st_uid != os.geteuid()
            or before.st_nlink != 1
            or before.st_size > maximum
        ):
            _fail("local control artifact is nonregular, misowned, or has unsafe mode")
        raw = processio.read_fd_capped(descriptor, maximum, path.name)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size",
        "st_mtime_ns", "st_ctime_ns",
    )
    path_observed = path.lstat()
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(path_observed, field)
        for field in stable
    ):
        _fail("local control artifact changed during exact read")
    if (
        not stat.S_ISREG(path_observed.st_mode)
        or stat.S_IMODE(path_observed.st_mode) != 0o400
        or path_observed.st_uid != os.geteuid()
        or path_observed.st_nlink != 1
    ):
        _fail("local control artifact is nonregular, misowned, or has unsafe mode")
    return raw, path_observed


def _read_exact_local_control(path: Path, maximum: int) -> bytes:
    raw, _ = _read_exact_local_control_observed(path, maximum)
    return raw


def _verify_local_control_inventory(
    local_control_root: Path, *, allow_ambiguity: bool,
    allow_collection_roots: bool,
) -> set[str]:
    observed_root = local_control_root.lstat()
    if (
        not local_control_root.is_absolute()
        or not stat.S_ISDIR(observed_root.st_mode)
        or stat.S_IMODE(observed_root.st_mode) != 0o700
        or observed_root.st_uid != os.geteuid()
        or local_control_root.resolve(strict=True) != local_control_root
    ):
        _fail("local control root is redirected, misowned, or unsafe")
    names = {entry.name for entry in local_control_root.iterdir()}
    required = {LOCAL_PREPARE_RECEIPT_NAME, LOCAL_LAUNCH_ATTEMPT_NAME}
    optional = {LOCAL_TRANSPORT_AMBIGUITY_NAME} if allow_ambiguity else set()
    collection_names = {
        LOCAL_COLLECTION_ATTEMPTS_NAME,
        LOCAL_COLLECTION_SNAPSHOTS_NAME,
    }
    if (
        not required <= names
        or names - required - optional - (
            collection_names if allow_collection_roots else set()
        )
    ):
        _fail("local control root has an extra, missing, or partial entry")
    for name in names & collection_names:
        path = local_control_root / name
        observed = path.lstat()
        if (
            not stat.S_ISDIR(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o700
            or observed.st_uid != os.geteuid()
            or path.resolve(strict=True) != path
        ):
            _fail("local collection root is redirected, misowned, or unsafe")
    return names


def issue_local_launch_attempt_once_v42r1(
    *, local_control_root: Path, prepare_receipt_raw: bytes
) -> dict[str, Any]:
    receipt = authority.verify_prepare_receipt_v42(
        prepare_receipt_raw,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
        require_live_source=False,
    )
    try:
        observed_control = local_control_root.lstat()
    except FileNotFoundError:
        processio.create_one_shot_root(
            local_control_root, expected_parent=local_control_root.parent
        )
        processio.write_once(
            local_control_root / LOCAL_PREPARE_RECEIPT_NAME, prepare_receipt_raw
        )
    else:
        if (
            not stat.S_ISDIR(observed_control.st_mode)
            or stat.S_IMODE(observed_control.st_mode) != 0o700
            or observed_control.st_uid != os.geteuid()
            or local_control_root.resolve(strict=True) != local_control_root
            or {entry.name for entry in local_control_root.iterdir()}
            != {LOCAL_PREPARE_RECEIPT_NAME}
        ):
            _fail(
                "existing local launch identity already exists or is not pristine; "
                "retry is forbidden"
            )
        retained = _read_exact_local_control(
            local_control_root / LOCAL_PREPARE_RECEIPT_NAME, 64 * 1024 * 1024
        )
        if retained != prepare_receipt_raw:
            _fail("local retained prepare receipt changed")
    observed_control = local_control_root.lstat()
    receipt_observed = (local_control_root / LOCAL_PREPARE_RECEIPT_NAME).lstat()
    if (
        not stat.S_ISDIR(observed_control.st_mode)
        or stat.S_IMODE(observed_control.st_mode) != 0o700
        or observed_control.st_uid != os.geteuid()
        or local_control_root.resolve(strict=True) != local_control_root
        or {entry.name for entry in local_control_root.iterdir()}
        != {LOCAL_PREPARE_RECEIPT_NAME}
        or not stat.S_ISREG(receipt_observed.st_mode)
        or stat.S_IMODE(receipt_observed.st_mode) != 0o400
        or receipt_observed.st_uid != os.geteuid()
    ):
        _fail("local launch control inventory changed before attempt publication")
    attempt = build_local_launch_attempt_v42r1(
        prepare_receipt=receipt, transport_target_alias=authority.REMOTE_HOST_ALIAS
    )
    processio.write_once(
        local_control_root / LOCAL_LAUNCH_ATTEMPT_NAME,
        canonical_json_bytes(attempt),
    )
    return attempt


def record_transport_ambiguity_once_v42r1(
    *, local_control_root: Path, classification: str,
    transport_stdout: bytes, transport_stderr: bytes,
) -> dict[str, Any]:
    if classification not in TRANSPORT_AMBIGUITY_CLASSIFICATIONS:
        _fail("transport ambiguity classification changed")
    if len(transport_stdout) > MAX_TRANSPORT_STDOUT_BYTES:
        _fail("transport ambiguity stdout exceeds its byte cap")
    if len(transport_stderr) > MAX_TRANSPORT_STDERR_BYTES:
        _fail("transport ambiguity stderr exceeds its byte cap")
    _verify_local_control_inventory(
        local_control_root,
        allow_ambiguity=False,
        allow_collection_roots=False,
    )
    receipt_raw = _read_exact_local_control(
        local_control_root / LOCAL_PREPARE_RECEIPT_NAME, 64 * 1024 * 1024
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_raw,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
    )
    attempt_raw = _read_exact_local_control(
        local_control_root / LOCAL_LAUNCH_ATTEMPT_NAME, 1024 * 1024
    )
    attempt = verify_local_launch_attempt_v42r1(
        attempt_raw, prepare_receipt=receipt
    )
    payload = {
        "schema": TRANSPORT_AMBIGUITY_SCHEMA,
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "local_launch_attempt_id": attempt["local_launch_attempt_id"],
        "classification": classification,
        "launch_effect_may_have_occurred": True,
        "transport_stdout": _stream_fact(transport_stdout, MAX_TRANSPORT_STDOUT_BYTES),
        "transport_stderr": _stream_fact(transport_stderr, MAX_TRANSPORT_STDERR_BYTES),
        "same_identity_retry_forbidden": True,
        "retry_authorized": False,
        "only_read_only_collection_allowed": True,
    }
    document = {
        **payload,
        "transport_ambiguity_id": _content_id(
            "acfqp:v42-remote-ordinal2:transport-ambiguity", payload
        ),
    }
    processio.write_once(
        local_control_root / LOCAL_TRANSPORT_AMBIGUITY_NAME,
        canonical_json_bytes(document),
    )
    return document


def _read_local_transport_ambiguity(
    local_control_root: Path, *, local_launch_attempt_id: str
) -> dict[str, Any] | None:
    ambiguity_path = local_control_root / LOCAL_TRANSPORT_AMBIGUITY_NAME
    try:
        ambiguity_raw = _read_exact_local_control(ambiguity_path, 4 * 1024**2)
    except FileNotFoundError:
        return None
    ambiguity = _verify_collected_id_document(
        ambiguity_raw,
        label="local transport ambiguity",
        schema=TRANSPORT_AMBIGUITY_SCHEMA,
        id_key="transport_ambiguity_id",
        domain="acfqp:v42-remote-ordinal2:transport-ambiguity",
        exact_payload_fields=frozenset(
            {
                "schema", "schema_version", "formal_identity",
                "global_execution_ordinal", "local_launch_attempt_id",
                "classification", "launch_effect_may_have_occurred",
                "transport_stdout", "transport_stderr",
                "same_identity_retry_forbidden", "retry_authorized",
                "only_read_only_collection_allowed",
            }
        ),
    )
    if (
        ambiguity.get("local_launch_attempt_id") != local_launch_attempt_id
        or ambiguity.get("classification")
        not in TRANSPORT_AMBIGUITY_CLASSIFICATIONS
        or ambiguity.get("launch_effect_may_have_occurred") is not True
        or ambiguity.get("same_identity_retry_forbidden") is not True
        or ambiguity.get("retry_authorized") is not False
        or ambiguity.get("only_read_only_collection_allowed") is not True
    ):
        _fail("local transport ambiguity changed no-retry semantics")
    return ambiguity


def _collection_sources(
    remote_source_root: Path, remote_control_root: Path
) -> tuple[tuple[str, Path, int], ...]:
    authority_root = remote_source_root / authority.AUTHORITY_ROOT_RELATIVE
    evidence_root = remote_source_root / authority.EVIDENCE_ROOT_RELATIVE
    return (
        ("LOCAL_MATERIALIZATION_ATTEMPT", remote_control_root / authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME, 4 * 1024**2),
        ("SOURCE_CAPSULE", remote_control_root / authority.SOURCE_CAPSULE_NAME, MAX_SOURCE_CAPSULE_BYTES),
        ("SOURCE_MANIFEST", remote_control_root / authority.SOURCE_MANIFEST_NAME, 64 * 1024**2),
        ("TRANSPORT_MANIFEST", remote_control_root / authority.TRANSPORT_MANIFEST_NAME, 64 * 1024**2),
        ("REMOTE_BOOTSTRAP_PYZ", remote_control_root / authority.REMOTE_BOOTSTRAP_PYZ_NAME, 64 * 1024**2),
        ("REMOTE_MATERIALIZATION_ATTEMPT", remote_control_root / authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME, 4 * 1024**2),
        ("MATERIALIZATION_FAILURE", remote_control_root / authority.MATERIALIZATION_FAILURE_NAME, 4 * 1024**2),
        ("MATERIALIZATION_TERMINAL", remote_source_root / authority.MATERIALIZATION_TERMINAL_NAME, 4 * 1024**2),
        ("LOCAL_LAUNCH_ATTEMPT", remote_control_root / authority.LOCAL_LAUNCH_ATTEMPT_NAME, 1024**2),
        ("PREPARE_HOST_ATTESTATION", remote_control_root / authority.PREPARE_HOST_ATTESTATION_NAME, 1024**2),
        ("LAUNCH_HOST_ATTESTATION", remote_control_root / authority.LAUNCH_HOST_ATTESTATION_NAME, 1024**2),
        ("PREPARE_ATTEMPT", remote_source_root / authority.PREPARE_ATTEMPT_JOURNAL_NAME, 1024**2),
        ("PREPARE_FAILURE", remote_source_root / authority.PREPARE_FAILURE_JOURNAL_NAME, 4 * 1024**2),
        ("PREPARE_RECEIPT", authority_root / authority.PREPARE_RECEIPT_NAME, 64 * 1024**2),
        ("LAUNCH_ATTEMPT", remote_source_root / authority.LAUNCH_ATTEMPT_JOURNAL_NAME, 4 * 1024**2),
        ("LAUNCH_FAILURE", remote_source_root / authority.LAUNCH_FAILURE_JOURNAL_NAME, 4 * 1024**2),
        ("ATTEMPT", evidence_root / authority.ATTEMPT_NAME, 4 * 1024**2),
        ("WORKER_START", evidence_root / authority.WORKER_START_NAME, 4 * 1024**2),
        ("AUTHORITY_CONSUMPTION", evidence_root / authority.AUTHORITY_CONSUMPTION_NAME, 4 * 1024**2),
        ("SUPERVISOR_STDOUT", evidence_root / authority.SUPERVISOR_STDOUT_NAME, MAX_COLLECTION_ARTIFACT_BYTES),
        ("SUPERVISOR_STDERR", evidence_root / authority.SUPERVISOR_STDERR_NAME, 4 * 1024**2),
        ("CAMPAIGN", evidence_root / authority.CAMPAIGN_NAME, MAX_COLLECTION_ARTIFACT_BYTES),
        ("VERIFICATION", evidence_root / authority.VERIFICATION_NAME, 64 * 1024**2),
        ("TERMINAL", evidence_root / authority.TERMINAL_NAME, 4 * 1024**2),
        ("FAILURE", evidence_root / authority.FAILURE_NAME, 4 * 1024**2),
    )


def _collection_remote_path_map(
    remote_source_root: Path, remote_control_root: Path
) -> dict[str, str]:
    return {
        role: str(path)
        for role, path, _ in _collection_sources(
            remote_source_root, remote_control_root
        )
    }


def _verify_remote_collection_known_inventory(
    *, remote_source_root: Path, remote_control_root: Path,
    raw_by_role: dict[str, bytes], receipt: dict[str, Any],
    require_fixed_remote_paths: bool,
) -> None:
    expected_owner = authority.REMOTE_UID if require_fixed_remote_paths else os.geteuid()
    evidence_relative_root = Path(authority.EVIDENCE_ROOT_RELATIVE)
    declared_evidence_root_state: object = None
    if "LAUNCH_FAILURE" in raw_by_role:
        declared_evidence_root_state = _canonical_document(
            raw_by_role["LAUNCH_FAILURE"], "collected runner failure"
        ).get("evidence_root_state")
    control_role_names = {
        "LOCAL_MATERIALIZATION_ATTEMPT": authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        "SOURCE_CAPSULE": authority.SOURCE_CAPSULE_NAME,
        "SOURCE_MANIFEST": authority.SOURCE_MANIFEST_NAME,
        "TRANSPORT_MANIFEST": authority.TRANSPORT_MANIFEST_NAME,
        "REMOTE_BOOTSTRAP_PYZ": authority.REMOTE_BOOTSTRAP_PYZ_NAME,
        "REMOTE_MATERIALIZATION_ATTEMPT": authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
        "MATERIALIZATION_FAILURE": authority.MATERIALIZATION_FAILURE_NAME,
        "LOCAL_LAUNCH_ATTEMPT": authority.LOCAL_LAUNCH_ATTEMPT_NAME,
        "PREPARE_HOST_ATTESTATION": authority.PREPARE_HOST_ATTESTATION_NAME,
        "LAUNCH_HOST_ATTESTATION": authority.LAUNCH_HOST_ATTESTATION_NAME,
    }
    expected_control_names = {"source"} | {
        name for role, name in control_role_names.items() if role in raw_by_role
    }
    if {entry.name for entry in remote_control_root.iterdir()} != expected_control_names:
        _fail("collector remote control root has an extra or missing entry")

    reserved_root_roles = {
        Path(authority.AUTHORITY_ROOT_RELATIVE): {
            "PREPARE_RECEIPT": authority.PREPARE_RECEIPT_NAME,
        },
        Path(authority.EVIDENCE_ROOT_RELATIVE): {
            "ATTEMPT": authority.ATTEMPT_NAME,
            "WORKER_START": authority.WORKER_START_NAME,
            "AUTHORITY_CONSUMPTION": authority.AUTHORITY_CONSUMPTION_NAME,
            "SUPERVISOR_STDOUT": authority.SUPERVISOR_STDOUT_NAME,
            "SUPERVISOR_STDERR": authority.SUPERVISOR_STDERR_NAME,
            "CAMPAIGN": authority.CAMPAIGN_NAME,
            "VERIFICATION": authority.VERIFICATION_NAME,
            "TERMINAL": authority.TERMINAL_NAME,
            "FAILURE": authority.FAILURE_NAME,
        },
    }
    active_reserved: dict[Path, set[str]] = {
        root: {name for role, name in roles.items() if role in raw_by_role}
        for root, roles in reserved_root_roles.items()
    }
    transport_facts = {
        fact["relative_path"]: fact
        for fact in receipt["transport_manifest"]["transport_facts"]
    }
    transport_files = set(transport_facts)
    allowed_directories: set[str] = set()
    for relative in transport_files:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            allowed_directories.add(parent.as_posix())
            parent = parent.parent
    for relative_root, expected_names in active_reserved.items():
        if not expected_names:
            continue
        parent = PurePosixPath(relative_root.as_posix())
        while parent != PurePosixPath("."):
            allowed_directories.add(parent.as_posix())
            parent = parent.parent

    root_dynamic_files = {
        role: name
        for role, name in {
            "MATERIALIZATION_TERMINAL": authority.MATERIALIZATION_TERMINAL_NAME,
            "PREPARE_ATTEMPT": authority.PREPARE_ATTEMPT_JOURNAL_NAME,
            "PREPARE_FAILURE": authority.PREPARE_FAILURE_JOURNAL_NAME,
            "LAUNCH_ATTEMPT": authority.LAUNCH_ATTEMPT_JOURNAL_NAME,
            "LAUNCH_FAILURE": authority.LAUNCH_FAILURE_JOURNAL_NAME,
        }.items()
    }
    expected_root_dynamic = {
        name for role, name in root_dynamic_files.items() if role in raw_by_role
    }
    observed_transport_files: set[str] = set()
    for current, directories, filenames in os.walk(
        remote_source_root, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        relative_current = current_path.relative_to(remote_source_root)
        for name in tuple(directories):
            path = current_path / name
            relative_path = path.relative_to(remote_source_root)
            relative = relative_path.as_posix()
            if relative_path in active_reserved:
                expected_names = active_reserved[relative_path]
                observed = path.lstat()
                if not stat.S_ISDIR(observed.st_mode):
                    actual_state = (
                        "REGULAR_FILE"
                        if stat.S_ISREG(observed.st_mode)
                        else "NONREGULAR"
                    )
                    if (
                        relative_path == evidence_relative_root
                        and declared_evidence_root_state == actual_state
                        and not expected_names
                    ):
                        directories.remove(name)
                        continue
                    _fail("collector reserved result root inventory changed")
                if (
                    not expected_names
                    and not (
                        relative_path == evidence_relative_root
                        and declared_evidence_root_state == "DIRECTORY"
                    )
                ):
                    _fail("collector observed an inactive reserved result root")
                if (
                    stat.S_IMODE(observed.st_mode) != 0o700
                    or observed.st_uid != expected_owner
                    or path.resolve(strict=True) != path
                    or {entry.name for entry in path.iterdir()} != expected_names
                ):
                    _fail("collector reserved result root inventory changed")
                for child in path.iterdir():
                    child_observed = child.lstat()
                    if (
                        not stat.S_ISREG(child_observed.st_mode)
                        or child_observed.st_uid != expected_owner
                        or require_fixed_remote_paths
                        and (
                            stat.S_IMODE(child_observed.st_mode) != 0o400
                        )
                    ):
                        _fail("collector reserved result artifact is unsafe")
                directories.remove(name)
                continue
            observed = path.lstat()
            if (
                relative not in allowed_directories
                or not stat.S_ISDIR(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o700
                or observed.st_uid != expected_owner
                or path.resolve(strict=True) != path
            ):
                _fail("collector source contains an unrecognized directory")
        for name in filenames:
            path = current_path / name
            relative_path = path.relative_to(remote_source_root)
            relative = relative_path.as_posix()
            if relative_path == evidence_relative_root:
                observed = path.lstat()
                actual_state = (
                    "REGULAR_FILE"
                    if stat.S_ISREG(observed.st_mode)
                    else "NONREGULAR"
                )
                if (
                    declared_evidence_root_state == actual_state
                    and not active_reserved[evidence_relative_root]
                ):
                    continue
                _fail("collector reserved result root inventory changed")
            allowed = relative in transport_files or (
                relative_current == Path(".") and name in expected_root_dynamic
            )
            if not allowed or not stat.S_ISREG(path.lstat().st_mode):
                _fail("collector source contains an unrecognized file")
            if relative in transport_files:
                fact = transport_facts[relative]
                observed = path.lstat()
                if observed.st_uid != expected_owner or require_fixed_remote_paths and (
                    stat.S_IMODE(observed.st_mode)
                    != int(authority.MATERIALIZED_SOURCE_FILE_MODE, 8)
                ):
                    _fail("collector manifested transport file mode or owner changed")
                raw = processio.read_fixed_artifact(path, fact["byte_count"])
                git_blob_oid = hashlib.sha1(  # noqa: S324 - Git object identity
                    f"blob {len(raw)}\0".encode("ascii") + raw
                ).hexdigest()
                if (
                    len(raw) != fact["byte_count"]
                    or hashlib.sha256(raw).hexdigest() != fact["sha256"]
                    or git_blob_oid != fact["git_blob_oid"]
                ):
                    _fail("collector manifested transport file bytes changed")
                observed_transport_files.add(relative)
    if "MATERIALIZATION_TERMINAL" in raw_by_role:
        if observed_transport_files != transport_files:
            _fail("collector source is missing a manifested transport file")
    elif observed_transport_files:
        _fail("collector observed an unpublished partial transport source")


def _verify_collected_id_document(
    raw: bytes,
    *,
    label: str,
    schema: str,
    id_key: str,
    domain: str,
    exact_payload_fields: frozenset[str] | None = None,
) -> dict[str, Any]:
    document = _canonical_document(raw, label)
    payload = {key: value for key, value in document.items() if key != id_key}
    if (
        exact_payload_fields is not None
        and set(payload) != exact_payload_fields
    ) or (
        document.get("schema") != schema
        or document.get("schema_version") != authority.SCHEMA_VERSION
        or document.get("formal_identity") != authority.FORMAL_IDENTITY
        or document.get("global_execution_ordinal")
        != authority.GLOBAL_EXECUTION_ORDINAL
        or document.get(id_key) != _content_id(domain, payload)
    ):
        _fail(f"{label} type, identity, or content ID changed")
    return document


def _verify_scientific_documents(
    campaign_raw: bytes, verification_raw: bytes, *, receipt: dict[str, Any],
    attempt: dict[str, Any], worker_start: dict[str, Any],
    consumption: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    campaign = _canonical_document(campaign_raw, "collected campaign")
    verification = _canonical_document(
        verification_raw, "collected independent verification"
    )
    campaign_payload = {
        key: value
        for key, value in campaign.items()
        if key != "fresh_terminal_campaign_id"
    }
    verification_payload = {
        key: value
        for key, value in verification.items()
        if key != "fresh_terminal_verification_id"
    }
    campaign_id = domains.extension_content_id_v42(
        domains.CONSTRUCTION_K7_CAMPAIGN_V42_DOMAIN, campaign_payload
    )
    verification_id = domains.extension_content_id_v42(
        domains.CONSTRUCTION_K7_VERIFICATION_V42_DOMAIN, verification_payload
    )
    if (
        campaign.get("fresh_terminal_campaign_id") != campaign_id
        or verification.get("fresh_terminal_verification_id") != verification_id
        or verification.get("fresh_terminal_campaign_id") != campaign_id
        or verification.get("prepare_receipt_id") != receipt["prepare_receipt_id"]
        or verification.get("runner_attempt_id") != attempt["runner_attempt_id"]
        or verification.get("worker_start_id") != worker_start["worker_start_id"]
        or verification.get("authority_consumption_id")
        != consumption["authority_consumption_id"]
        or verification.get("producer_or_runner_module_imported") is not False
        or type(campaign.get("all_registered_episodes_terminal")) is not bool
    ):
        _fail("collected campaign/verification identity or join changed")
    return campaign, verification


def _write_fact(raw: bytes, relative_name: str) -> dict[str, Any]:
    return {
        "relative_name": relative_name,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _verify_collected_artifacts(
    raw_by_role: dict[str, bytes],
    *,
    local_receipt_raw: bytes,
    receipt: dict[str, Any],
    local_attempt_raw: bytes,
    local_attempt: dict[str, Any],
) -> str:
    """Type and join every present control artifact before classifying it."""

    source_manifest: dict[str, Any] | None = None
    transport_manifest: dict[str, Any] | None = None
    if "SOURCE_MANIFEST" in raw_by_role:
        source_manifest = authority.verify_source_manifest_v42r1(
            raw_by_role["SOURCE_MANIFEST"]
        )
        if source_manifest != receipt["source_manifest"]:
            _fail("collected source manifest differs from the prepare receipt")
    if "TRANSPORT_MANIFEST" in raw_by_role:
        if source_manifest is None:
            _fail("collected transport manifest omitted its execution manifest")
        transport_manifest = authority.verify_transport_manifest_v42r1(
            raw_by_role["TRANSPORT_MANIFEST"], source_manifest=source_manifest
        )
        if transport_manifest != receipt["transport_manifest"]:
            _fail("collected transport manifest differs from the prepare receipt")
    if "SOURCE_CAPSULE" in raw_by_role:
        if transport_manifest is None:
            _fail("collected source capsule omitted its transport manifest")
        capsule_raw = raw_by_role["SOURCE_CAPSULE"]
        if (
            len(capsule_raw) != transport_manifest["source_archive_byte_count"]
            or hashlib.sha256(capsule_raw).hexdigest()
            != transport_manifest["source_archive_sha256"]
        ):
            _fail("collected source capsule bytes changed")
    if "REMOTE_BOOTSTRAP_PYZ" in raw_by_role:
        if transport_manifest is None:
            _fail("collected remote bootstrap pyz omitted its transport manifest")
        pyz_artifact = authority.verify_remote_bootstrap_pyz_artifact_v42r1(
            transport_manifest["remote_bootstrap_pyz_artifact"]
        )
        pyz_raw = raw_by_role["REMOTE_BOOTSTRAP_PYZ"]
        if (
            len(pyz_raw) != pyz_artifact["pyz_byte_count"]
            or hashlib.sha256(pyz_raw).hexdigest() != pyz_artifact["pyz_sha256"]
        ):
            _fail("collected remote bootstrap pyz bytes changed")

    materialization_local: dict[str, Any] | None = None
    materialization_remote: dict[str, Any] | None = None
    materialization_terminal: dict[str, Any] | None = None
    materialization_failure: dict[str, Any] | None = None
    if "LOCAL_MATERIALIZATION_ATTEMPT" in raw_by_role:
        if source_manifest is None or transport_manifest is None:
            _fail("collected local materialization attempt omitted its manifests")
        materialization_local = authority.verify_local_materialization_attempt_v42r1(
            raw_by_role["LOCAL_MATERIALIZATION_ATTEMPT"],
            source_manifest=source_manifest,
            transport_manifest=transport_manifest,
        )
    if "REMOTE_MATERIALIZATION_ATTEMPT" in raw_by_role:
        if materialization_local is None or source_manifest is None or transport_manifest is None:
            _fail("collected remote materialization attempt omitted its local authority")
        materialization_remote = authority.verify_remote_materialization_attempt_v42r1(
            raw_by_role["REMOTE_MATERIALIZATION_ATTEMPT"],
            local_materialization_attempt=materialization_local,
            source_manifest=source_manifest,
            transport_manifest=transport_manifest,
        )
        if (
            materialization_remote["remote_bootstrap_pyz_artifact_id"]
            != receipt["remote_bootstrap_pyz_artifact_id"]
            or materialization_remote["remote_bootstrap_pyz_member_manifest_id"]
            != receipt["remote_bootstrap_pyz_member_manifest_id"]
            or materialization_remote["remote_bootstrap_pyz_sha256"]
            != receipt["remote_bootstrap_pyz_sha256"]
            or materialization_remote["remote_bootstrap_pyz_byte_count"]
            != receipt["remote_bootstrap_pyz_byte_count"]
            or materialization_remote["remote_bootstrap_runtime_binding_id"]
            != receipt["remote_bootstrap_runtime_binding_id"]
            or materialization_remote["remote_bootstrap_runtime_binding"]
            != receipt["remote_bootstrap_runtime_binding"]
        ):
            _fail("collected remote bootstrap authority differs from the prepare receipt")
    if "MATERIALIZATION_TERMINAL" in raw_by_role:
        if (
            materialization_local is None
            or materialization_remote is None
            or source_manifest is None
            or transport_manifest is None
        ):
            _fail("collected materialization terminal omitted its attempt chain")
        materialization_terminal = authority.verify_materialization_terminal_v42r1(
            raw_by_role["MATERIALIZATION_TERMINAL"],
            local_materialization_attempt=materialization_local,
            remote_materialization_attempt=materialization_remote,
            source_manifest=source_manifest,
            transport_manifest=transport_manifest,
        )
    if "MATERIALIZATION_FAILURE" in raw_by_role:
        if (
            materialization_local is None
            or materialization_remote is None
            or source_manifest is None
            or transport_manifest is None
        ):
            _fail("collected materialization failure omitted its attempt chain")
        materialization_failure = authority.verify_materialization_failure_v42r1(
            raw_by_role["MATERIALIZATION_FAILURE"],
            local_materialization_attempt=materialization_local,
            remote_materialization_attempt=materialization_remote,
            source_manifest=source_manifest,
            transport_manifest=transport_manifest,
        )
    if "PREPARE_RECEIPT" in raw_by_role:
        remote_receipt = authority.verify_prepare_receipt_v42(
            raw_by_role["PREPARE_RECEIPT"],
            fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
            history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
                "history_freshness_manifest_id"
            ],
        )
        if remote_receipt != receipt or raw_by_role["PREPARE_RECEIPT"] != local_receipt_raw:
            _fail("collected remote prepare receipt differs from retained local bytes")
    if "LOCAL_LAUNCH_ATTEMPT" in raw_by_role:
        remote_local_attempt = verify_local_launch_attempt_v42r1(
            raw_by_role["LOCAL_LAUNCH_ATTEMPT"], prepare_receipt=receipt
        )
        if (
            remote_local_attempt != local_attempt
            or raw_by_role["LOCAL_LAUNCH_ATTEMPT"] != local_attempt_raw
        ):
            _fail("collected transported local launch attempt changed")

    prepare_host: dict[str, Any] | None = None
    launch_host: dict[str, Any] | None = None
    if "PREPARE_HOST_ATTESTATION" in raw_by_role:
        prepare_host = authority.verify_host_attestation_v42r1(
            raw_by_role["PREPARE_HOST_ATTESTATION"],
            expected_stage="PREPARE",
            require_pass=True,
        )
        if prepare_host["host_attestation_id"] != receipt["prepare_host_attestation_id"]:
            _fail("collected prepare host attestation changed join")
    if "LAUNCH_HOST_ATTESTATION" in raw_by_role:
        launch_host = authority.verify_host_attestation_v42r1(
            raw_by_role["LAUNCH_HOST_ATTESTATION"],
            expected_stage="LAUNCH",
            require_pass=True,
        )

    if "PREPARE_ATTEMPT" in raw_by_role:
        prepare_journal = _verify_collected_id_document(
            raw_by_role["PREPARE_ATTEMPT"],
            label="collected prepare attempt",
            schema="acfqp.v42_remote_ordinal2_prepare_attempt_journal.v42r1",
            id_key="prepare_attempt_journal_id",
            domain="acfqp:v42-remote-ordinal2:prepare-journal",
            exact_payload_fields=frozenset(
                {
                    "schema", "schema_version", "formal_identity",
                    "global_execution_ordinal", "source_commit", "source_tree",
                    "source_manifest_id", "transport_manifest_id",
                    "remote_host_alias", "remote_hostname", "prepare_ordinal",
                    "outcome_or_tape_materialized", "formal_execution_performed",
                    "same_identity_prepare_retry_forbidden",
                }
            ),
        )
        if (
            prepare_journal.get("source_manifest_id") != receipt["source_manifest_id"]
            or prepare_journal.get("transport_manifest_id")
            != receipt["transport_manifest_id"]
            or prepare_journal.get("source_commit") != receipt["source_commit"]
            or prepare_journal.get("source_tree") != receipt["source_tree"]
            or prepare_journal.get("remote_host_alias") != authority.REMOTE_HOST_ALIAS
            or prepare_journal.get("remote_hostname") != authority.REMOTE_HOSTNAME
            or prepare_journal.get("prepare_ordinal")
            != authority.GLOBAL_EXECUTION_ORDINAL
            or prepare_journal.get("outcome_or_tape_materialized") is not False
            or prepare_journal.get("formal_execution_performed") is not False
            or prepare_journal.get("same_identity_prepare_retry_forbidden") is not True
        ):
            _fail("collected prepare attempt changed join or retry boundary")
    if "PREPARE_FAILURE" in raw_by_role:
        prepare_failure = _verify_collected_id_document(
            raw_by_role["PREPARE_FAILURE"],
            label="collected prepare failure",
            schema="acfqp.v42_remote_ordinal2_prepare_failure_journal.v42r1",
            id_key="prepare_failure_journal_id",
            domain="acfqp:v42-remote-ordinal2:prepare-journal",
            exact_payload_fields=frozenset(
                {
                    "schema", "schema_version", "formal_identity",
                    "global_execution_ordinal", "prepare_attempt_journal_id",
                    "failure_stage", "failure_type", "failure_message",
                    "authority_root_state", "evidence_root_state",
                    "prepare_receipt_state", "outcome_or_tape_materialized",
                    "formal_execution_performed",
                    "same_identity_prepare_retry_forbidden",
                }
            ),
        )
        if (
            "PREPARE_ATTEMPT" not in raw_by_role
            or prepare_failure.get("prepare_attempt_journal_id")
            != prepare_journal["prepare_attempt_journal_id"]
            or prepare_failure.get("outcome_or_tape_materialized") is not False
            or prepare_failure.get("formal_execution_performed") is not False
            or prepare_failure.get("same_identity_prepare_retry_forbidden") is not True
        ):
            _fail("collected prepare failure changed join or retry boundary")

    launch_journal: dict[str, Any] | None = None
    if "LAUNCH_ATTEMPT" in raw_by_role:
        launch_journal = _verify_collected_id_document(
            raw_by_role["LAUNCH_ATTEMPT"],
            label="collected launch attempt",
            schema="acfqp.v42_remote_ordinal2_launch_attempt_journal.v42r1",
            id_key="launch_attempt_journal_id",
            domain="acfqp:v42-remote-ordinal2:launch-journal",
            exact_payload_fields=frozenset(
                {
                    "schema", "schema_version", "formal_identity",
                    "global_execution_ordinal", "prepare_receipt_id",
                    "runner_attempt_id", "source_commit", "source_tree",
                    "source_manifest_id", "transport_manifest_id",
                    "predecessor_binding_id", "launch_host_attestation_id",
                    "local_launch_attempt_id", "launch_ordinal",
                    "formal_execution_performed", "outcome_fields_present",
                    "same_identity_launch_retry_forbidden",
                }
            ),
        )
        if (
            launch_journal.get("prepare_receipt_id") != receipt["prepare_receipt_id"]
            or launch_journal.get("source_commit") != receipt["source_commit"]
            or launch_journal.get("source_tree") != receipt["source_tree"]
            or launch_journal.get("source_manifest_id")
            != receipt["source_manifest_id"]
            or launch_journal.get("transport_manifest_id")
            != receipt["transport_manifest_id"]
            or launch_journal.get("predecessor_binding_id")
            != receipt["predecessor_binding_id"]
            or launch_journal.get("local_launch_attempt_id")
            != local_attempt["local_launch_attempt_id"]
            or launch_host is not None
            and launch_journal.get("launch_host_attestation_id")
            != launch_host["host_attestation_id"]
            or launch_journal.get("launch_ordinal")
            != authority.GLOBAL_EXECUTION_ORDINAL
            or launch_journal.get("formal_execution_performed") is not False
            or launch_journal.get("outcome_fields_present") is not False
            or launch_journal.get("same_identity_launch_retry_forbidden") is not True
        ):
            _fail("collected launch attempt changed join or retry boundary")

    runner_attempt: dict[str, Any] | None = None
    worker_start: dict[str, Any] | None = None
    consumption: dict[str, Any] | None = None
    if "ATTEMPT" in raw_by_role:
        runner_attempt = authority.verify_runner_attempt_v42(
            raw_by_role["ATTEMPT"],
            prepare_receipt=receipt,
            registered_episode_count=len(pre.INITIAL_BOARDS),
            decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
        )
        if (
            runner_attempt["local_launch_attempt_id"]
            != local_attempt["local_launch_attempt_id"]
            or launch_host is not None
            and runner_attempt["launch_host_attestation_id"]
            != launch_host["host_attestation_id"]
        ):
            _fail("collected runner attempt changed local-attempt or host join")
    if "WORKER_START" in raw_by_role:
        if runner_attempt is None:
            _fail("collected worker start omitted runner attempt")
        preliminary = _canonical_document(
            raw_by_role["WORKER_START"], "collected worker start"
        )
        worker_start = authority.verify_worker_start_v42(
            preliminary,
            prepare_receipt=receipt,
            runner_attempt=runner_attempt,
            worker_authorization_secret_sha256=preliminary.get(
                "worker_authorization_secret_sha256"
            ),
        )
    if "AUTHORITY_CONSUMPTION" in raw_by_role:
        if runner_attempt is None or worker_start is None:
            _fail("collected authority consumption omitted predecessor authority")
        consumption = authority.verify_authority_consumption_v42(
            raw_by_role["AUTHORITY_CONSUMPTION"],
            prepare_receipt=receipt,
            runner_attempt=runner_attempt,
            worker_start=worker_start,
        )

    campaign: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    if "CAMPAIGN" in raw_by_role or "VERIFICATION" in raw_by_role:
        if (
            "CAMPAIGN" not in raw_by_role
            or "VERIFICATION" not in raw_by_role
            or runner_attempt is None
            or worker_start is None
            or consumption is None
        ):
            _fail("collected scientific result is missing its authority chain")
        campaign, verification = _verify_scientific_documents(
            raw_by_role["CAMPAIGN"],
            raw_by_role["VERIFICATION"],
            receipt=receipt,
            attempt=runner_attempt,
            worker_start=worker_start,
            consumption=consumption,
        )

    terminal: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    if "TERMINAL" in raw_by_role:
        terminal = _verify_collected_id_document(
            raw_by_role["TERMINAL"],
            label="collected runner terminal",
            schema="acfqp.v42_remote_ordinal2_runner_terminal.v42r1",
            id_key="runner_terminal_id",
            domain="acfqp:v42-remote-ordinal2:runner-terminal",
            exact_payload_fields=frozenset(
                {
                    "schema", "schema_version", "formal_identity",
                    "global_execution_ordinal", "prepare_receipt_id",
                    "runner_attempt_id", "launch_attempt_journal_id",
                    "source_manifest_id", "transport_manifest_id",
                    "predecessor_binding_id", "local_launch_attempt_id",
                    "attempt_artifact", "worker_start_artifact",
                    "authority_consumption_artifact", "campaign_artifact",
                    "verification_artifact", "supervisor_stdout_artifact",
                    "supervisor_stderr_artifact", "status", "scientific_success",
                    "all_registered_episodes_terminal",
                    "same_identity_rerun_forbidden", "official_execution_allowed",
                }
            ),
        )
        if (
            runner_attempt is None
            or campaign is None
            or verification is None
            or launch_journal is None
            or terminal.get("prepare_receipt_id") != receipt["prepare_receipt_id"]
            or terminal.get("runner_attempt_id") != runner_attempt["runner_attempt_id"]
            or terminal.get("launch_attempt_journal_id")
            != launch_journal["launch_attempt_journal_id"]
            or terminal.get("source_manifest_id") != receipt["source_manifest_id"]
            or terminal.get("transport_manifest_id")
            != receipt["transport_manifest_id"]
            or terminal.get("predecessor_binding_id")
            != receipt["predecessor_binding_id"]
            or terminal.get("local_launch_attempt_id")
            != local_attempt["local_launch_attempt_id"]
            or terminal.get("all_registered_episodes_terminal")
            is not campaign["all_registered_episodes_terminal"]
            or terminal.get("scientific_success")
            is not campaign["all_registered_episodes_terminal"]
            or terminal.get("status")
            != (
                "PASS_FRESH_FROM_INITIAL_TO_TERMINAL"
                if campaign["all_registered_episodes_terminal"]
                else "FAIL_CLOSED_ACTIVE_AT_2048_DECISION_CAP"
            )
            or terminal.get("same_identity_rerun_forbidden") is not True
            or terminal.get("official_execution_allowed") is not False
        ):
            _fail("collected runner terminal changed authority or claim join")
        expected_terminal_facts = {
            "attempt_artifact": _write_fact(
                raw_by_role["ATTEMPT"], authority.ATTEMPT_NAME
            ),
            "worker_start_artifact": {
                **_stream_fact(raw_by_role["WORKER_START"], 1024 * 1024),
                "relative_name": authority.WORKER_START_NAME,
            },
            "authority_consumption_artifact": {
                **_stream_fact(
                    raw_by_role["AUTHORITY_CONSUMPTION"], 1024 * 1024
                ),
                "relative_name": authority.AUTHORITY_CONSUMPTION_NAME,
            },
            "campaign_artifact": _write_fact(
                raw_by_role["CAMPAIGN"], authority.CAMPAIGN_NAME
            ),
            "verification_artifact": _write_fact(
                raw_by_role["VERIFICATION"], authority.VERIFICATION_NAME
            ),
            "supervisor_stdout_artifact": _write_fact(
                raw_by_role["SUPERVISOR_STDOUT"], authority.SUPERVISOR_STDOUT_NAME
            ),
            "supervisor_stderr_artifact": _write_fact(
                raw_by_role["SUPERVISOR_STDERR"], authority.SUPERVISOR_STDERR_NAME
            ),
        }
        if any(
            terminal.get(field) != expected
            for field, expected in expected_terminal_facts.items()
        ):
            _fail("collected runner terminal artifact byte facts changed")
        envelope_campaign, envelope_verification, envelope_terminal = (
            _parse_supervisor_envelope(
                SimpleNamespace(
                    returncode=(
                        0
                        if campaign["all_registered_episodes_terminal"]
                        else 2
                    ),
                    stdout=raw_by_role["SUPERVISOR_STDOUT"],
                    stderr=raw_by_role["SUPERVISOR_STDERR"],
                ),
                receipt=receipt,
                attempt=runner_attempt,
            )
        )
        if (
            envelope_campaign != raw_by_role["CAMPAIGN"]
            or envelope_verification != raw_by_role["VERIFICATION"]
            or envelope_terminal
            is not campaign["all_registered_episodes_terminal"]
        ):
            _fail("collected supervisor envelope differs from published artifacts")
    if "LAUNCH_FAILURE" in raw_by_role:
        failure = _verify_collected_id_document(
            raw_by_role["LAUNCH_FAILURE"],
            label="collected runner failure",
            schema="acfqp.v42_remote_ordinal2_runner_failure.v42r1",
            id_key="runner_failure_id",
            domain="acfqp:v42-remote-ordinal2:runner-failure",
            exact_payload_fields=frozenset(
                {
                    "schema", "schema_version", "formal_identity",
                    "global_execution_ordinal", "prepare_receipt_id",
                    "runner_attempt_id", "launch_attempt_journal_id",
                    "local_launch_attempt_id", "failure_stage", "failure_type",
                    "failure_message", "supervisor_failure_classification",
                    "supervisor_returncode", "supervisor_group_teardown",
                    "supervisor_stdout",
                    "supervisor_stderr", "evidence_root_state",
                    "scientific_success", "same_identity_rerun_forbidden",
                    "transport_disconnect_retry_authorized",
                    "official_execution_allowed",
                }
            ),
        )
        if (
            failure.get("prepare_receipt_id") != receipt["prepare_receipt_id"]
            or launch_journal is None
            or failure.get("runner_attempt_id")
            != launch_journal["runner_attempt_id"]
            or failure.get("launch_attempt_journal_id")
            != launch_journal["launch_attempt_journal_id"]
            or failure.get("local_launch_attempt_id")
            != local_attempt["local_launch_attempt_id"]
            or type(failure.get("failure_stage")) is not str
            or not failure["failure_stage"]
            or type(failure.get("failure_type")) is not str
            or not failure["failure_type"]
            or type(failure.get("failure_message")) is not str
            or len(failure["failure_message"].encode("utf-8", errors="replace"))
            > processio.MAX_EXCEPTION_MESSAGE_BYTES
            or (
                failure.get("supervisor_failure_classification") is not None
                and (
                    type(failure.get("supervisor_failure_classification")) is not str
                    or not failure["supervisor_failure_classification"]
                    or len(
                        failure["supervisor_failure_classification"].encode(
                            "utf-8", errors="replace"
                        )
                    ) > 512
                )
            )
            or (
                failure.get("supervisor_returncode") is not None
                and type(failure.get("supervisor_returncode")) is not int
            )
            or type(failure.get("supervisor_group_teardown")) is not str
            or re.fullmatch(
                r"(?:NOT_REQUESTED|"
                r"DIRECT_CHILD_(?:TERM_KILL_INCOMPLETE|"
                r"TERM_THEN_KILL_REAPED|TERM_REAPED|ALREADY_ABSENT)_"
                r"ENCLOSING_GROUP_(?:REQUIRED|OWNS_DESCENDANTS)|"
                r"(?:TERM_THEN_KILL_GROUP|TERM_GROUP|GROUP_ALREADY_ABSENT)_"
                r"(?:CONFIRMED_DIRECT_WAIT_AND_PIPE_EOF|"
                r"INCOMPLETE_GROUP_OR_PIPE_DRAIN))",
                failure["supervisor_group_teardown"],
            ) is None
            or failure.get("evidence_root_state")
            not in {"ABSENT", "REGULAR_FILE", "DIRECTORY", "NONREGULAR"}
            or failure.get("scientific_success") is not False
            or failure.get("same_identity_rerun_forbidden") is not True
            or failure.get("transport_disconnect_retry_authorized") is not False
            or failure.get("official_execution_allowed") is not False
        ):
            _fail("collected runner failure changed authority or retry boundary")
        if failure.get("supervisor_stdout") != _stream_fact(
            raw_by_role.get("SUPERVISOR_STDOUT", b""),
            MAX_SUPERVISOR_STDOUT_BYTES,
        ) or failure.get("supervisor_stderr") != _stream_fact(
            raw_by_role.get("SUPERVISOR_STDERR", b""),
            MAX_SUPERVISOR_STDERR_BYTES,
        ):
            _fail("collected runner failure stream facts changed")
    if "FAILURE" in raw_by_role:
        if failure is None or raw_by_role["FAILURE"] != raw_by_role["LAUNCH_FAILURE"]:
            _fail("evidence failure differs from the fixed-parent failure journal")

    present = set(raw_by_role)
    materialization_success_required = {
        "LOCAL_MATERIALIZATION_ATTEMPT",
        "SOURCE_CAPSULE",
        "SOURCE_MANIFEST",
        "TRANSPORT_MANIFEST",
        "REMOTE_BOOTSTRAP_PYZ",
        "REMOTE_MATERIALIZATION_ATTEMPT",
        "MATERIALIZATION_TERMINAL",
    }
    terminal_required = {
        "SOURCE_MANIFEST", "TRANSPORT_MANIFEST", "LOCAL_LAUNCH_ATTEMPT",
        "PREPARE_HOST_ATTESTATION", "PREPARE_ATTEMPT", "PREPARE_RECEIPT",
        "LAUNCH_HOST_ATTESTATION", "LAUNCH_ATTEMPT", "ATTEMPT", "WORKER_START",
        "AUTHORITY_CONSUMPTION", "SUPERVISOR_STDOUT", "SUPERVISOR_STDERR",
        "CAMPAIGN", "VERIFICATION", "TERMINAL",
    }
    if terminal is not None:
        if not (terminal_required | materialization_success_required) <= present or present & {
            "MATERIALIZATION_FAILURE", "PREPARE_FAILURE", "LAUNCH_FAILURE", "FAILURE"
        }:
            _fail("terminal collection has an inconsistent artifact inventory")
        return "COMPLETE_TERMINAL"
    if failure is not None:
        failure_required = {
            "SOURCE_MANIFEST", "TRANSPORT_MANIFEST", "LOCAL_LAUNCH_ATTEMPT",
            "PREPARE_HOST_ATTESTATION", "PREPARE_ATTEMPT", "PREPARE_RECEIPT",
            "LAUNCH_ATTEMPT", "LAUNCH_FAILURE",
        }
        if (
            not (failure_required | materialization_success_required) <= present
            or "MATERIALIZATION_FAILURE" in present
            or "PREPARE_FAILURE" in present
        ):
            _fail("failure collection has an inconsistent artifact inventory")
        return "COMPLETE_FAILURE"
    if "PREPARE_FAILURE" in present:
        # A launch collector with a retained successful receipt cannot relabel a
        # prepare failure as complete.  Preserve it as ambiguous evidence.
        return "AMBIGUOUS_INCOMPLETE_READ_ONLY_SNAPSHOT"
    return "AMBIGUOUS_INCOMPLETE_READ_ONLY_SNAPSHOT"


_COLLECTION_ATTEMPT_PAYLOAD_FIELDS = frozenset(
    {
        "schema", "schema_version", "formal_identity", "global_execution_ordinal",
        "local_launch_attempt_id", "collection_ordinal",
        "previous_collection_ordinal", "previous_collection_manifest_id",
        "previous_collection_status", "transport_target_alias",
        "remote_collection_is_read_only", "same_identity_execution_retry_authorized",
        "same_collection_ordinal_retry_authorized",
    }
)
_COLLECTION_MANIFEST_PAYLOAD_FIELDS = frozenset(
    {
        "schema", "schema_version", "formal_identity", "global_execution_ordinal",
        "collection_attempt_id", "collection_ordinal",
        "previous_collection_ordinal", "previous_collection_manifest_id",
        "previous_collection_status", "local_launch_attempt_id",
        "prepare_receipt_id", "transport_target_alias",
        "collection_input_provenance", "collection_status",
        "artifact_inventory", "artifact_inventory_count",
        "transport_ambiguity_present", "transport_ambiguity_id",
        "transport_ambiguity_observation_state", "collection_failure",
        "remote_process_started_by_collector", "remote_path_mutated_by_collector",
        "collection_is_read_only", "same_identity_retry_authorized",
        "continued_read_only_collection_allowed", "further_action_if_incomplete",
        "snapshot_ordinal_root_relative",
        "snapshot_content_directory_name_is_manifest_id",
    }
)
_COLLECTION_RECOVERY_MANIFEST_PAYLOAD_FIELDS = frozenset(
    {
        *(_COLLECTION_MANIFEST_PAYLOAD_FIELDS - {"schema"}),
        "schema", "snapshot_kind", "remote_read_performed_for_snapshot",
        "expected_collection_attempt", "collection_attempt_storage",
        "recovery_root_fact", "residual_inventory", "residual_inventory_count",
        "recovery_generation", "same_ordinal_remote_observation_retry_performed",
        "recovery_publication_semantics",
    }
)


def _build_collection_failure_document(
    *, collection_attempt: dict[str, Any], failure_stage: str,
    failure_type: str, failure_message: str,
) -> dict[str, Any]:
    if (
        type(failure_stage) is not str
        or re.fullmatch(r"[A-Z0-9_]+", failure_stage) is None
        or type(failure_type) is not str
        or not failure_type
        or len(failure_type.encode("utf-8", errors="replace")) > 256
        or type(failure_message) is not str
        or len(failure_message.encode("utf-8", errors="replace")) > 4096
    ):
        _fail("local collection failure fields changed")
    payload = {
        "schema": COLLECTION_FAILURE_SCHEMA,
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "collection_attempt_id": collection_attempt["collection_attempt_id"],
        "collection_ordinal": collection_attempt["collection_ordinal"],
        "local_launch_attempt_id": collection_attempt["local_launch_attempt_id"],
        "failure_stage": failure_stage,
        "failure_type": failure_type,
        "failure_message": failure_message,
        "remote_process_started_by_collector": False,
        "remote_path_mutated_by_collector": False,
        "same_collection_ordinal_retry_authorized": False,
        "next_collection_ordinal_only": True,
    }
    return {
        **payload,
        "collection_failure_id": _content_id(
            "acfqp:v42-remote-ordinal2:collection-failure", payload
        ),
    }


def _verify_collection_failure_document(
    raw_or_document: bytes | dict[str, Any], *, collection_attempt: dict[str, Any]
) -> dict[str, Any]:
    document = (
        _canonical_document(raw_or_document, "local collection failure")
        if type(raw_or_document) is bytes
        else raw_or_document
    )
    if type(document) is not dict or set(document) != {
        "schema", "schema_version", "formal_identity", "global_execution_ordinal",
        "collection_attempt_id", "collection_ordinal", "local_launch_attempt_id",
        "failure_stage", "failure_type", "failure_message",
        "remote_process_started_by_collector", "remote_path_mutated_by_collector",
        "same_collection_ordinal_retry_authorized", "next_collection_ordinal_only",
        "collection_failure_id",
    }:
        _fail("local collection failure schema changed")
    expected = _build_collection_failure_document(
        collection_attempt=collection_attempt,
        failure_stage=document.get("failure_stage"),
        failure_type=document.get("failure_type"),
        failure_message=document.get("failure_message"),
    )
    if document != expected:
        _fail("local collection failure identity changed")
    return document


def _empty_collection_chain_state() -> dict[str, Any]:
    return {
        "artifact_baseline": {},
        "remote_paths": {},
        "remote_terminal_status": None,
        "transport_ambiguity_id": None,
        "collection_input_provenance": None,
    }


def _verify_artifact_observation_against_baseline(
    row: dict[str, Any], baseline: dict[str, Any] | None
) -> None:
    if baseline is None:
        return
    if row.get("remote_path") != baseline["remote_path"]:
        _fail("collection mirror path changed across snapshot ordinals")
    if (
        row.get("state") != COLLECTION_UNOBSERVED_STATE
        and baseline["state"] == "EXACT_RETAINED"
        and (
            row.get("state") != "EXACT_RETAINED"
            or row.get("byte_count") != baseline["byte_count"]
            or row.get("sha256") != baseline["sha256"]
        )
    ):
        _fail("collection observation rolled back or changed an exact artifact")


def _verify_and_advance_collection_observation(
    manifest: dict[str, Any], chain_state: dict[str, Any]
) -> dict[str, Any]:
    state = {
        "artifact_baseline": {
            role: dict(row)
            for role, row in chain_state["artifact_baseline"].items()
        },
        "remote_paths": dict(chain_state["remote_paths"]),
        "remote_terminal_status": chain_state["remote_terminal_status"],
        "transport_ambiguity_id": chain_state["transport_ambiguity_id"],
        "collection_input_provenance": chain_state["collection_input_provenance"],
    }
    provenance = manifest.get("collection_input_provenance")
    if provenance not in {"FIXED_REMOTE_PATHS", "LOCAL_READ_ONLY_MIRROR"}:
        _fail("collection input provenance changed")
    if (
        state["collection_input_provenance"] is not None
        and state["collection_input_provenance"] != provenance
    ):
        _fail("collection input provenance changed across snapshot ordinals")
    state["collection_input_provenance"] = provenance
    status = manifest.get("collection_status")
    if status not in {
        "COMPLETE_TERMINAL",
        "COMPLETE_FAILURE",
        "AMBIGUOUS_INCOMPLETE_READ_ONLY_SNAPSHOT",
        COLLECTION_FAILURE_STATUS,
    }:
        _fail("collection status changed")
    failure = manifest.get("collection_failure")
    if status == COLLECTION_FAILURE_STATUS:
        if type(failure) is not dict:
            _fail("closed collection failure omitted its typed failure")
    elif failure is not None:
        _fail("successful collection snapshot contains a local failure")

    inventory = manifest.get("artifact_inventory")
    expected_roles = tuple(
        role
        for role, _, _ in _collection_sources(Path("/mirror/source"), Path("/mirror"))
    )
    if type(inventory) is not list or len(inventory) != len(expected_roles):
        _fail("collection observation inventory changed")
    for expected_role, row in zip(expected_roles, inventory):
        if type(row) is not dict or row.get("role") != expected_role:
            _fail("collection observation role order changed")
        row_state = row.get("state")
        if row_state not in {
            "ABSENT", "EXACT_RETAINED", COLLECTION_UNOBSERVED_STATE
        }:
            _fail("collection observation state changed")
        remote_path = row.get("remote_path")
        prior_remote_path = state["remote_paths"].get(expected_role)
        if (
            type(remote_path) is not str
            or not Path(remote_path).is_absolute()
            or prior_remote_path is not None
            and remote_path != prior_remote_path
        ):
            _fail("collection mirror path changed across snapshot ordinals")
        state["remote_paths"][expected_role] = remote_path
        if row_state == COLLECTION_UNOBSERVED_STATE:
            if status != COLLECTION_FAILURE_STATUS or any(
                row.get(field) is not None
                for field in ("retained_relative_path", "byte_count", "sha256")
            ):
                _fail("unobserved collection role is not confined to a closed failure")
        baseline = state["artifact_baseline"].get(expected_role)
        _verify_artifact_observation_against_baseline(row, baseline)
        if row_state == COLLECTION_UNOBSERVED_STATE:
            continue
        state["artifact_baseline"][expected_role] = dict(row)

    terminal_status = state["remote_terminal_status"]
    if status != COLLECTION_FAILURE_STATUS:
        if terminal_status is not None and status != terminal_status:
            _fail("collection remote terminal status rolled back or switched")
        if status in {"COMPLETE_TERMINAL", "COMPLETE_FAILURE"}:
            state["remote_terminal_status"] = status

    ambiguity_state = manifest.get("transport_ambiguity_observation_state")
    ambiguity_present = manifest.get("transport_ambiguity_present")
    ambiguity_id = manifest.get("transport_ambiguity_id")
    prior_ambiguity_id = state["transport_ambiguity_id"]
    if ambiguity_state == "PRESENT":
        if (
            ambiguity_present is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(ambiguity_id)) is None
            or prior_ambiguity_id is not None
            and ambiguity_id != prior_ambiguity_id
        ):
            _fail("transport ambiguity changed across collection ordinals")
        state["transport_ambiguity_id"] = ambiguity_id
    elif ambiguity_state == "ABSENT":
        if ambiguity_present is not False or ambiguity_id is not None:
            _fail("absent transport ambiguity has an identity claim")
        if prior_ambiguity_id is not None:
            _fail("transport ambiguity disappeared across collection ordinals")
    elif ambiguity_state == COLLECTION_UNOBSERVED_STATE:
        if (
            status != COLLECTION_FAILURE_STATUS
            or ambiguity_present is not (prior_ambiguity_id is not None)
            or ambiguity_id != prior_ambiguity_id
        ):
            _fail("unobserved transport ambiguity changed its retained chain identity")
    else:
        _fail("transport ambiguity observation state changed")
    return state


def _hash_fixed_artifact(path: Path, maximum: int) -> tuple[int, str]:
    parent = path.parent
    observed_parent = parent.lstat()
    if (
        not path.is_absolute()
        or not stat.S_ISDIR(observed_parent.st_mode)
        or observed_parent.st_uid != os.geteuid()
        or parent.resolve(strict=True) != parent
    ):
        _fail("retained collection artifact parent changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o400
            or before.st_uid != os.geteuid()
            or before.st_nlink != 1
            or before.st_size > maximum
        ):
            _fail("retained collection artifact is nonregular or oversized")
        digest = hashlib.sha256()
        byte_count = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            byte_count += len(chunk)
            if byte_count > maximum:
                _fail("retained collection artifact exceeds its byte cap")
            digest.update(chunk)
        # Hash and flush this same pinned inode before accepting its bytes.
        os.fsync(descriptor)
        after = os.fstat(descriptor)
        digest_value = digest.hexdigest()
    finally:
        os.close(descriptor)
    final = path.lstat()
    stable = (
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_size",
        "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(final, field)
        for field in stable
    ):
        _fail("retained collection artifact changed during verification")
    return byte_count, digest_value


_RESIDUAL_FILE_STABLE_FIELDS = (
    "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
    "st_size", "st_mtime_ns", "st_ctime_ns",
)
_RECOVERY_ROOT_IDENTITY_FIELDS = (
    "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
)
_PERSISTED_RESIDUAL_FILE_FIELDS = (
    "st_mode", "st_uid", "st_gid", "st_size",
)
_PERSISTED_RECOVERY_ROOT_FIELDS = ("st_mode", "st_uid", "st_gid")


def _safe_residual_name(name: str) -> None:
    if (
        type(name) is not str
        or not name
        or name in {".", ".."}
        or "/" in name
        or "\x00" in name
        or any(ord(character) < 32 or 0xD800 <= ord(character) <= 0xDFFF for character in name)
        or name.startswith(COLLECTION_RECOVERY_MANIFEST_PREFIX)
        and re.fullmatch(
            re.escape(COLLECTION_RECOVERY_MANIFEST_PREFIX) + r"[0-9a-f]{64}\.json",
            name,
        )
        is None
    ):
        _fail("collection recovery residual name is unsafe or collides with its namespace")


def _recovery_root_fact(observed: os.stat_result) -> dict[str, Any]:
    return {
        "entry_type": "DIRECTORY",
        **{
            field: getattr(observed, field)
            for field in _PERSISTED_RECOVERY_ROOT_FIELDS
        },
    }


def _retained_attempt_storage_fact(
    attempt_path: Path, *, expected_attempt: dict[str, Any], durable: bool = False,
) -> tuple[dict[str, Any], bytes | None]:
    try:
        before = attempt_path.lstat()
    except FileNotFoundError:
        return {
            "state": "ABSENT",
            "entry_type": "ABSENT",
            "relative_path": (
                f"{LOCAL_COLLECTION_ATTEMPTS_NAME}/"
                f"{expected_attempt['collection_ordinal']:06d}.json"
            ),
            **{field: None for field in _PERSISTED_RESIDUAL_FILE_FIELDS},
            "sha256": None,
        }, None
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != os.geteuid()
        or before.st_nlink != 1
        or before.st_size > 4 * 1024**2
    ):
        _fail("interrupted collection attempt is nonregular, linked, or unsafe")
    descriptor = os.open(
        attempt_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        opened = os.fstat(descriptor)
        if any(
            getattr(before, field) != getattr(opened, field)
            for field in _RESIDUAL_FILE_STABLE_FIELDS
        ):
            _fail("interrupted collection attempt changed while opening")
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        byte_count = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            byte_count += len(chunk)
            if byte_count > 4 * 1024**2:
                _fail("interrupted collection attempt exceeds its byte cap")
            digest.update(chunk)
            chunks.append(chunk)
        if durable:
            os.fsync(descriptor)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = attempt_path.lstat()
    if any(
        getattr(opened, field) != getattr(after, field)
        or getattr(opened, field) != getattr(final, field)
        for field in _RESIDUAL_FILE_STABLE_FIELDS
    ):
        _fail("interrupted collection attempt changed during retention")
    if durable:
        processio.fsync_directory(attempt_path.parent)
    raw = b"".join(chunks)
    expected_raw = canonical_json_bytes(expected_attempt)
    return {
        "state": (
            "EXACT_CANONICAL" if raw == expected_raw else "PARTIAL_RETAINED"
        ),
        "entry_type": "REGULAR_FILE",
        "relative_path": (
            f"{LOCAL_COLLECTION_ATTEMPTS_NAME}/"
            f"{expected_attempt['collection_ordinal']:06d}.json"
        ),
        **{
            field: getattr(after, field)
            for field in _PERSISTED_RESIDUAL_FILE_FIELDS
        },
        "sha256": digest.hexdigest(),
    }, raw


def _snapshot_collection_recovery_residual(
    root: Path, *, excluded_top_level_name: str | None,
    durable: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Hash a PENDING/final residual tree without following any link."""

    before_root = root.lstat()
    if (
        not stat.S_ISDIR(before_root.st_mode)
        or stat.S_IMODE(before_root.st_mode) != 0o700
        or before_root.st_uid != os.geteuid()
    ):
        _fail("collection recovery residual root is redirected or unsafe")
    root_descriptor = os.open(
        root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    inventory: list[dict[str, Any]] = []

    def scan_directory(descriptor: int, prefix: str) -> None:
        directory_before = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(directory_before.st_mode)
            or stat.S_IMODE(directory_before.st_mode) != 0o700
            or directory_before.st_uid != os.geteuid()
            or directory_before.st_nlink < 2
        ):
            _fail("collection recovery residual contains an unsafe directory")
        names = sorted(os.listdir(descriptor))
        if len(names) != len(set(names)):
            _fail("collection recovery residual contains duplicate entries")
        for name in names:
            _safe_residual_name(name)
            if not prefix and name == excluded_top_level_name:
                continue
            relative = f"{prefix}/{name}" if prefix else name
            before = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISDIR(before.st_mode):
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
                try:
                    opened = os.fstat(child)
                    if any(
                        getattr(before, field) != getattr(opened, field)
                        for field in _RESIDUAL_FILE_STABLE_FIELDS
                    ):
                        _fail("collection recovery residual directory changed while opening")
                    scan_directory(child, relative)
                    if durable:
                        os.fsync(child)
                    after = os.fstat(child)
                finally:
                    os.close(child)
                final = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                if any(
                    getattr(after, field) != getattr(final, field)
                    for field in _RESIDUAL_FILE_STABLE_FIELDS
                ):
                    _fail("collection recovery residual directory changed during scan")
                inventory.append(
                    {
                        "relative_path": relative,
                        "entry_type": "DIRECTORY",
                        **{
                            field: (
                                None if field == "st_size" else getattr(after, field)
                            )
                            for field in _PERSISTED_RESIDUAL_FILE_FIELDS
                        },
                        "sha256": None,
                    }
                )
                continue
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != os.geteuid()
                or before.st_nlink != 1
                or before.st_size > MAX_SOURCE_CAPSULE_BYTES
            ):
                _fail("collection recovery residual contains a linked or unsafe file")
            child = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
            try:
                opened = os.fstat(child)
                if any(
                    getattr(before, field) != getattr(opened, field)
                    for field in _RESIDUAL_FILE_STABLE_FIELDS
                ):
                    _fail("collection recovery residual file changed while opening")
                digest = hashlib.sha256()
                byte_count = 0
                while True:
                    chunk = os.read(child, 1024 * 1024)
                    if not chunk:
                        break
                    byte_count += len(chunk)
                    if byte_count > MAX_SOURCE_CAPSULE_BYTES:
                        _fail("collection recovery residual file exceeds its cap")
                    digest.update(chunk)
                if durable:
                    os.fsync(child)
                after = os.fstat(child)
            finally:
                os.close(child)
            final = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if any(
                getattr(opened, field) != getattr(after, field)
                or getattr(opened, field) != getattr(final, field)
                for field in _RESIDUAL_FILE_STABLE_FIELDS
            ):
                _fail("collection recovery residual file changed during hash")
            inventory.append(
                {
                    "relative_path": relative,
                    "entry_type": "REGULAR_FILE",
                    **{
                        field: getattr(after, field)
                        for field in _PERSISTED_RESIDUAL_FILE_FIELDS
                    },
                    "sha256": digest.hexdigest(),
                }
            )
        if durable:
            os.fsync(descriptor)
        directory_after = os.fstat(descriptor)
        if any(
            getattr(directory_before, field) != getattr(directory_after, field)
            for field in _RESIDUAL_FILE_STABLE_FIELDS
        ):
            _fail("collection recovery residual directory changed across scan")

    try:
        opened_root = os.fstat(root_descriptor)
        if any(
            getattr(before_root, field) != getattr(opened_root, field)
            for field in _RECOVERY_ROOT_IDENTITY_FIELDS
        ):
            _fail("collection recovery residual root changed while opening")
        scan_directory(root_descriptor, "")
        after_root = os.fstat(root_descriptor)
    finally:
        os.close(root_descriptor)
    final_root = root.lstat()
    if any(
        getattr(opened_root, field) != getattr(after_root, field)
        or getattr(opened_root, field) != getattr(final_root, field)
        for field in _RECOVERY_ROOT_IDENTITY_FIELDS
    ):
        _fail("collection recovery residual root identity changed")
    if durable:
        processio.fsync_directory(root.parent)
    inventory.sort(key=lambda row: row["relative_path"])
    return _recovery_root_fact(after_root), inventory


def _fsync_collection_recovery_references(
    *, local_control_root: Path, collection_ordinal: int, staging_root: Path,
) -> None:
    """Flush retained interruption evidence leaf-to-root before its manifest."""

    attempts_root = local_control_root / LOCAL_COLLECTION_ATTEMPTS_NAME
    snapshots_root = local_control_root / LOCAL_COLLECTION_SNAPSHOTS_NAME
    attempt_path = attempts_root / f"{collection_ordinal:06d}.json"
    try:
        attempt_observed = attempt_path.lstat()
    except FileNotFoundError:
        attempt_observed = None
    if attempt_observed is not None:
        if (
            not stat.S_ISREG(attempt_observed.st_mode)
            or stat.S_IMODE(attempt_observed.st_mode) != 0o400
            or attempt_observed.st_uid != os.geteuid()
            or attempt_observed.st_nlink != 1
        ):
            _fail("interrupted collection attempt cannot be durably retained")
        attempt_descriptor = os.open(
            attempt_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        try:
            opened = os.fstat(attempt_descriptor)
            if any(
                getattr(attempt_observed, field) != getattr(opened, field)
                for field in _RESIDUAL_FILE_STABLE_FIELDS
            ):
                _fail("interrupted collection attempt changed before fsync")
            os.fsync(attempt_descriptor)
            after = os.fstat(attempt_descriptor)
            if any(
                getattr(opened, field) != getattr(after, field)
                for field in _RESIDUAL_FILE_STABLE_FIELDS
            ):
                _fail("interrupted collection attempt changed during fsync")
        finally:
            os.close(attempt_descriptor)
        attempt_final = attempt_path.lstat()
        if any(
            getattr(after, field) != getattr(attempt_final, field)
            for field in _RESIDUAL_FILE_STABLE_FIELDS
        ):
            _fail("interrupted collection attempt changed after fsync")
    processio.fsync_directory(attempts_root)

    def flush_directory(descriptor: int) -> None:
        directory_before = os.fstat(descriptor)
        names = sorted(os.listdir(descriptor))
        for name in names:
            _safe_residual_name(name)
            observed = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISDIR(observed.st_mode):
                child = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=descriptor,
                )
                try:
                    opened = os.fstat(child)
                    if any(
                        getattr(observed, field) != getattr(opened, field)
                        for field in _RESIDUAL_FILE_STABLE_FIELDS
                    ):
                        _fail("collection recovery directory changed before fsync")
                    flush_directory(child)
                    after = os.fstat(child)
                finally:
                    os.close(child)
                final = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                if any(
                    getattr(opened, field) != getattr(after, field)
                    or getattr(opened, field) != getattr(final, field)
                    for field in _RESIDUAL_FILE_STABLE_FIELDS
                ):
                    _fail("collection recovery directory changed during fsync")
                continue
            if (
                not stat.S_ISREG(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o400
                or observed.st_uid != os.geteuid()
                or observed.st_nlink != 1
            ):
                _fail("collection recovery file cannot be durably retained")
            child = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=descriptor,
            )
            try:
                opened = os.fstat(child)
                if any(
                    getattr(observed, field) != getattr(opened, field)
                    for field in _RESIDUAL_FILE_STABLE_FIELDS
                ):
                    _fail("collection recovery file changed before fsync")
                os.fsync(child)
                after = os.fstat(child)
                if any(
                    getattr(opened, field) != getattr(after, field)
                    for field in _RESIDUAL_FILE_STABLE_FIELDS
                ):
                    _fail("collection recovery file changed during fsync")
            finally:
                os.close(child)
            final = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if any(
                getattr(after, field) != getattr(final, field)
                for field in _RESIDUAL_FILE_STABLE_FIELDS
            ):
                _fail("collection recovery file changed after fsync")
        os.fsync(descriptor)
        directory_after = os.fstat(descriptor)
        if (
            sorted(os.listdir(descriptor)) != names
            or any(
                getattr(directory_before, field) != getattr(directory_after, field)
                for field in _RESIDUAL_FILE_STABLE_FIELDS
            )
        ):
            _fail("collection recovery directory changed across durable flush")

    staging_descriptor = os.open(
        staging_root,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        flush_directory(staging_descriptor)
    finally:
        os.close(staging_descriptor)
    processio.fsync_directory(staging_root.parent)
    processio.fsync_directory(snapshots_root)
    processio.fsync_directory(local_control_root)


def _verify_collection_snapshot_storage(
    content_root: Path, manifest: dict[str, Any]
) -> None:
    observed_root = content_root.lstat()
    storage_fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if (
        not stat.S_ISDIR(observed_root.st_mode)
        or stat.S_IMODE(observed_root.st_mode) != 0o700
        or observed_root.st_uid != os.geteuid()
        or content_root.resolve(strict=True) != content_root
    ):
        _fail("retained collection content root changed")
    if {entry.name for entry in content_root.iterdir()} != {
        "artifacts",
        "COLLECTION_MANIFEST.json",
    }:
        _fail("retained collection content root has an extra or missing entry")
    manifest_observed = (content_root / "COLLECTION_MANIFEST.json").lstat()
    if (
        not stat.S_ISREG(manifest_observed.st_mode)
        or stat.S_IMODE(manifest_observed.st_mode) != 0o400
        or manifest_observed.st_uid != os.geteuid()
        or manifest_observed.st_nlink != 1
    ):
        _fail("retained collection manifest is nonregular or has unsafe mode")
    manifest_raw = canonical_json_bytes(manifest)
    manifest_count, manifest_sha256 = _hash_fixed_artifact(
        content_root / "COLLECTION_MANIFEST.json", 64 * 1024**2
    )
    if (
        manifest_count != len(manifest_raw)
        or manifest_sha256 != hashlib.sha256(manifest_raw).hexdigest()
    ):
        _fail("retained collection manifest bytes changed")
    artifact_root = content_root / "artifacts"
    observed_artifact_root = artifact_root.lstat()
    if (
        not stat.S_ISDIR(observed_artifact_root.st_mode)
        or stat.S_IMODE(observed_artifact_root.st_mode) != 0o700
        or observed_artifact_root.st_uid != os.geteuid()
        or artifact_root.resolve(strict=True) != artifact_root
    ):
        _fail("retained collection artifact root changed")
    expected_sources = _collection_sources(Path("/mirror/source"), Path("/mirror"))
    expected_roles = tuple(role for role, _, _ in expected_sources)
    caps = {role: cap for role, _, cap in expected_sources}
    inventory = manifest.get("artifact_inventory")
    if (
        type(inventory) is not list
        or manifest.get("artifact_inventory_count") != len(expected_roles)
        or len(inventory) != len(expected_roles)
    ):
        _fail("retained collection artifact inventory count changed")
    expected_retained_names: set[str] = set()
    for index, (expected_role, row) in enumerate(zip(expected_roles, inventory)):
        if type(row) is not dict or set(row) != {
            "role", "remote_path", "state", "retained_relative_path",
            "byte_count", "sha256",
        }:
            _fail("retained collection artifact row schema changed")
        remote_path = row.get("remote_path")
        if (
            row.get("role") != expected_role
            or type(remote_path) is not str
            or not Path(remote_path).is_absolute()
        ):
            _fail("retained collection artifact role or remote path changed")
        if row.get("state") in {"ABSENT", COLLECTION_UNOBSERVED_STATE}:
            if any(
                row.get(field) is not None
                for field in ("retained_relative_path", "byte_count", "sha256")
            ):
                _fail("non-retained collection artifact has retained byte claims")
            continue
        retained_name = f"{index:02d}_{expected_role}.bin"
        retained_relative = f"artifacts/{retained_name}"
        if (
            row.get("state") != "EXACT_RETAINED"
            or row.get("retained_relative_path") != retained_relative
            or type(row.get("byte_count")) is not int
            or row["byte_count"] < 0
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256"))) is None
        ):
            _fail("retained collection artifact fact changed")
        byte_count, sha256 = _hash_fixed_artifact(
            artifact_root / retained_name, caps[expected_role]
        )
        if byte_count != row["byte_count"] or sha256 != row["sha256"]:
            _fail("retained collection artifact bytes changed")
        expected_retained_names.add(retained_name)
    observed_retained_names: set[str] = set()
    for entry in artifact_root.iterdir():
        if not stat.S_ISREG(entry.lstat().st_mode):
            _fail("retained collection artifact root contains a nonregular entry")
        observed_retained_names.add(entry.name)
    if observed_retained_names != expected_retained_names:
        _fail("retained collection artifact root has an extra or missing file")
    processio.fsync_directory(artifact_root)
    processio.fsync_directory(content_root)
    final_root = content_root.lstat()
    final_artifact_root = artifact_root.lstat()
    if (
        any(
            getattr(observed_root, field) != getattr(final_root, field)
            for field in storage_fields
        )
        or any(
            getattr(observed_artifact_root, field)
            != getattr(final_artifact_root, field)
            for field in storage_fields
        )
        or {entry.name for entry in content_root.iterdir()}
        != {"artifacts", "COLLECTION_MANIFEST.json"}
        or {entry.name for entry in artifact_root.iterdir()}
        != expected_retained_names
    ):
        _fail("retained collection snapshot changed during durable verification")


def _verify_expected_collection_attempt_document(
    document: object,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("collection recovery omitted its deterministic expected attempt")
    return _verify_collected_id_document(
        canonical_json_bytes(document),
        label="collection recovery expected attempt",
        schema=COLLECTION_ATTEMPT_SCHEMA,
        id_key="collection_attempt_id",
        domain="acfqp:v42-remote-ordinal2:collection-attempt",
        exact_payload_fields=_COLLECTION_ATTEMPT_PAYLOAD_FIELDS,
    )


def _verify_collection_recovery_manifest_document(raw: bytes) -> dict[str, Any]:
    manifest = _verify_collected_id_document(
        raw,
        label="collection interruption recovery manifest",
        schema=COLLECTION_RECOVERY_MANIFEST_SCHEMA,
        id_key="collection_manifest_id",
        domain="acfqp:v42-remote-ordinal2:collection-recovery-manifest",
        exact_payload_fields=_COLLECTION_RECOVERY_MANIFEST_PAYLOAD_FIELDS,
    )
    expected_attempt = _verify_expected_collection_attempt_document(
        manifest.get("expected_collection_attempt")
    )
    attempt_storage = manifest.get("collection_attempt_storage")
    storage_fields = {
        "state", "entry_type", "relative_path",
        *_PERSISTED_RESIDUAL_FILE_FIELDS, "sha256",
    }
    root_fact = manifest.get("recovery_root_fact")
    residual_inventory = manifest.get("residual_inventory")
    if (
        manifest.get("snapshot_kind") != "LOCAL_INTERRUPTION_RECOVERY"
        or manifest.get("remote_read_performed_for_snapshot") is not False
        or manifest.get("same_ordinal_remote_observation_retry_performed") is not False
        or manifest.get("recovery_publication_semantics")
        != "SAME_ORDINAL_LOCAL_TYPED_CLOSE_WITHOUT_REMOTE_REREAD"
        or manifest.get("collection_status") != COLLECTION_FAILURE_STATUS
        or manifest.get("collection_attempt_id")
        != expected_attempt["collection_attempt_id"]
        or type(attempt_storage) is not dict
        or set(attempt_storage) != storage_fields
        or attempt_storage.get("state")
        not in {"ABSENT", "EXACT_CANONICAL", "PARTIAL_RETAINED"}
        or type(root_fact) is not dict
        or set(root_fact)
        != {"entry_type", *_PERSISTED_RECOVERY_ROOT_FIELDS}
        or root_fact.get("entry_type") != "DIRECTORY"
        or type(residual_inventory) is not list
        or manifest.get("residual_inventory_count") != len(residual_inventory)
        or type(manifest.get("recovery_generation")) is not int
        or manifest["recovery_generation"] <= 0
    ):
        _fail("collection recovery manifest semantics changed")
    expected_attempt_relative = (
        f"{LOCAL_COLLECTION_ATTEMPTS_NAME}/"
        f"{expected_attempt['collection_ordinal']:06d}.json"
    )
    if attempt_storage["relative_path"] != expected_attempt_relative:
        _fail("collection recovery attempt storage path changed")
    if attempt_storage["state"] == "ABSENT":
        if (
            attempt_storage["entry_type"] != "ABSENT"
            or any(
                attempt_storage[field] is not None
                for field in (*_PERSISTED_RESIDUAL_FILE_FIELDS, "sha256")
            )
        ):
            _fail("absent collection recovery attempt has retained metadata")
    elif (
        attempt_storage["entry_type"] != "REGULAR_FILE"
        or type(attempt_storage["st_mode"]) is not int
        or not stat.S_ISREG(attempt_storage["st_mode"])
        or stat.S_IMODE(attempt_storage["st_mode"]) != 0o400
        or type(attempt_storage["st_uid"]) is not int
        or type(attempt_storage["st_gid"]) is not int
        or type(attempt_storage["st_size"]) is not int
        or attempt_storage["st_size"] < 0
        or re.fullmatch(r"[0-9a-f]{64}", str(attempt_storage["sha256"])) is None
    ):
        _fail("retained collection recovery attempt metadata changed")
    if (
        type(root_fact.get("st_mode")) is not int
        or not stat.S_ISDIR(root_fact["st_mode"])
        or stat.S_IMODE(root_fact["st_mode"]) != 0o700
        or type(root_fact.get("st_uid")) is not int
        or type(root_fact.get("st_gid")) is not int
    ):
        _fail("collection recovery root metadata changed")
    expected_residual_fields = {
        "relative_path", "entry_type", *_PERSISTED_RESIDUAL_FILE_FIELDS, "sha256",
    }
    previous_relative: str | None = None
    for row in residual_inventory:
        if (
            type(row) is not dict
            or set(row) != expected_residual_fields
            or type(row.get("relative_path")) is not str
            or not row["relative_path"]
            or row["relative_path"].startswith("/")
            or any(
                part in {"", ".", ".."}
                for part in PurePosixPath(row["relative_path"]).parts
            )
            or row.get("entry_type") not in {"DIRECTORY", "REGULAR_FILE"}
            or type(row.get("st_mode")) is not int
            or type(row.get("st_uid")) is not int
            or type(row.get("st_gid")) is not int
            or previous_relative is not None
            and row["relative_path"] <= previous_relative
            or row["entry_type"] == "DIRECTORY"
            and (
                not stat.S_ISDIR(row["st_mode"])
                or stat.S_IMODE(row["st_mode"]) != 0o700
                or row.get("sha256") is not None
                or row.get("st_size") is not None
            )
            or row["entry_type"] == "REGULAR_FILE"
            and (
                not stat.S_ISREG(row["st_mode"])
                or stat.S_IMODE(row["st_mode"]) != 0o400
                or type(row.get("st_size")) is not int
                or row["st_size"] < 0
                or re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256"))) is None
            )
        ):
            _fail("collection recovery residual inventory schema changed")
        previous_relative = row["relative_path"]
    return manifest


def _verify_collection_recovery_snapshot_storage(
    content_root: Path, manifest: dict[str, Any], *, attempt_path: Path,
) -> dict[str, Any]:
    recovery_name = (
        f"{COLLECTION_RECOVERY_MANIFEST_PREFIX}"
        f"{manifest['collection_manifest_id']}.json"
    )
    recovery_path = content_root / recovery_name
    observed_manifest = recovery_path.lstat()
    if (
        not stat.S_ISREG(observed_manifest.st_mode)
        or stat.S_IMODE(observed_manifest.st_mode) != 0o400
        or observed_manifest.st_uid != os.geteuid()
        or observed_manifest.st_nlink != 1
    ):
        _fail("collection recovery manifest storage is unsafe")
    raw = processio.read_fixed_artifact(recovery_path, 64 * 1024**2)
    if _verify_collection_recovery_manifest_document(raw) != manifest:
        _fail("collection recovery manifest bytes changed")
    recovery_count, recovery_sha256 = _hash_fixed_artifact(
        recovery_path, 64 * 1024**2
    )
    if (
        recovery_count != len(raw)
        or recovery_sha256 != hashlib.sha256(raw).hexdigest()
    ):
        _fail("collection recovery manifest durable bytes changed")
    root_fact, residual_inventory = _snapshot_collection_recovery_residual(
        content_root, excluded_top_level_name=recovery_name, durable=True
    )
    if (
        root_fact != manifest["recovery_root_fact"]
        or residual_inventory != manifest["residual_inventory"]
    ):
        _fail("collection recovery residual bytes or metadata changed")
    expected_attempt = manifest["expected_collection_attempt"]
    attempt_storage, attempt_raw = _retained_attempt_storage_fact(
        attempt_path, expected_attempt=expected_attempt, durable=True
    )
    if attempt_storage != manifest["collection_attempt_storage"]:
        _fail("collection recovery attempt residual changed")
    expected_raw = canonical_json_bytes(expected_attempt)
    if (
        attempt_storage["state"] == "EXACT_CANONICAL"
        and attempt_raw != expected_raw
        or attempt_storage["state"] == "PARTIAL_RETAINED"
        and (attempt_raw is None or attempt_raw == expected_raw)
        or attempt_storage["state"] == "ABSENT"
        and attempt_raw is not None
    ):
        _fail("collection recovery attempt state changed")
    prior_recovery_files = sum(
        1
        for row in residual_inventory
        if "/" not in row["relative_path"]
        and row["entry_type"] == "REGULAR_FILE"
        and re.fullmatch(
            re.escape(COLLECTION_RECOVERY_MANIFEST_PREFIX)
            + r"[0-9a-f]{64}\.json",
            row["relative_path"],
        )
        is not None
    )
    if manifest["recovery_generation"] != prior_recovery_files + 1:
        _fail("collection recovery generation changed")
    return expected_attempt


def _ensure_local_append_container(parent: Path, name: str) -> Path:
    path = parent / name
    try:
        observed = path.lstat()
    except FileNotFoundError:
        previous_umask = os.umask(0o077)
        try:
            try:
                os.mkdir(path, 0o700)
            except FileExistsError:
                observed = path.lstat()
            else:
                os.chmod(path, 0o700)
                observed = path.lstat()
        finally:
            os.umask(previous_umask)
    if (
        not stat.S_ISDIR(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o700
        or observed.st_uid != os.geteuid()
        or path.resolve(strict=True) != path
    ):
        _fail("local append-only collection container changed")
    processio.fsync_directory(path)
    processio.fsync_directory(parent)
    return path


def _snapshot_local_collection_chain(
    attempts_root: Path, snapshots_root: Path
) -> dict[str, tuple[Any, ...]]:
    snapshot: dict[str, tuple[Any, ...]] = {}
    stable_fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size",
        "st_mtime_ns", "st_ctime_ns",
    )
    for label, root in (("attempts", attempts_root), ("snapshots", snapshots_root)):
        observed_root = root.lstat()
        if (
            not stat.S_ISDIR(observed_root.st_mode)
            or stat.S_IMODE(observed_root.st_mode) != 0o700
            or observed_root.st_uid != os.geteuid()
            or root.resolve(strict=True) != root
        ):
            _fail("local collection chain root changed")
        for current, directories, filenames in os.walk(
            root, topdown=True, followlinks=False
        ):
            current_path = Path(current)
            for path in (current_path, *(current_path / name for name in directories)):
                observed = path.lstat()
                relative = "." if path == root else path.relative_to(root).as_posix()
                key = f"{label}/{relative}"
                fact = ("DIRECTORY", *(getattr(observed, field) for field in stable_fields))
                previous = snapshot.get(key)
                if (
                    not stat.S_ISDIR(observed.st_mode)
                    or previous is not None
                    and previous != fact
                ):
                    _fail("local collection chain directory changed during snapshot")
                snapshot[key] = fact
            for name in filenames:
                path = current_path / name
                observed = path.lstat()
                relative = path.relative_to(root).as_posix()
                if (
                    not stat.S_ISREG(observed.st_mode)
                    or stat.S_IMODE(observed.st_mode) != 0o400
                    or observed.st_uid != os.geteuid()
                    or observed.st_nlink != 1
                ):
                    _fail("local collection chain contains an unsafe file")
                byte_count, sha256 = _hash_fixed_artifact(
                    path, MAX_SOURCE_CAPSULE_BYTES
                )
                after = path.lstat()
                if any(
                    getattr(observed, field) != getattr(after, field)
                    for field in stable_fields
                ):
                    _fail("local collection chain file changed during snapshot")
                snapshot[f"{label}/{relative}"] = (
                    "FILE",
                    *(getattr(after, field) for field in stable_fields),
                    byte_count,
                    sha256,
                )
    return snapshot


def _verify_collection_chain_link(
    *, attempt: dict[str, Any], manifest: dict[str, Any], ordinal: int,
    content_directory_name: str, local_launch_attempt_id: str,
    previous_manifest: dict[str, Any] | None,
    expected_prepare_receipt_id: str,
    expected_collection_input_provenance: str,
    expected_remote_paths: dict[str, str],
) -> None:
    expected_previous_ordinal = None if ordinal == 1 else ordinal - 1
    expected_previous_id = (
        None if previous_manifest is None else previous_manifest["collection_manifest_id"]
    )
    expected_previous_status = (
        None if previous_manifest is None else previous_manifest["collection_status"]
    )
    if (
        attempt.get("collection_ordinal") != ordinal
        or manifest.get("collection_ordinal") != ordinal
        or manifest.get("collection_manifest_id") != content_directory_name
        or attempt.get("local_launch_attempt_id") != local_launch_attempt_id
        or manifest.get("local_launch_attempt_id") != local_launch_attempt_id
        or manifest.get("collection_attempt_id") != attempt.get("collection_attempt_id")
        or attempt.get("transport_target_alias") != authority.REMOTE_HOST_ALIAS
        or manifest.get("transport_target_alias") != authority.REMOTE_HOST_ALIAS
        or manifest.get("prepare_receipt_id") != expected_prepare_receipt_id
        or manifest.get("collection_input_provenance")
        != expected_collection_input_provenance
        or manifest.get("remote_process_started_by_collector") is not False
        or manifest.get("remote_path_mutated_by_collector") is not False
        or attempt.get("previous_collection_ordinal") != expected_previous_ordinal
        or attempt.get("previous_collection_manifest_id") != expected_previous_id
        or attempt.get("previous_collection_status") != expected_previous_status
        or manifest.get("previous_collection_ordinal") != expected_previous_ordinal
        or manifest.get("previous_collection_manifest_id") != expected_previous_id
        or manifest.get("previous_collection_status") != expected_previous_status
        or attempt.get("remote_collection_is_read_only") is not True
        or attempt.get("same_identity_execution_retry_authorized") is not False
        or attempt.get("same_collection_ordinal_retry_authorized") is not False
        or manifest.get("collection_is_read_only") is not True
        or manifest.get("same_identity_retry_authorized") is not False
        or manifest.get("continued_read_only_collection_allowed") is not True
        or manifest.get("snapshot_ordinal_root_relative")
        != f"{LOCAL_COLLECTION_SNAPSHOTS_NAME}/{ordinal:06d}"
        or manifest.get("snapshot_content_directory_name_is_manifest_id") is not True
        or manifest.get("collection_status")
        not in {
            "COMPLETE_TERMINAL",
            "COMPLETE_FAILURE",
            "AMBIGUOUS_INCOMPLETE_READ_ONLY_SNAPSHOT",
            COLLECTION_FAILURE_STATUS,
        }
        or manifest.get("further_action_if_incomplete")
        != (
            "NEXT_COLLECTION_ORDINAL_ONLY"
            if manifest.get("collection_status")
            in {
                "AMBIGUOUS_INCOMPLETE_READ_ONLY_SNAPSHOT",
                COLLECTION_FAILURE_STATUS,
            }
            else "NO_EXECUTION_ACTION_OPTIONAL_NEXT_READ_ONLY_COLLECTION"
        )
        or manifest.get("artifact_inventory_count")
        != len(manifest.get("artifact_inventory", []))
        or type(manifest.get("transport_ambiguity_present")) is not bool
    ):
        _fail("previous collection chain identity or no-retry semantics changed")
    inventory = manifest.get("artifact_inventory")
    if type(inventory) is not list or {
        row.get("role"): row.get("remote_path")
        for row in inventory
        if type(row) is dict and type(row.get("role")) is str
    } != expected_remote_paths:
        _fail("previous collection chain remote role paths changed")


def _verify_previous_collection_chain(
    *, attempts_root: Path, snapshots_root: Path, expected_count: int,
    local_launch_attempt_id: str,
    expected_prepare_receipt_id: str,
    expected_collection_input_provenance: str,
    expected_remote_paths: dict[str, str],
    allowed_open_ordinal: int | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    chain_before = _snapshot_local_collection_chain(attempts_root, snapshots_root)
    expected_attempt_names = {f"{ordinal:06d}.json" for ordinal in range(1, expected_count + 1)}
    observed_attempt_names = {entry.name for entry in attempts_root.iterdir()}
    expected_snapshot_names = {f"{ordinal:06d}" for ordinal in range(1, expected_count + 1)}
    observed_snapshot_names = {entry.name for entry in snapshots_root.iterdir()}
    allowed_attempt_names = set(expected_attempt_names)
    allowed_snapshot_names = set(expected_snapshot_names)
    if allowed_open_ordinal is not None:
        if allowed_open_ordinal != expected_count + 1:
            _fail("open collection ordinal differs from the next chain ordinal")
        allowed_attempt_names.add(f"{allowed_open_ordinal:06d}.json")
        allowed_snapshot_names.add(f"{allowed_open_ordinal:06d}")
    if (
        not observed_attempt_names <= allowed_attempt_names
        or not expected_snapshot_names <= observed_snapshot_names <= allowed_snapshot_names
    ):
        _fail("local collection chain has a branch, gap, rollback, or extra entry")
    previous_attempt: dict[str, Any] | None = None
    previous_manifest: dict[str, Any] | None = None
    chain_state = _empty_collection_chain_state()
    for ordinal in range(1, expected_count + 1):
        attempt_path = attempts_root / f"{ordinal:06d}.json"
        ordinal_root = snapshots_root / f"{ordinal:06d}"
        observed = ordinal_root.lstat()
        if (
            not stat.S_ISDIR(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o700
            or observed.st_uid != os.geteuid()
            or ordinal_root.resolve(strict=True) != ordinal_root
        ):
            _fail("previous collection ordinal root changed")
        content_names = [entry.name for entry in ordinal_root.iterdir()]
        if len(content_names) != 1 or re.fullmatch(r"[0-9a-f]{64}", content_names[0]) is None:
            _fail("previous collection snapshot is not uniquely content-addressed")
        content_root = ordinal_root / content_names[0]
        recovery_name = (
            f"{COLLECTION_RECOVERY_MANIFEST_PREFIX}{content_names[0]}.json"
        )
        recovery_path = content_root / recovery_name
        try:
            recovery_observed = recovery_path.lstat()
        except FileNotFoundError:
            recovery_observed = None
        if recovery_observed is not None:
            manifest = _verify_collection_recovery_manifest_document(
                processio.read_fixed_artifact(recovery_path, 64 * 1024**2)
            )
            attempt = _verify_collection_recovery_snapshot_storage(
                content_root, manifest, attempt_path=attempt_path
            )
        else:
            attempt = _verify_collected_id_document(
                processio.read_fixed_artifact(attempt_path, 4 * 1024**2),
                label="previous collection attempt",
                schema=COLLECTION_ATTEMPT_SCHEMA,
                id_key="collection_attempt_id",
                domain="acfqp:v42-remote-ordinal2:collection-attempt",
                exact_payload_fields=_COLLECTION_ATTEMPT_PAYLOAD_FIELDS,
            )
            attempt_storage, attempt_raw = _retained_attempt_storage_fact(
                attempt_path, expected_attempt=attempt, durable=True
            )
            if (
                attempt_storage["state"] != "EXACT_CANONICAL"
                or attempt_raw != canonical_json_bytes(attempt)
            ):
                _fail("previous collection attempt storage changed")
            manifest = _verify_collected_id_document(
                processio.read_fixed_artifact(
                    content_root / "COLLECTION_MANIFEST.json", 64 * 1024**2
                ),
                label="previous collection manifest",
                schema=COLLECTION_MANIFEST_SCHEMA,
                id_key="collection_manifest_id",
                domain="acfqp:v42-remote-ordinal2:collection-manifest",
                exact_payload_fields=_COLLECTION_MANIFEST_PAYLOAD_FIELDS,
            )
            _verify_collection_snapshot_storage(content_root, manifest)
        if manifest.get("collection_status") == COLLECTION_FAILURE_STATUS:
            _verify_collection_failure_document(
                manifest.get("collection_failure"), collection_attempt=attempt
            )
        _verify_collection_chain_link(
            attempt=attempt,
            manifest=manifest,
            ordinal=ordinal,
            content_directory_name=content_names[0],
            local_launch_attempt_id=local_launch_attempt_id,
            previous_manifest=previous_manifest,
            expected_prepare_receipt_id=expected_prepare_receipt_id,
            expected_collection_input_provenance=(
                expected_collection_input_provenance
            ),
            expected_remote_paths=expected_remote_paths,
        )
        chain_state = _verify_and_advance_collection_observation(
            manifest, chain_state
        )
        previous_attempt = attempt
        previous_manifest = manifest
    chain_after = _snapshot_local_collection_chain(attempts_root, snapshots_root)
    if chain_after != chain_before:
        _fail("local collection chain changed across whole-chain verification")
    return previous_attempt, previous_manifest, chain_state


def _build_expected_collection_attempt(
    *, collection_ordinal: int, local_launch_attempt_id: str,
    previous_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "schema": COLLECTION_ATTEMPT_SCHEMA,
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "local_launch_attempt_id": local_launch_attempt_id,
        "collection_ordinal": collection_ordinal,
        "previous_collection_ordinal": (
            None if previous_manifest is None else collection_ordinal - 1
        ),
        "previous_collection_manifest_id": (
            None if previous_manifest is None else previous_manifest["collection_manifest_id"]
        ),
        "previous_collection_status": (
            None if previous_manifest is None else previous_manifest["collection_status"]
        ),
        "transport_target_alias": authority.REMOTE_HOST_ALIAS,
        "remote_collection_is_read_only": True,
        "same_identity_execution_retry_authorized": False,
        "same_collection_ordinal_retry_authorized": False,
    }
    return {
        **payload,
        "collection_attempt_id": _content_id(
            "acfqp:v42-remote-ordinal2:collection-attempt", payload
        ),
    }


def _begin_collection_snapshot(
    *, local_control_root: Path, collection_ordinal: int,
    local_launch_attempt_id: str,
    prepare_receipt_id: str, collection_input_provenance: str,
    observed_transport_ambiguity_id: str | None,
    remote_source_root: Path, remote_control_root: Path,
) -> tuple[dict[str, Any], Path, dict[str, Any] | None, dict[str, Any]]:
    if type(collection_ordinal) is not int or collection_ordinal <= 0:
        _fail("collection ordinal must be one positive integer")
    attempts_root = _ensure_local_append_container(
        local_control_root, LOCAL_COLLECTION_ATTEMPTS_NAME
    )
    snapshots_root = _ensure_local_append_container(
        local_control_root, LOCAL_COLLECTION_SNAPSHOTS_NAME
    )
    expected_remote_paths = _collection_remote_path_map(
        remote_source_root, remote_control_root
    )
    _, previous_manifest, chain_state = _verify_previous_collection_chain(
        attempts_root=attempts_root,
        snapshots_root=snapshots_root,
        expected_count=collection_ordinal - 1,
        local_launch_attempt_id=local_launch_attempt_id,
        expected_prepare_receipt_id=prepare_receipt_id,
        expected_collection_input_provenance=collection_input_provenance,
        expected_remote_paths=_collection_remote_path_map(
            remote_source_root, remote_control_root
        ),
    )
    retained_ambiguity_id = chain_state["transport_ambiguity_id"]
    if (
        previous_manifest is not None
        and observed_transport_ambiguity_id != retained_ambiguity_id
    ):
        _fail(
            "transport ambiguity appeared, disappeared, or changed after the first "
            "collection attempt"
        )
    current_remote_paths = {
        role: str(path)
        for role, path, _ in _collection_sources(
            remote_source_root, remote_control_root
        )
    }
    if chain_state["remote_paths"] and chain_state["remote_paths"] != current_remote_paths:
        _fail("collection mirror roots changed before collection attempt publication")
    attempt = _build_expected_collection_attempt(
        collection_ordinal=collection_ordinal,
        local_launch_attempt_id=local_launch_attempt_id,
        previous_manifest=previous_manifest,
    )
    processio.write_once(
        attempts_root / f"{collection_ordinal:06d}.json",
        canonical_json_bytes(attempt),
    )
    ordinal_root = snapshots_root / f"{collection_ordinal:06d}"
    processio.create_one_shot_root(
        ordinal_root, expected_parent=snapshots_root
    )
    staging_root = ordinal_root / "PENDING"
    processio.create_one_shot_root(staging_root, expected_parent=ordinal_root)
    return attempt, staging_root, previous_manifest, chain_state


def _build_collection_manifest(
    *, collection_attempt: dict[str, Any], prepare_receipt_id: str,
    collection_status: str, artifact_inventory: list[dict[str, Any]],
    transport_ambiguity: dict[str, Any] | None,
    collection_failure: dict[str, Any] | None,
    collection_input_provenance: str,
) -> dict[str, Any]:
    if collection_input_provenance not in {
        "FIXED_REMOTE_PATHS", "LOCAL_READ_ONLY_MIRROR"
    }:
        _fail("collection input provenance changed")
    ambiguity_state = "PRESENT" if transport_ambiguity is not None else "ABSENT"
    payload = {
        "schema": COLLECTION_MANIFEST_SCHEMA,
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "collection_attempt_id": collection_attempt["collection_attempt_id"],
        "collection_ordinal": collection_attempt["collection_ordinal"],
        "previous_collection_ordinal": collection_attempt[
            "previous_collection_ordinal"
        ],
        "previous_collection_manifest_id": collection_attempt[
            "previous_collection_manifest_id"
        ],
        "previous_collection_status": collection_attempt[
            "previous_collection_status"
        ],
        "local_launch_attempt_id": collection_attempt["local_launch_attempt_id"],
        "prepare_receipt_id": prepare_receipt_id,
        "transport_target_alias": authority.REMOTE_HOST_ALIAS,
        "collection_input_provenance": collection_input_provenance,
        "collection_status": collection_status,
        "transport_ambiguity_present": transport_ambiguity is not None,
        "transport_ambiguity_id": (
            None
            if transport_ambiguity is None
            else transport_ambiguity["transport_ambiguity_id"]
        ),
        "transport_ambiguity_observation_state": ambiguity_state,
        "collection_failure": collection_failure,
        "artifact_inventory": artifact_inventory,
        "artifact_inventory_count": len(artifact_inventory),
        "remote_process_started_by_collector": False,
        "remote_path_mutated_by_collector": False,
        "collection_is_read_only": True,
        "same_identity_retry_authorized": False,
        "continued_read_only_collection_allowed": True,
        "further_action_if_incomplete": (
            "NEXT_COLLECTION_ORDINAL_ONLY"
            if collection_status
            in {"AMBIGUOUS_INCOMPLETE_READ_ONLY_SNAPSHOT", COLLECTION_FAILURE_STATUS}
            else "NO_EXECUTION_ACTION_OPTIONAL_NEXT_READ_ONLY_COLLECTION"
        ),
        "snapshot_ordinal_root_relative": (
            f"{LOCAL_COLLECTION_SNAPSHOTS_NAME}/"
            f"{collection_attempt['collection_ordinal']:06d}"
        ),
        "snapshot_content_directory_name_is_manifest_id": True,
    }
    return {
        **payload,
        "collection_manifest_id": _content_id(
            "acfqp:v42-remote-ordinal2:collection-manifest", payload
        ),
    }


def _unobserved_collection_inventory(
    remote_source_root: Path, remote_control_root: Path
) -> list[dict[str, Any]]:
    return [
        {
            "role": role,
            "remote_path": str(source),
            "state": COLLECTION_UNOBSERVED_STATE,
            "retained_relative_path": None,
            "byte_count": None,
            "sha256": None,
        }
        for role, source, _ in _collection_sources(
            remote_source_root, remote_control_root
        )
    ]


def _validate_next_collection_context(
    *, previous_manifest: dict[str, Any] | None, chain_state: dict[str, Any],
    observed_transport_ambiguity_id: str | None,
    remote_source_root: Path, remote_control_root: Path,
) -> None:
    retained_ambiguity_id = chain_state["transport_ambiguity_id"]
    if (
        previous_manifest is not None
        and observed_transport_ambiguity_id != retained_ambiguity_id
    ):
        _fail(
            "transport ambiguity appeared, disappeared, or changed after the first "
            "collection attempt"
        )
    current_remote_paths = {
        role: str(path)
        for role, path, _ in _collection_sources(
            remote_source_root, remote_control_root
        )
    }
    if chain_state["remote_paths"] and chain_state["remote_paths"] != current_remote_paths:
        _fail("collection mirror roots changed before collection attempt publication")


def _build_collection_recovery_manifest(
    *, collection_attempt: dict[str, Any], prepare_receipt_id: str,
    remote_source_root: Path, remote_control_root: Path,
    transport_ambiguity: dict[str, Any] | None,
    collection_input_provenance: str,
    collection_attempt_storage: dict[str, Any],
    recovery_root_fact: dict[str, Any],
    residual_inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    failure = _build_collection_failure_document(
        collection_attempt=collection_attempt,
        failure_stage="LOCAL_COLLECTION_INTERRUPTION_RECOVERY",
        failure_type="InterruptedLocalCollectionPublication",
        failure_message=(
            "a prior local collection publication was interrupted; this ordinal "
            "was closed from retained local bytes without reading the remote mirror"
        ),
    )
    base = _build_collection_manifest(
        collection_attempt=collection_attempt,
        prepare_receipt_id=prepare_receipt_id,
        collection_status=COLLECTION_FAILURE_STATUS,
        artifact_inventory=_unobserved_collection_inventory(
            remote_source_root, remote_control_root
        ),
        transport_ambiguity=transport_ambiguity,
        collection_failure=failure,
        collection_input_provenance=collection_input_provenance,
    )
    payload = {
        key: value for key, value in base.items() if key != "collection_manifest_id"
    }
    payload.update(
        {
            "schema": COLLECTION_RECOVERY_MANIFEST_SCHEMA,
            "snapshot_kind": "LOCAL_INTERRUPTION_RECOVERY",
            "remote_read_performed_for_snapshot": False,
            "expected_collection_attempt": collection_attempt,
            "collection_attempt_storage": collection_attempt_storage,
            "recovery_root_fact": recovery_root_fact,
            "residual_inventory": residual_inventory,
            "residual_inventory_count": len(residual_inventory),
            "recovery_generation": 1
            + sum(
                1
                for row in residual_inventory
                if "/" not in row["relative_path"]
                and row["entry_type"] == "REGULAR_FILE"
                and re.fullmatch(
                    re.escape(COLLECTION_RECOVERY_MANIFEST_PREFIX)
                    + r"[0-9a-f]{64}\.json",
                    row["relative_path"],
                )
                is not None
            ),
            "same_ordinal_remote_observation_retry_performed": False,
            "recovery_publication_semantics": (
                "SAME_ORDINAL_LOCAL_TYPED_CLOSE_WITHOUT_REMOTE_REREAD"
            ),
        }
    )
    manifest = {
        **payload,
        "collection_manifest_id": _content_id(
            "acfqp:v42-remote-ordinal2:collection-recovery-manifest", payload
        ),
    }
    _verify_collection_recovery_manifest_document(canonical_json_bytes(manifest))
    _verify_collection_failure_document(
        failure, collection_attempt=collection_attempt
    )
    return manifest


def _publish_resumed_collection_snapshot(
    *, local_control_root: Path, collection_attempt: dict[str, Any],
    manifest: dict[str, Any], staging_root: Path,
    expected_prepare_receipt_id: str,
    expected_collection_input_provenance: str,
    expected_remote_paths: dict[str, str],
) -> dict[str, Any]:
    ordinal_root = staging_root.parent
    _fsync_collection_recovery_references(
        local_control_root=local_control_root,
        collection_ordinal=collection_attempt["collection_ordinal"],
        staging_root=staging_root,
    )
    attempt_path = (
        local_control_root
        / LOCAL_COLLECTION_ATTEMPTS_NAME
        / f"{collection_attempt['collection_ordinal']:06d}.json"
    )
    if manifest.get("schema") == COLLECTION_RECOVERY_MANIFEST_SCHEMA:
        if _verify_collection_recovery_snapshot_storage(
            staging_root, manifest, attempt_path=attempt_path
        ) != collection_attempt:
            _fail("durable pending recovery attempt changed")
    else:
        attempt_storage, attempt_raw = _retained_attempt_storage_fact(
            attempt_path, expected_attempt=collection_attempt, durable=True
        )
        if (
            attempt_storage["state"] != "EXACT_CANONICAL"
            or attempt_raw != canonical_json_bytes(collection_attempt)
        ):
            _fail("durable pending ordinary attempt changed")
        _verify_collection_snapshot_storage(staging_root, manifest)
    processio.rename_noreplace(
        ordinal_root, "PENDING", manifest["collection_manifest_id"]
    )
    processio.fsync_directory(ordinal_root.parent)
    _, verified, _ = _verify_previous_collection_chain(
        attempts_root=local_control_root / LOCAL_COLLECTION_ATTEMPTS_NAME,
        snapshots_root=local_control_root / LOCAL_COLLECTION_SNAPSHOTS_NAME,
        expected_count=collection_attempt["collection_ordinal"],
        local_launch_attempt_id=collection_attempt["local_launch_attempt_id"],
        expected_prepare_receipt_id=expected_prepare_receipt_id,
        expected_collection_input_provenance=(
            expected_collection_input_provenance
        ),
        expected_remote_paths=expected_remote_paths,
    )
    if verified != manifest:
        _fail("resumed collection snapshot readback changed")
    return manifest


def _verify_pending_ordinary_snapshot(
    *, staging_root: Path, attempt_path: Path,
    expected_attempt: dict[str, Any], previous_manifest: dict[str, Any] | None,
    chain_state: dict[str, Any], expected_prepare_receipt_id: str,
    expected_collection_input_provenance: str,
    expected_remote_paths: dict[str, str],
) -> dict[str, Any] | None:
    if {entry.name for entry in staging_root.iterdir()} != {
        "artifacts", "COLLECTION_MANIFEST.json",
    }:
        return None
    attempt_storage, attempt_raw = _retained_attempt_storage_fact(
        attempt_path, expected_attempt=expected_attempt, durable=True
    )
    if (
        attempt_storage["state"] != "EXACT_CANONICAL"
        or attempt_raw != canonical_json_bytes(expected_attempt)
    ):
        return None
    try:
        manifest_raw = processio.read_fixed_artifact(
            staging_root / "COLLECTION_MANIFEST.json", 64 * 1024**2
        )
        parsed_manifest = _canonical_document(
            manifest_raw, "pending ordinary collection candidate"
        )
    except (OSError, ValueError, V42RemoteOrdinal2RunnerError, processio.V42RemoteOrdinal2ProcessError):
        return None
    manifest = _verify_collected_id_document(
        canonical_json_bytes(parsed_manifest),
        label="pending complete collection manifest",
        schema=COLLECTION_MANIFEST_SCHEMA,
        id_key="collection_manifest_id",
        domain="acfqp:v42-remote-ordinal2:collection-manifest",
        exact_payload_fields=_COLLECTION_MANIFEST_PAYLOAD_FIELDS,
    )
    _verify_collection_snapshot_storage(staging_root, manifest)
    if manifest.get("collection_status") == COLLECTION_FAILURE_STATUS:
        _verify_collection_failure_document(
            manifest.get("collection_failure"), collection_attempt=expected_attempt
        )
    _verify_collection_chain_link(
        attempt=expected_attempt,
        manifest=manifest,
        ordinal=expected_attempt["collection_ordinal"],
        content_directory_name=manifest["collection_manifest_id"],
        local_launch_attempt_id=expected_attempt["local_launch_attempt_id"],
        previous_manifest=previous_manifest,
        expected_prepare_receipt_id=expected_prepare_receipt_id,
        expected_collection_input_provenance=expected_collection_input_provenance,
        expected_remote_paths=expected_remote_paths,
    )
    _verify_and_advance_collection_observation(manifest, chain_state)
    return manifest


def _verify_pending_recovery_snapshot(
    *, staging_root: Path, attempt_path: Path,
    expected_attempt: dict[str, Any], previous_manifest: dict[str, Any] | None,
    chain_state: dict[str, Any], expected_prepare_receipt_id: str,
    expected_collection_input_provenance: str,
    expected_remote_paths: dict[str, str],
) -> dict[str, Any] | None:
    complete: list[dict[str, Any]] = []
    for entry in staging_root.iterdir():
        if re.fullmatch(
            re.escape(COLLECTION_RECOVERY_MANIFEST_PREFIX)
            + r"[0-9a-f]{64}\.json",
            entry.name,
        ) is None:
            continue
        try:
            raw = processio.read_fixed_artifact(entry, 64 * 1024**2)
            parsed = _canonical_document(raw, "pending collection recovery candidate")
        except (OSError, ValueError, V42RemoteOrdinal2RunnerError, processio.V42RemoteOrdinal2ProcessError):
            continue
        # A canonical document in the reserved complete-name namespace is a
        # publication claim, not an ignorable partial.  It must verify fully.
        manifest = _verify_collection_recovery_manifest_document(
            canonical_json_bytes(parsed)
        )
        expected_name = (
            f"{COLLECTION_RECOVERY_MANIFEST_PREFIX}"
            f"{manifest['collection_manifest_id']}.json"
        )
        if entry.name != expected_name:
            _fail("collection recovery manifest filename changed")
        recovered_attempt = _verify_collection_recovery_snapshot_storage(
            staging_root, manifest, attempt_path=attempt_path
        )
        if recovered_attempt != expected_attempt:
            _fail("pending collection recovery expected attempt changed")
        _verify_collection_failure_document(
            manifest.get("collection_failure"), collection_attempt=expected_attempt
        )
        _verify_collection_chain_link(
            attempt=expected_attempt,
            manifest=manifest,
            ordinal=expected_attempt["collection_ordinal"],
            content_directory_name=manifest["collection_manifest_id"],
            local_launch_attempt_id=expected_attempt["local_launch_attempt_id"],
            previous_manifest=previous_manifest,
            expected_prepare_receipt_id=expected_prepare_receipt_id,
            expected_collection_input_provenance=(
                expected_collection_input_provenance
            ),
            expected_remote_paths=expected_remote_paths,
        )
        _verify_and_advance_collection_observation(manifest, chain_state)
        complete.append(manifest)
    if len(complete) > 1:
        _fail("pending collection contains multiple complete recovery manifests")
    return None if not complete else complete[0]


def _recover_interrupted_collection_if_present(
    *, local_control_root: Path, collection_ordinal: int,
    local_launch_attempt_id: str, prepare_receipt_id: str,
    observed_transport_ambiguity: dict[str, Any] | None,
    remote_source_root: Path, remote_control_root: Path,
    collection_input_provenance: str,
) -> dict[str, Any] | None:
    """Close or finish one prior local publication without reading remote paths."""

    if type(collection_ordinal) is not int or collection_ordinal <= 0:
        _fail("collection ordinal must be one positive integer")
    attempts_root = _ensure_local_append_container(
        local_control_root, LOCAL_COLLECTION_ATTEMPTS_NAME
    )
    snapshots_root = _ensure_local_append_container(
        local_control_root, LOCAL_COLLECTION_SNAPSHOTS_NAME
    )
    expected_remote_paths = _collection_remote_path_map(
        remote_source_root, remote_control_root
    )
    _, previous_manifest, chain_state = _verify_previous_collection_chain(
        attempts_root=attempts_root,
        snapshots_root=snapshots_root,
        expected_count=collection_ordinal - 1,
        local_launch_attempt_id=local_launch_attempt_id,
        expected_prepare_receipt_id=prepare_receipt_id,
        expected_collection_input_provenance=collection_input_provenance,
        expected_remote_paths=expected_remote_paths,
        allowed_open_ordinal=collection_ordinal,
    )
    observed_ambiguity_id = (
        None
        if observed_transport_ambiguity is None
        else observed_transport_ambiguity["transport_ambiguity_id"]
    )
    _validate_next_collection_context(
        previous_manifest=previous_manifest,
        chain_state=chain_state,
        observed_transport_ambiguity_id=observed_ambiguity_id,
        remote_source_root=remote_source_root,
        remote_control_root=remote_control_root,
    )
    expected_attempt = _build_expected_collection_attempt(
        collection_ordinal=collection_ordinal,
        local_launch_attempt_id=local_launch_attempt_id,
        previous_manifest=previous_manifest,
    )
    attempt_path = attempts_root / f"{collection_ordinal:06d}.json"
    ordinal_root = snapshots_root / f"{collection_ordinal:06d}"
    try:
        attempt_path.lstat()
        attempt_present = True
    except FileNotFoundError:
        attempt_present = False
    try:
        ordinal_observed = ordinal_root.lstat()
    except FileNotFoundError:
        ordinal_observed = None
    if not attempt_present and ordinal_observed is None:
        return None
    if ordinal_observed is None:
        processio.create_one_shot_root(
            ordinal_root, expected_parent=snapshots_root
        )
        ordinal_observed = ordinal_root.lstat()
    if (
        not stat.S_ISDIR(ordinal_observed.st_mode)
        or stat.S_IMODE(ordinal_observed.st_mode) != 0o700
        or ordinal_observed.st_uid != os.geteuid()
        or ordinal_root.resolve(strict=True) != ordinal_root
    ):
        _fail("interrupted collection ordinal root is redirected or unsafe")
    names = {entry.name for entry in ordinal_root.iterdir()}
    if names and names != {"PENDING"}:
        if (
            len(names) != 1
            or re.fullmatch(r"[0-9a-f]{64}", next(iter(names))) is None
        ):
            _fail("interrupted collection ordinal has a branch or extra entry")
        _, verified, _ = _verify_previous_collection_chain(
            attempts_root=attempts_root,
            snapshots_root=snapshots_root,
            expected_count=collection_ordinal,
            local_launch_attempt_id=local_launch_attempt_id,
            expected_prepare_receipt_id=prepare_receipt_id,
            expected_collection_input_provenance=collection_input_provenance,
            expected_remote_paths=expected_remote_paths,
        )
        if verified is None:
            _fail("published collection snapshot disappeared during recovery")
        # The no-replace rename may have completed immediately before an
        # ordinal-directory fsync or readback interruption.  Verify the unique
        # published tree first, flush every retained leaf and directory link,
        # then verify the entire chain again.  This repairs only local
        # durability and never re-opens the remote mirror.
        published_root = ordinal_root / next(iter(names))
        _fsync_collection_recovery_references(
            local_control_root=local_control_root,
            collection_ordinal=collection_ordinal,
            staging_root=published_root,
        )
        _, durable_verified, _ = _verify_previous_collection_chain(
            attempts_root=attempts_root,
            snapshots_root=snapshots_root,
            expected_count=collection_ordinal,
            local_launch_attempt_id=local_launch_attempt_id,
            expected_prepare_receipt_id=prepare_receipt_id,
            expected_collection_input_provenance=collection_input_provenance,
            expected_remote_paths=expected_remote_paths,
        )
        if durable_verified != verified:
            _fail("published collection snapshot changed during durability recovery")
        return durable_verified
    staging_root = ordinal_root / "PENDING"
    if not names:
        processio.create_one_shot_root(staging_root, expected_parent=ordinal_root)
    else:
        staging_observed = staging_root.lstat()
        if (
            not stat.S_ISDIR(staging_observed.st_mode)
            or stat.S_IMODE(staging_observed.st_mode) != 0o700
            or staging_observed.st_uid != os.geteuid()
            or staging_root.resolve(strict=True) != staging_root
        ):
            _fail("interrupted collection PENDING root is redirected or unsafe")
    ordinary = _verify_pending_ordinary_snapshot(
        staging_root=staging_root,
        attempt_path=attempt_path,
        expected_attempt=expected_attempt,
        previous_manifest=previous_manifest,
        chain_state=chain_state,
        expected_prepare_receipt_id=prepare_receipt_id,
        expected_collection_input_provenance=collection_input_provenance,
        expected_remote_paths=expected_remote_paths,
    )
    if ordinary is not None:
        return _publish_resumed_collection_snapshot(
            local_control_root=local_control_root,
            collection_attempt=expected_attempt,
            manifest=ordinary,
            staging_root=staging_root,
            expected_prepare_receipt_id=prepare_receipt_id,
            expected_collection_input_provenance=collection_input_provenance,
            expected_remote_paths=expected_remote_paths,
        )
    recovery = _verify_pending_recovery_snapshot(
        staging_root=staging_root,
        attempt_path=attempt_path,
        expected_attempt=expected_attempt,
        previous_manifest=previous_manifest,
        chain_state=chain_state,
        expected_prepare_receipt_id=prepare_receipt_id,
        expected_collection_input_provenance=collection_input_provenance,
        expected_remote_paths=expected_remote_paths,
    )
    if recovery is not None:
        return _publish_resumed_collection_snapshot(
            local_control_root=local_control_root,
            collection_attempt=expected_attempt,
            manifest=recovery,
            staging_root=staging_root,
            expected_prepare_receipt_id=prepare_receipt_id,
            expected_collection_input_provenance=collection_input_provenance,
            expected_remote_paths=expected_remote_paths,
        )
    _fsync_collection_recovery_references(
        local_control_root=local_control_root,
        collection_ordinal=collection_ordinal,
        staging_root=staging_root,
    )
    attempt_storage, _ = _retained_attempt_storage_fact(
        attempt_path, expected_attempt=expected_attempt, durable=True
    )
    recovery_root_fact, residual_inventory = (
        _snapshot_collection_recovery_residual(
            staging_root, excluded_top_level_name=None, durable=True
        )
    )
    processio.fsync_directory(staging_root.parent.parent)
    processio.fsync_directory(local_control_root)
    manifest = _build_collection_recovery_manifest(
        collection_attempt=expected_attempt,
        prepare_receipt_id=prepare_receipt_id,
        remote_source_root=remote_source_root,
        remote_control_root=remote_control_root,
        transport_ambiguity=observed_transport_ambiguity,
        collection_input_provenance=collection_input_provenance,
        collection_attempt_storage=attempt_storage,
        recovery_root_fact=recovery_root_fact,
        residual_inventory=residual_inventory,
    )
    recovery_name = (
        f"{COLLECTION_RECOVERY_MANIFEST_PREFIX}"
        f"{manifest['collection_manifest_id']}.json"
    )
    processio.write_once(
        staging_root / recovery_name, canonical_json_bytes(manifest)
    )
    recovered_attempt = _verify_collection_recovery_snapshot_storage(
        staging_root, manifest, attempt_path=attempt_path
    )
    if recovered_attempt != expected_attempt:
        _fail("new collection recovery expected attempt changed")
    _verify_collection_failure_document(
        manifest["collection_failure"], collection_attempt=expected_attempt
    )
    _verify_collection_chain_link(
        attempt=expected_attempt,
        manifest=manifest,
        ordinal=collection_ordinal,
        content_directory_name=manifest["collection_manifest_id"],
        local_launch_attempt_id=local_launch_attempt_id,
        previous_manifest=previous_manifest,
        expected_prepare_receipt_id=prepare_receipt_id,
        expected_collection_input_provenance=collection_input_provenance,
        expected_remote_paths=expected_remote_paths,
    )
    _verify_and_advance_collection_observation(manifest, chain_state)
    return _publish_resumed_collection_snapshot(
        local_control_root=local_control_root,
        collection_attempt=expected_attempt,
        manifest=manifest,
        staging_root=staging_root,
        expected_prepare_receipt_id=prepare_receipt_id,
        expected_collection_input_provenance=collection_input_provenance,
        expected_remote_paths=expected_remote_paths,
    )


def _publish_collection_snapshot(
    *, local_control_root: Path, collection_root: Path,
    collection_attempt: dict[str, Any], manifest: dict[str, Any],
    raw_by_role: dict[str, bytes], chain_state: dict[str, Any],
    previous_manifest: dict[str, Any] | None,
    expected_prepare_receipt_id: str,
    expected_collection_input_provenance: str,
    expected_remote_paths: dict[str, str],
) -> dict[str, Any]:
    _verify_collection_chain_link(
        attempt=collection_attempt,
        manifest=manifest,
        ordinal=collection_attempt["collection_ordinal"],
        content_directory_name=manifest["collection_manifest_id"],
        local_launch_attempt_id=collection_attempt["local_launch_attempt_id"],
        previous_manifest=previous_manifest,
        expected_prepare_receipt_id=expected_prepare_receipt_id,
        expected_collection_input_provenance=expected_collection_input_provenance,
        expected_remote_paths=expected_remote_paths,
    )
    _verify_and_advance_collection_observation(manifest, chain_state)
    if manifest.get("collection_status") == COLLECTION_FAILURE_STATUS:
        _verify_collection_failure_document(
            manifest.get("collection_failure"), collection_attempt=collection_attempt
        )
    artifact_root = collection_root / "artifacts"
    processio.create_one_shot_root(artifact_root, expected_parent=collection_root)
    retained_roles = {
        row["role"]
        for row in manifest["artifact_inventory"]
        if row["state"] == "EXACT_RETAINED"
    }
    if set(raw_by_role) != retained_roles:
        _fail("collection retained bytes differ from the manifest roles")
    for index, row in enumerate(manifest["artifact_inventory"]):
        if row["state"] != "EXACT_RETAINED":
            continue
        raw = raw_by_role[row["role"]]
        retained_name = f"{index:02d}_{row['role']}.bin"
        if (
            row["retained_relative_path"] != f"artifacts/{retained_name}"
            or row["byte_count"] != len(raw)
            or row["sha256"] != hashlib.sha256(raw).hexdigest()
        ):
            _fail("collection retained bytes changed before publication")
        processio.write_once(artifact_root / retained_name, raw)
    processio.write_once(
        collection_root / "COLLECTION_MANIFEST.json", canonical_json_bytes(manifest)
    )
    attempt_path = (
        local_control_root
        / LOCAL_COLLECTION_ATTEMPTS_NAME
        / f"{collection_attempt['collection_ordinal']:06d}.json"
    )
    attempt_storage, attempt_raw = _retained_attempt_storage_fact(
        attempt_path, expected_attempt=collection_attempt, durable=True
    )
    if (
        attempt_storage["state"] != "EXACT_CANONICAL"
        or attempt_raw != canonical_json_bytes(collection_attempt)
    ):
        _fail("new collection attempt changed before publication")
    _verify_collection_snapshot_storage(collection_root, manifest)
    ordinal_root = collection_root.parent
    processio.rename_noreplace(
        ordinal_root, "PENDING", manifest["collection_manifest_id"]
    )
    processio.fsync_directory(ordinal_root.parent)
    _, verified, _ = _verify_previous_collection_chain(
        attempts_root=local_control_root / LOCAL_COLLECTION_ATTEMPTS_NAME,
        snapshots_root=local_control_root / LOCAL_COLLECTION_SNAPSHOTS_NAME,
        expected_count=collection_attempt["collection_ordinal"],
        local_launch_attempt_id=collection_attempt["local_launch_attempt_id"],
        expected_prepare_receipt_id=expected_prepare_receipt_id,
        expected_collection_input_provenance=(
            expected_collection_input_provenance
        ),
        expected_remote_paths=expected_remote_paths,
    )
    if verified != manifest:
        _fail("new collection snapshot readback changed")
    return manifest


def collect_remote_result_read_only_v42r1(
    *,
    remote_source_root: Path,
    remote_control_root: Path,
    local_control_root: Path,
    collection_ordinal: int,
    require_fixed_remote_paths: bool = True,
) -> dict[str, Any]:
    """Read a local mirror without spawning or mutating any remote process."""

    if (
        not remote_control_root.is_absolute()
        or not remote_source_root.is_absolute()
        or remote_source_root != remote_control_root / "source"
    ):
        _fail("collector source/control mirror roots are not one lexical snapshot")
    if require_fixed_remote_paths and (
        remote_source_root != authority.REMOTE_SOURCE_ROOT
        or remote_control_root != authority.REMOTE_ROOT
    ):
        _fail("collector remote paths differ from the fixed identity")
    collection_input_provenance = (
        "FIXED_REMOTE_PATHS"
        if require_fixed_remote_paths
        else "LOCAL_READ_ONLY_MIRROR"
    )
    try:
        observed_local_root = local_control_root.lstat()
    except FileNotFoundError as error:
        raise V42RemoteOrdinal2RunnerError(
            "collector local control root is absent"
        ) from error
    if (
        not local_control_root.is_absolute()
        or not stat.S_ISDIR(observed_local_root.st_mode)
        or stat.S_IMODE(observed_local_root.st_mode) != 0o700
        or observed_local_root.st_uid != os.geteuid()
        or local_control_root.resolve(strict=True) != local_control_root
    ):
        _fail("collector local control root is redirected or non-directory")
    _verify_local_control_inventory(
        local_control_root,
        allow_ambiguity=True,
        allow_collection_roots=True,
    )
    receipt_raw, receipt_control_before = _read_exact_local_control_observed(
        local_control_root / LOCAL_PREPARE_RECEIPT_NAME, 64 * 1024**2
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_raw,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
    )
    attempt_raw, attempt_control_before = _read_exact_local_control_observed(
        local_control_root / LOCAL_LAUNCH_ATTEMPT_NAME, 4 * 1024**2
    )
    attempt = verify_local_launch_attempt_v42r1(
        attempt_raw, prepare_receipt=receipt
    )
    ambiguity = _read_local_transport_ambiguity(
        local_control_root,
        local_launch_attempt_id=attempt["local_launch_attempt_id"],
    )
    ambiguity_path = local_control_root / LOCAL_TRANSPORT_AMBIGUITY_NAME
    ambiguity_control_before = None if ambiguity is None else ambiguity_path.lstat()
    recovered = _recover_interrupted_collection_if_present(
        local_control_root=local_control_root,
        collection_ordinal=collection_ordinal,
        local_launch_attempt_id=attempt["local_launch_attempt_id"],
        prepare_receipt_id=receipt["prepare_receipt_id"],
        observed_transport_ambiguity=ambiguity,
        remote_source_root=remote_source_root,
        remote_control_root=remote_control_root,
        collection_input_provenance=collection_input_provenance,
    )
    if recovered is not None:
        return recovered
    (
        collection_attempt,
        collection_root,
        previous_manifest,
        chain_state,
    ) = _begin_collection_snapshot(
        local_control_root=local_control_root,
        collection_ordinal=collection_ordinal,
        local_launch_attempt_id=attempt["local_launch_attempt_id"],
        prepare_receipt_id=receipt["prepare_receipt_id"],
        collection_input_provenance=collection_input_provenance,
        observed_transport_ambiguity_id=(
            None if ambiguity is None else ambiguity["transport_ambiguity_id"]
        ),
        remote_source_root=remote_source_root,
        remote_control_root=remote_control_root,
    )
    local_root_after_attempt = local_control_root.lstat()
    # No remote path has been opened before the append-only local attempt above.
    # A transport disconnect can therefore never leave an unbound collection
    # effect, and every later observation must use the next ordinal.
    inventory: list[dict[str, Any]] = []
    raw_by_role: dict[str, bytes] = {}
    stage = "REMOTE_ROOT_VALIDATION"
    try:
        root_observations: dict[Path, os.stat_result] = {}
        for label, root in (
            ("remote control", remote_control_root),
            ("remote source", remote_source_root),
        ):
            try:
                observed_root = root.lstat()
            except FileNotFoundError as error:
                raise V42RemoteOrdinal2RunnerError(
                    f"collector {label} root is absent"
                ) from error
            if (
                not root.is_absolute()
                or not stat.S_ISDIR(observed_root.st_mode)
                or stat.S_IMODE(observed_root.st_mode) != 0o700
                or observed_root.st_uid
                != (
                    authority.REMOTE_UID
                    if require_fixed_remote_paths
                    else os.geteuid()
                )
                or root.resolve(strict=True) != root
            ):
                _fail(f"collector {label} root is redirected or non-directory")
            root_observations[root] = observed_root
        stage = "REMOTE_TREE_INITIAL_SNAPSHOT"
        remote_tree_before = {
            root: authority._snapshot_transport_tree_metadata_v42r1(root)  # noqa: SLF001
            for root in (remote_control_root, remote_source_root)
        }

        parent_observations: dict[Path, os.stat_result | None] = {}
        file_observations: dict[Path, os.stat_result] = {}
        blocked_non_directory_parents: set[Path] = set()
        for index, (role, source, cap) in enumerate(
            _collection_sources(remote_source_root, remote_control_root)
        ):
            stage = f"REMOTE_{role}_OBSERVATION"
            try:
                before_parent = source.parent.lstat()
            except FileNotFoundError:
                before_parent = None
            if source.parent not in parent_observations:
                parent_observations[source.parent] = before_parent
            if before_parent is not None and not stat.S_ISDIR(before_parent.st_mode):
                declared_state: object = None
                if "LAUNCH_FAILURE" in raw_by_role:
                    declared_state = _canonical_document(
                        raw_by_role["LAUNCH_FAILURE"], "collected runner failure"
                    ).get("evidence_root_state")
                actual_state = (
                    "REGULAR_FILE"
                    if stat.S_ISREG(before_parent.st_mode)
                    else "NONREGULAR"
                )
                if (
                    source.parent
                    == remote_source_root / authority.EVIDENCE_ROOT_RELATIVE
                    and declared_state == actual_state
                ):
                    blocked_non_directory_parents.add(source.parent)
                    row = {
                        "role": role,
                        "remote_path": str(source),
                        "state": "ABSENT",
                        "retained_relative_path": None,
                        "byte_count": None,
                        "sha256": None,
                    }
                    _verify_artifact_observation_against_baseline(
                        row, chain_state["artifact_baseline"].get(role)
                    )
                    inventory.append(row)
                    continue
                _fail(f"collector source parent is non-directory: {role}")
            if (
                before_parent is not None
                and source.parent.resolve(strict=True) != source.parent
            ):
                _fail(f"collector source parent is redirected: {role}")
            try:
                before = source.lstat()
            except FileNotFoundError:
                try:
                    after_parent = source.parent.lstat()
                except FileNotFoundError:
                    if before_parent is not None:
                        _fail(f"collector source parent disappeared: {role}")
                else:
                    if before_parent is None or any(
                        getattr(before_parent, field) != getattr(after_parent, field)
                        for field in (
                            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
                            "st_mtime_ns", "st_ctime_ns",
                        )
                    ):
                        _fail(f"collector absent source parent changed: {role}")
                row = {
                    "role": role,
                    "remote_path": str(source),
                    "state": "ABSENT",
                    "retained_relative_path": None,
                    "byte_count": None,
                    "sha256": None,
                }
                _verify_artifact_observation_against_baseline(
                    row, chain_state["artifact_baseline"].get(role)
                )
                inventory.append(row)
                continue
            if before_parent is None:
                _fail(f"collector source parent appeared during read: {role}")
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid
                != (
                    authority.REMOTE_UID
                    if require_fixed_remote_paths
                    else os.geteuid()
                )
                or require_fixed_remote_paths
                and (
                    stat.S_IMODE(before.st_mode) != 0o400
                )
            ):
                _fail(f"collector source is nonregular, misowned, or unsafe: {role}")
            raw = processio.read_fixed_artifact(source, cap)
            after = source.lstat()
            after_parent = source.parent.lstat()
            stable = (
                "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size",
                "st_mtime_ns", "st_ctime_ns",
            )
            if any(getattr(before, field) != getattr(after, field) for field in stable):
                _fail(f"collector source changed during read: {role}")
            if before_parent is not None and any(
                getattr(before_parent, field) != getattr(after_parent, field)
                for field in (
                    "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
                    "st_mtime_ns", "st_ctime_ns",
                )
            ):
                _fail(f"collector source directory changed during read: {role}")
            file_observations[source] = after
            retained_name = f"{index:02d}_{role}.bin"
            row = {
                "role": role,
                "remote_path": str(source),
                "state": "EXACT_RETAINED",
                "retained_relative_path": f"artifacts/{retained_name}",
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            _verify_artifact_observation_against_baseline(
                row, chain_state["artifact_baseline"].get(role)
            )
            raw_by_role[role] = raw
            inventory.append(row)

        stage = "REMOTE_PHASE_INVENTORY_VALIDATION"
        _verify_remote_collection_known_inventory(
            remote_source_root=remote_source_root,
            remote_control_root=remote_control_root,
            raw_by_role=raw_by_role,
            receipt=receipt,
            require_fixed_remote_paths=require_fixed_remote_paths,
        )
        stage = "REMOTE_FILE_STABILITY_VALIDATION"
        root_stable_fields = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
            "st_mtime_ns", "st_ctime_ns",
        )
        file_stable_fields = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size",
            "st_mtime_ns", "st_ctime_ns",
        )
        for source, first_file in file_observations.items():
            try:
                final_file = source.lstat()
            except FileNotFoundError:
                _fail("collector source file disappeared across observation")
            if (
                not stat.S_ISREG(final_file.st_mode)
                or any(
                    getattr(first_file, field) != getattr(final_file, field)
                    for field in file_stable_fields
                )
            ):
                _fail("collector source file changed across observation")
        stage = "REMOTE_PARENT_STABILITY_VALIDATION"
        for parent, first_parent in parent_observations.items():
            try:
                final_parent = parent.lstat()
            except FileNotFoundError:
                if first_parent is not None:
                    _fail("collector source parent disappeared during observation")
                continue
            if parent in blocked_non_directory_parents:
                if (
                    first_parent is None
                    or stat.S_ISDIR(final_parent.st_mode)
                    or any(
                        getattr(first_parent, field) != getattr(final_parent, field)
                        for field in root_stable_fields
                    )
                ):
                    _fail("collector blocked source parent changed during observation")
                continue
            if (
                first_parent is None
                or not stat.S_ISDIR(final_parent.st_mode)
                or parent.resolve(strict=True) != parent
                or any(
                    getattr(first_parent, field) != getattr(final_parent, field)
                    for field in root_stable_fields
                )
            ):
                _fail("collector source parent changed during observation")
        stage = "REMOTE_ROOT_STABILITY_VALIDATION"
        for root, before_root in root_observations.items():
            after_root = root.lstat()
            if any(
                getattr(before_root, field) != getattr(after_root, field)
                for field in root_stable_fields
            ) or root.resolve(strict=True) != root:
                _fail("collector remote snapshot root changed during observation")
        stage = "REMOTE_TREE_FINAL_SNAPSHOT"
        remote_tree_after = {
            root: authority._snapshot_transport_tree_metadata_v42r1(root)  # noqa: SLF001
            for root in (remote_control_root, remote_source_root)
        }
        if remote_tree_after != remote_tree_before:
            _fail("collector remote tree changed across read-only observation")

        stage = "COLLECTED_ARTIFACT_VALIDATION"
        status = _verify_collected_artifacts(
            raw_by_role,
            local_receipt_raw=receipt_raw,
            receipt=receipt,
            local_attempt_raw=attempt_raw,
            local_attempt=attempt,
        )
        stage = "LOCAL_AMBIGUITY_REVALIDATION"
        ambiguity_after = _read_local_transport_ambiguity(
            local_control_root,
            local_launch_attempt_id=attempt["local_launch_attempt_id"],
        )
        if ambiguity_after != ambiguity:
            _fail("local transport ambiguity changed during collection")
        stage = "LOCAL_CONTROL_REVALIDATION"
        _verify_local_control_inventory(
            local_control_root,
            allow_ambiguity=True,
            allow_collection_roots=True,
        )
        receipt_after, receipt_control_after = _read_exact_local_control_observed(
            local_control_root / LOCAL_PREPARE_RECEIPT_NAME, 64 * 1024**2
        )
        attempt_after, attempt_control_after = _read_exact_local_control_observed(
            local_control_root / LOCAL_LAUNCH_ATTEMPT_NAME, 4 * 1024**2
        )
        local_stable_fields = (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size",
            "st_mtime_ns", "st_ctime_ns",
        )
        local_root_final = local_control_root.lstat()
        if (
            receipt_after != receipt_raw
            or attempt_after != attempt_raw
            or any(
                getattr(receipt_control_before, field)
                != getattr(receipt_control_after, field)
                or getattr(attempt_control_before, field)
                != getattr(attempt_control_after, field)
                for field in local_stable_fields
            )
            or any(
                getattr(local_root_after_attempt, field)
                != getattr(local_root_final, field)
                for field in local_stable_fields
            )
        ):
            _fail("local launch controls changed during collection")
        try:
            ambiguity_control_after = ambiguity_path.lstat()
        except FileNotFoundError:
            ambiguity_control_after = None
        if (
            (ambiguity_control_before is None)
            is not (ambiguity_control_after is None)
            or ambiguity_control_before is not None
            and any(
                getattr(ambiguity_control_before, field)
                != getattr(ambiguity_control_after, field)
                for field in local_stable_fields
            )
        ):
            _fail("local transport ambiguity identity changed during collection")
        stage = "CHAIN_MONOTONICITY_VALIDATION"
        manifest = _build_collection_manifest(
            collection_attempt=collection_attempt,
            prepare_receipt_id=receipt["prepare_receipt_id"],
            collection_status=status,
            artifact_inventory=inventory,
            transport_ambiguity=ambiguity,
            collection_failure=None,
            collection_input_provenance=collection_input_provenance,
        )
        _verify_and_advance_collection_observation(manifest, chain_state)
    except BaseException as error:
        failure = _build_collection_failure_document(
            collection_attempt=collection_attempt,
            failure_stage=stage,
            failure_type=type(error).__name__,
            failure_message=processio.bounded_message(error),
        )
        failure_manifest = _build_collection_manifest(
            collection_attempt=collection_attempt,
            prepare_receipt_id=receipt["prepare_receipt_id"],
            collection_status=COLLECTION_FAILURE_STATUS,
            artifact_inventory=_unobserved_collection_inventory(
                remote_source_root, remote_control_root
            ),
            transport_ambiguity=ambiguity,
            collection_failure=failure,
            collection_input_provenance=collection_input_provenance,
        )
        try:
            _publish_collection_snapshot(
                local_control_root=local_control_root,
                collection_root=collection_root,
                collection_attempt=collection_attempt,
                manifest=failure_manifest,
                raw_by_role={},
                chain_state=chain_state,
                previous_manifest=previous_manifest,
                expected_prepare_receipt_id=receipt["prepare_receipt_id"],
                expected_collection_input_provenance=collection_input_provenance,
                expected_remote_paths=_collection_remote_path_map(
                    remote_source_root, remote_control_root
                ),
            )
        except BaseException as publication_error:
            raise V42RemoteOrdinal2RunnerError(
                "collection observation failed and its typed local closure could not "
                f"be published: {processio.bounded_message(publication_error)}"
            ) from error
        raise
    return _publish_collection_snapshot(
        local_control_root=local_control_root,
        collection_root=collection_root,
        collection_attempt=collection_attempt,
        manifest=manifest,
        raw_by_role=raw_by_role,
        chain_state=chain_state,
        previous_manifest=previous_manifest,
        expected_prepare_receipt_id=receipt["prepare_receipt_id"],
        expected_collection_input_provenance=collection_input_provenance,
        expected_remote_paths=_collection_remote_path_map(
            remote_source_root, remote_control_root
        ),
    )


def _issue_local_cli() -> int:
    local_root = ROOT / LOCAL_CONTROL_ROOT_RELATIVE
    receipt_path = local_root / LOCAL_PREPARE_RECEIPT_NAME
    if not receipt_path.exists():
        _fail(
            "place the exact collected remote prepare receipt at the fixed local path first"
        )
    receipt_raw = processio.read_fixed_artifact(receipt_path, 64 * 1024**2)
    attempt = issue_local_launch_attempt_once_v42r1(
        local_control_root=local_root, prepare_receipt_raw=receipt_raw
    )
    sys.stdout.buffer.write(canonical_json_bytes(attempt) + b"\n")
    return 0


def _collect_cli(mirror_root: Path | None, collection_ordinal: int | None) -> int:
    if mirror_root is None or collection_ordinal is None:
        _fail("read-only collection requires one mirror root and collection ordinal")
    if not mirror_root.is_absolute():
        mirror_root = Path(os.path.abspath(mirror_root))
    manifest = collect_remote_result_read_only_v42r1(
        remote_source_root=mirror_root / "source",
        remote_control_root=mirror_root,
        local_control_root=ROOT / LOCAL_CONTROL_ROOT_RELATIVE,
        collection_ordinal=collection_ordinal,
        require_fixed_remote_paths=False,
    )
    sys.stdout.buffer.write(canonical_json_bytes(manifest) + b"\n")
    return 0


def _record_ambiguity_cli(
    *, classification: str | None, stdout_path: Path | None,
    stderr_path: Path | None,
) -> int:
    if classification is None or stdout_path is None or stderr_path is None:
        _fail("transport ambiguity requires classification and two local stream files")
    if not stdout_path.is_absolute():
        stdout_path = Path(os.path.abspath(stdout_path))
    if not stderr_path.is_absolute():
        stderr_path = Path(os.path.abspath(stderr_path))
    document = record_transport_ambiguity_once_v42r1(
        local_control_root=ROOT / LOCAL_CONTROL_ROOT_RELATIVE,
        classification=classification,
        transport_stdout=processio.read_fixed_artifact(
            stdout_path, MAX_TRANSPORT_STDOUT_BYTES
        ),
        transport_stderr=processio.read_fixed_artifact(
            stderr_path, MAX_TRANSPORT_STDERR_BYTES
        ),
    )
    sys.stdout.buffer.write(canonical_json_bytes(document) + b"\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or collect the fixed V42 remote ordinal-2 identity"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-remote", action="store_true")
    modes.add_argument("--launch-remote", action="store_true")
    modes.add_argument("--issue-local-launch-attempt", action="store_true")
    modes.add_argument("--record-ambiguous-disconnect", action="store_true")
    modes.add_argument("--collect-only-from-local-mirror", action="store_true")
    parser.add_argument("--local-mirror-root", type=Path)
    parser.add_argument("--collection-ordinal", type=int)
    parser.add_argument(
        "--transport-classification",
        choices=sorted(TRANSPORT_AMBIGUITY_CLASSIFICATIONS),
    )
    parser.add_argument("--transport-stdout-file", type=Path)
    parser.add_argument("--transport-stderr-file", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    ambiguity_arguments_present = any(
        value is not None
        for value in (
            arguments.transport_classification,
            arguments.transport_stdout_file,
            arguments.transport_stderr_file,
        )
    )
    if not arguments.collect_only_from_local_mirror and arguments.collection_ordinal is not None:
        _fail("collection ordinal is accepted only by read-only collection")
    if arguments.prepare_remote:
        if arguments.local_mirror_root is not None or ambiguity_arguments_present:
            _fail("remote prepare accepts no local collection arguments")
        return _prepare_remote()
    if arguments.launch_remote:
        if arguments.local_mirror_root is not None or ambiguity_arguments_present:
            _fail("remote launch accepts no local collection arguments")
        return _launch_remote()
    if arguments.issue_local_launch_attempt:
        if arguments.local_mirror_root is not None or ambiguity_arguments_present:
            _fail("local launch attempt accepts no collection arguments")
        return _issue_local_cli()
    if arguments.record_ambiguous_disconnect:
        if arguments.local_mirror_root is not None:
            _fail("transport ambiguity accepts no mirror path")
        return _record_ambiguity_cli(
            classification=arguments.transport_classification,
            stdout_path=arguments.transport_stdout_file,
            stderr_path=arguments.transport_stderr_file,
        )
    if ambiguity_arguments_present:
        _fail("read-only collection accepts no transport stream arguments")
    return _collect_cli(arguments.local_mirror_root, arguments.collection_ordinal)


if __name__ == "__main__":
    raise SystemExit(main())
