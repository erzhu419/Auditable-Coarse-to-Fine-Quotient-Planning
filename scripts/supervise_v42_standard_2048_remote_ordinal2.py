#!/usr/bin/env python3
"""Isolated producer/verifier supervisor for V42 remote ordinal-2.

The frozen scientific producer and independent verifier are reused without
executing the ordinal-1 runner or supervisor.  Their authority import name is
preinstalled as an alias of the new authority module, so the old authority
source is never executed under a hidden module name.
"""

from __future__ import annotations

import argparse
import hashlib
import multiprocessing
import os
from pathlib import Path
import secrets
import sys
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

import acfqp
from acfqp import construction_k7_standard_2048_process_supervision_v42r1 as processio
from acfqp import construction_k7_standard_2048_remote_execution_authority_v42r1 as authority
from acfqp import construction_k7_standard_2048_fresh_terminal_preregistration_v42 as pre
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CHILD_TIMEOUT_SECONDS = 7 * 24 * 60 * 60
MAX_PRODUCER_STDOUT_BYTES = 512 * 1024 * 1024
MAX_VERIFIER_STDOUT_BYTES = 32 * 1024 * 1024
OLD_AUTHORITY_MODULE = "acfqp.construction_k7_standard_2048_execution_authority_v42"
OLD_AUTHORITY_ATTRIBUTE = "construction_k7_standard_2048_execution_authority_v42"
ORDINAL1_FORBIDDEN_SOURCE_ORIGINS = frozenset(
    {
        "src/acfqp/construction_k7_standard_2048_execution_authority_v42.py",
        "scripts/run_v42_standard_2048_fresh_terminal_campaign.py",
        "scripts/supervise_v42_standard_2048_fresh_terminal_campaign.py",
    }
)


class V42RemoteOrdinal2SupervisorError(RuntimeError):
    """The ordinal-2 authority alias, role isolation, or scientific join failed."""


def _fail(message: str) -> NoReturn:
    raise V42RemoteOrdinal2SupervisorError(processio.bounded_message(message))


def _install_frozen_authority_alias() -> None:
    expected_origin = (
        "src/acfqp/"
        "construction_k7_standard_2048_remote_execution_authority_v42r1.py"
    )
    try:
        authority_origin = (
            Path(authority.__file__).resolve(strict=True).relative_to(ROOT).as_posix()
        )
    except (AttributeError, FileNotFoundError, OSError, ValueError) as error:
        raise V42RemoteOrdinal2SupervisorError(
            "ordinal-2 authority source origin is unavailable"
        ) from error
    if authority_origin != expected_origin:
        _fail("ordinal-2 authority source origin changed")
    existing = sys.modules.get(OLD_AUTHORITY_MODULE)
    if existing is not None and existing is not authority:
        _fail("ordinal-1 authority was already loaded before alias installation")
    sys.modules[OLD_AUTHORITY_MODULE] = authority
    setattr(acfqp, OLD_AUTHORITY_ATTRIBUTE, authority)
    if sys.modules[OLD_AUTHORITY_MODULE] is not authority:
        _fail("frozen authority import alias changed")


def _repository_module_origins() -> dict[str, str]:
    origins: dict[str, str] = {}
    root = ROOT.resolve()
    for name, module in tuple(sys.modules.items()):
        raw_file = getattr(module, "__file__", None)
        if type(raw_file) is not str:
            continue
        try:
            relative = Path(raw_file).resolve(strict=True).relative_to(root).as_posix()
        except (FileNotFoundError, OSError, ValueError):
            continue
        origins[name] = relative
    return origins


def _reject_forbidden_source_origins(forbidden: frozenset[str], role: str) -> None:
    observed = _repository_module_origins()
    conflicts = sorted(
        f"{name}:{relative}"
        for name, relative in observed.items()
        if relative in forbidden
    )
    if conflicts:
        _fail(f"{role} loaded forbidden repository source origins: " + ", ".join(conflicts))


def _verify_runtime_authority_alias(role: str) -> None:
    expected_origin = (
        "src/acfqp/"
        "construction_k7_standard_2048_remote_execution_authority_v42r1.py"
    )
    try:
        observed_origin = (
            Path(authority.__file__).resolve(strict=True).relative_to(ROOT).as_posix()
        )
    except (AttributeError, FileNotFoundError, OSError, ValueError) as error:
        raise V42RemoteOrdinal2SupervisorError(
            f"{role} ordinal-2 authority origin became unavailable"
        ) from error
    if (
        observed_origin != expected_origin
        or sys.modules.get(OLD_AUTHORITY_MODULE) is not authority
        or getattr(acfqp, OLD_AUTHORITY_ATTRIBUTE, None) is not authority
    ):
        _fail(f"{role} ordinal-2 authority alias or source origin changed")
    _reject_forbidden_source_origins(ORDINAL1_FORBIDDEN_SOURCE_ORIGINS, role)


def _isolated_command(*arguments: object) -> tuple[str, ...]:
    return (
        authority.REMOTE_PYTHON,
        "-I",
        "-S",
        "-B",
        str(Path(__file__).resolve()),
        *(str(argument) for argument in arguments),
    )


def _verify_post_launch_remote_controls(
    receipt: dict[str, Any], attempt: dict[str, Any] | None = None
) -> dict[str, Any]:
    phase = authority.verify_remote_control_phase_inventory_v42r1(
        "POST_LAUNCH", prepare_receipt=receipt
    )
    if attempt is not None and (
        phase["local_launch_attempt"]["local_launch_attempt_id"]
        != attempt["local_launch_attempt_id"]
        or phase["launch_host_attestation"] != attempt["launch_host_attestation"]
    ):
        _fail("post-launch remote controls differ from the runner attempt")
    return phase


def _producer_worker(authorization_fd: int) -> int:
    processio.require_isolated_python()
    _install_frozen_authority_alias()
    _reject_forbidden_source_origins(
        ORDINAL1_FORBIDDEN_SOURCE_ORIGINS
        | frozenset(
            {
                "src/acfqp/construction_k7_standard_2048_fresh_terminal_independent_verifier_v42.py",
            }
        ),
        "producer",
    )
    try:
        secret = processio.read_fd_capped(
            authorization_fd, 32, "producer authorization"
        )
    finally:
        os.close(authorization_fd)
    if len(secret) != 32:
        _fail("remote ordinal-2 producer authorization has the wrong length")
    receipt_bytes = processio.read_fixed_artifact(
        authority.fixed_authority_root_v42(ROOT) / authority.PREPARE_RECEIPT_NAME,
        64 * 1024 * 1024,
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_bytes,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
        root=ROOT,
        require_live_source=True,
    )
    _verify_post_launch_remote_controls(receipt)
    authority.install_runtime_repository_import_guard_v42(
        ROOT, receipt["source_manifest"]
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    start_method = multiprocessing.get_start_method(allow_none=True)
    if start_method is None:
        multiprocessing.set_start_method("fork")
    elif start_method != "fork":
        _fail("frozen two-episode process pool requires the registered fork start method")
    from acfqp import construction_k7_standard_2048_fresh_terminal_campaign_v42 as campaign

    if campaign.authority is not authority:
        _fail("frozen producer did not receive the ordinal-2 authority alias")
    formal_authority = campaign._issue_formal_execution_authority_v42(  # noqa: SLF001
        repository_root=ROOT,
        worker_authorization_secret=secret,
    )
    produced = campaign._run_standard_2048_fresh_terminal_campaign_v42(  # noqa: SLF001
        formal_authority=formal_authority
    )
    _verify_runtime_authority_alias("producer post-campaign")
    _reject_forbidden_source_origins(
        ORDINAL1_FORBIDDEN_SOURCE_ORIGINS
        | frozenset(
            {
                "src/acfqp/"
                "construction_k7_standard_2048_fresh_terminal_independent_verifier_v42.py",
            }
        ),
        "producer post-campaign",
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    sys.stdout.buffer.write(produced.canonical_bytes + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _verifier_worker(campaign_fd: int) -> int:
    processio.require_isolated_python()
    _install_frozen_authority_alias()
    forbidden = ORDINAL1_FORBIDDEN_SOURCE_ORIGINS | frozenset(
        {
            "src/acfqp/construction_k7_standard_2048_fresh_terminal_campaign_v42.py",
            "src/acfqp/construction_k7_standard_2048_adaptive_expression_target_v35.py",
            "src/acfqp/construction_k7_standard_2048_observation_proposed_program_v14.py",
            "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
            "scripts/run_v42_standard_2048_fresh_terminal_campaign.py",
            "scripts/supervise_v42_standard_2048_fresh_terminal_campaign.py",
        }
    )
    _reject_forbidden_source_origins(forbidden, "verifier pre-import")
    try:
        campaign_bytes = processio.read_fd_capped(
            campaign_fd, MAX_PRODUCER_STDOUT_BYTES, "campaign input"
        )
    finally:
        os.close(campaign_fd)
    authority_root = authority.fixed_authority_root_v42(ROOT)
    evidence_root = authority.fixed_evidence_root_v42(ROOT)
    receipt_bytes = processio.read_fixed_artifact(
        authority_root / authority.PREPARE_RECEIPT_NAME, 64 * 1024 * 1024
    )
    attempt_bytes = processio.read_fixed_artifact(
        evidence_root / authority.ATTEMPT_NAME, 1024 * 1024
    )
    worker_start_bytes = processio.read_fixed_artifact(
        evidence_root / authority.WORKER_START_NAME, 1024 * 1024
    )
    consumption_bytes = processio.read_fixed_artifact(
        evidence_root / authority.AUTHORITY_CONSUMPTION_NAME, 1024 * 1024
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_bytes,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=pre._freshness()[  # noqa: SLF001
            "history_freshness_manifest_id"
        ],
        root=ROOT,
        require_live_source=True,
    )
    attempt = authority.verify_runner_attempt_v42(
        attempt_bytes,
        prepare_receipt=receipt,
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
    )
    _verify_post_launch_remote_controls(receipt, attempt)
    authority.install_runtime_repository_import_guard_v42(
        ROOT, receipt["source_manifest"]
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    from acfqp import construction_k7_standard_2048_fresh_terminal_independent_verifier_v42 as verifier

    if verifier.authority is not authority:
        _fail("frozen verifier did not receive the ordinal-2 authority alias")
    _reject_forbidden_source_origins(forbidden, "verifier post-import")
    checked = verifier.verify_standard_2048_fresh_terminal_bytes_independently_v42(
        campaign_bytes,
        prepare_receipt_bytes=receipt_bytes,
        runner_attempt_bytes=attempt_bytes,
        worker_start_bytes=worker_start_bytes,
        authority_consumption_bytes=consumption_bytes,
    )
    _verify_runtime_authority_alias("verifier post-replay alias")
    _reject_forbidden_source_origins(forbidden, "verifier post-replay")
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    sys.stdout.buffer.write(checked.canonical_bytes + b"\n")
    sys.stdout.buffer.flush()
    return 0


def _build_supervisor_envelope(
    *,
    receipt: dict[str, object],
    attempt: dict[str, object],
    worker_start: dict[str, object],
    consumption: dict[str, object],
    campaign_document: dict[str, object],
    verification_document: dict[str, object],
    all_terminal: bool,
) -> dict[str, object]:
    if type(all_terminal) is not bool:
        _fail("remote ordinal-2 campaign terminal flag changed type")
    return {
        "schema": "acfqp.v42_remote_ordinal2_supervised_result.v42r1",
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "prepare_receipt_id": receipt["prepare_receipt_id"],
        "runner_attempt_id": attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "authority_consumption_id": consumption["authority_consumption_id"],
        "source_manifest_id": receipt["source_manifest_id"],
        "transport_manifest_id": receipt["transport_manifest_id"],
        "predecessor_binding_id": receipt["predecessor_binding_id"],
        "prepare_host_attestation_id": receipt["prepare_host_attestation_id"],
        "launch_host_attestation_id": attempt["launch_host_attestation_id"],
        "local_launch_attempt_id": attempt["local_launch_attempt_id"],
        "producer_process_isolated": True,
        "verifier_process_isolated": True,
        "isolated_python_flags": ["-I", "-S", "-B"],
        "frozen_authority_import_resolved_to_ordinal2_source": True,
        "ordinal1_authority_source_loaded": False,
        "ordinal1_authority_runner_or_supervisor_source_loaded": False,
        "fresh_terminal_campaign": campaign_document,
        "fresh_terminal_independent_verification": verification_document,
        "all_registered_episodes_terminal": all_terminal,
        "scientific_exit_code": 0 if all_terminal else 2,
    }


def _formal_supervisor() -> int:
    processio.require_isolated_python()
    if os.getpid() != os.getpgrp() or os.getpid() != os.getsid(0):
        _fail("formal supervisor is not the leader of its fresh process group/session")
    _install_frozen_authority_alias()
    _reject_forbidden_source_origins(
        ORDINAL1_FORBIDDEN_SOURCE_ORIGINS, "supervisor post-alias"
    )
    history_manifest = pre._freshness()  # noqa: SLF001
    authority_root = authority.fixed_authority_root_v42(ROOT)
    evidence_root = authority.fixed_evidence_root_v42(ROOT)
    receipt_bytes = processio.read_fixed_artifact(
        authority_root / authority.PREPARE_RECEIPT_NAME, 64 * 1024 * 1024
    )
    attempt_bytes = processio.read_fixed_artifact(
        evidence_root / authority.ATTEMPT_NAME, 1024 * 1024
    )
    receipt = authority.verify_prepare_receipt_v42(
        receipt_bytes,
        fresh_terminal_preregistration_id=pre.PREREGISTRATION_ID,
        history_freshness_manifest_id=history_manifest[
            "history_freshness_manifest_id"
        ],
        root=ROOT,
        require_live_source=True,
    )
    attempt = authority.verify_runner_attempt_v42(
        attempt_bytes,
        prepare_receipt=receipt,
        registered_episode_count=len(pre.INITIAL_BOARDS),
        decision_cap_per_episode=pre.MAXIMUM_DECISIONS_PER_EPISODE,
    )
    _verify_post_launch_remote_controls(receipt, attempt)
    authority.install_runtime_repository_import_guard_v42(
        ROOT, receipt["source_manifest"]
    )
    authority.verify_runtime_repository_modules_in_manifest_v42(
        ROOT, receipt["source_manifest"]
    )
    secret = secrets.token_bytes(32)
    worker_start = authority.build_worker_start_v42(
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_authorization_secret_sha256=hashlib.sha256(secret).hexdigest(),
    )
    processio.write_once(
        evidence_root / authority.WORKER_START_NAME,
        canonical_json_bytes(worker_start),
    )

    authorization_fd = processio.memfd_from_bytes(
        "v42-remote-ordinal2-worker-authorization", secret
    )
    try:
        producer_completed = processio.run_capped_child(
            role="PRODUCER",
            command=_isolated_command(
                "--producer-worker", "--authorization-fd", authorization_fd
            ),
            inherited_descriptor=authorization_fd,
            stdout_cap=MAX_PRODUCER_STDOUT_BYTES + 1,
            timeout_seconds=CHILD_TIMEOUT_SECONDS,
            cwd=ROOT,
            start_new_session=False,
        )
    finally:
        os.close(authorization_fd)
    if producer_completed.returncode != 0 or producer_completed.stderr:
        classification = processio.typed_failure_classification(
            producer_completed.stderr,
            processio.child_classification("PRODUCER", producer_completed.returncode),
        )
        raise processio.V42RemoteOrdinal2ChildError(
            "remote ordinal-2 producer failed",
            role="PRODUCER",
            returncode=producer_completed.returncode,
            stdout=producer_completed.stdout,
            stderr=producer_completed.stderr,
            classification=classification,
        )
    campaign_bytes = processio.one_canonical_stdout(producer_completed, "producer")
    campaign_fd = processio.memfd_from_bytes(
        "v42-remote-ordinal2-campaign-for-verifier", campaign_bytes
    )
    try:
        verifier_completed = processio.run_capped_child(
            role="VERIFIER",
            command=_isolated_command(
                "--verifier-worker", "--campaign-fd", campaign_fd
            ),
            inherited_descriptor=campaign_fd,
            stdout_cap=MAX_VERIFIER_STDOUT_BYTES + 1,
            timeout_seconds=CHILD_TIMEOUT_SECONDS,
            cwd=ROOT,
            start_new_session=False,
        )
    finally:
        os.close(campaign_fd)
    if verifier_completed.returncode != 0 or verifier_completed.stderr:
        classification = processio.typed_failure_classification(
            verifier_completed.stderr,
            processio.child_classification("VERIFIER", verifier_completed.returncode),
        )
        raise processio.V42RemoteOrdinal2ChildError(
            "remote ordinal-2 verifier failed",
            role="VERIFIER",
            returncode=verifier_completed.returncode,
            stdout=verifier_completed.stdout,
            stderr=verifier_completed.stderr,
            classification=classification,
        )
    verification_bytes = processio.one_canonical_stdout(verifier_completed, "verifier")
    campaign_document = loads_canonical_json(campaign_bytes)
    verification_document = loads_canonical_json(verification_bytes)
    consumption_bytes = processio.read_fixed_artifact(
        evidence_root / authority.AUTHORITY_CONSUMPTION_NAME, 1024 * 1024
    )
    consumption = authority.verify_authority_consumption_v42(
        consumption_bytes,
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_start=worker_start,
    )
    if (
        type(campaign_document) is not dict
        or type(verification_document) is not dict
        or verification_document.get("fresh_terminal_campaign_id")
        != campaign_document.get("fresh_terminal_campaign_id")
    ):
        _fail("remote ordinal-2 producer/verifier join changed")
    _reject_forbidden_source_origins(
        ORDINAL1_FORBIDDEN_SOURCE_ORIGINS, "supervisor post-children"
    )
    _verify_runtime_authority_alias("supervisor post-children alias")
    all_terminal = campaign_document.get("all_registered_episodes_terminal")
    envelope = _build_supervisor_envelope(
        receipt=receipt,
        attempt=attempt,
        worker_start=worker_start,
        consumption=consumption,
        campaign_document=campaign_document,
        verification_document=verification_document,
        all_terminal=all_terminal,
    )
    sys.stdout.buffer.write(canonical_json_bytes(envelope) + b"\n")
    sys.stdout.buffer.flush()
    return 0 if all_terminal else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one isolated V42 remote ordinal-2 role"
    )
    roles = parser.add_mutually_exclusive_group(required=True)
    roles.add_argument("--formal-supervisor", action="store_true")
    roles.add_argument("--producer-worker", action="store_true")
    roles.add_argument("--verifier-worker", action="store_true")
    parser.add_argument("--authorization-fd", type=int)
    parser.add_argument("--campaign-fd", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.formal_supervisor:
        if arguments.authorization_fd is not None or arguments.campaign_fd is not None:
            _fail("remote ordinal-2 supervisor received a child descriptor")
        return _formal_supervisor()
    if arguments.producer_worker:
        if arguments.authorization_fd is None or arguments.campaign_fd is not None:
            _fail("remote ordinal-2 producer descriptor contract changed")
        return _producer_worker(arguments.authorization_fd)
    if arguments.campaign_fd is None or arguments.authorization_fd is not None:
        _fail("remote ordinal-2 verifier descriptor contract changed")
    return _verifier_worker(arguments.campaign_fd)


def _emit_typed_process_failure(error: BaseException) -> None:
    if "--producer-worker" in sys.argv:
        process_role = "PRODUCER"
    elif "--verifier-worker" in sys.argv:
        process_role = "VERIFIER"
    else:
        process_role = "SUPERVISOR"
    if isinstance(error, processio.V42RemoteOrdinal2ChildError):
        classification = error.classification
        nested_role = error.role
        nested_returncode = error.returncode
        nested_stdout = error.stdout
        nested_stderr = error.stderr
        nested_group_teardown = error.group_teardown
    else:
        classification = f"{process_role}_EXCEPTION"
        nested_role = None
        nested_returncode = None
        nested_stdout = b""
        nested_stderr = b""
        nested_group_teardown = "NOT_REQUESTED"
    document = {
        "schema": "acfqp.v42_remote_ordinal2_isolated_process_failure.v42r1",
        "schema_version": authority.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "process_role": process_role,
        "failure_classification": classification,
        "failure_type": type(error).__name__,
        "failure_message": processio.bounded_message(error),
        "failure_message_cap_bytes": processio.MAX_EXCEPTION_MESSAGE_BYTES,
        "nested_role": nested_role,
        "nested_returncode": nested_returncode,
        "nested_group_teardown": nested_group_teardown,
        "nested_stdout": {
            "captured_byte_count": len(nested_stdout),
            "sha256": hashlib.sha256(nested_stdout).hexdigest(),
        },
        "nested_stderr": {
            "captured_byte_count": len(nested_stderr),
            "sha256": hashlib.sha256(nested_stderr).hexdigest(),
        },
        "scientific_success": False,
        "same_identity_retry_authorized": False,
    }
    sys.stderr.buffer.write(canonical_json_bytes(document) + b"\n")
    sys.stderr.buffer.flush()


if __name__ == "__main__":
    try:
        _exit_code = main()
    except Exception as _error:
        _emit_typed_process_failure(_error)
        _exit_code = 70
    raise SystemExit(_exit_code)
