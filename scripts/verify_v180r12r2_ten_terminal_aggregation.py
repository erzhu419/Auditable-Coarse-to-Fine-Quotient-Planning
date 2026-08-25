#!/usr/bin/env python3
"""Producer-free verification and retained replay for V180r12r2."""

from __future__ import annotations

import ctypes
import gc
import hashlib
import os
from pathlib import Path
import resource
import signal
import stat
import traceback

from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_evidence_freeze_v180r12r2
    as authorization_evidence,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2
    as authorization,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_independent_verifier_v180r12r2
    as verifier,
)
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
TERMINAL = ROOT / authorization.TERMINAL_RELATIVE_PATH
RUNTIME_CAS_ROOT = ROOT / authorization.RUNTIME_CAS_ROOT_RELATIVE_PATH
PRODUCTION_FAILURE = ROOT / authorization.FAILURE_RELATIVE_PATH
VERIFICATION = ROOT / authorization.VERIFICATION_RELATIVE_PATH
FAILURE = ROOT / authorization.VERIFICATION_FAILURE_RELATIVE_PATH
REPLAY = ROOT / authorization.RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH

FAILURE_EMERGENCY_RESERVE_BYTES = authorization.FAILURE_EMERGENCY_RESERVE_BYTES
FAILURE_MESSAGE_BYTE_CAP = authorization.FAILURE_MESSAGE_BYTE_CAP
FAILURE_TYPE_BYTE_CAP = authorization.FAILURE_TYPE_BYTE_CAP


def _lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _require_symlink_free_existing_ancestors(path: Path) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as error:
        raise RuntimeError("V180r12r2 verification path escaped the repository") from error
    current = ROOT
    for part in relative.parts[:-1]:
        current = current / part
        metadata = os.lstat(current)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeError(
                "V180r12r2 verification ancestor is linked or non-directory"
            )


def _read_regular(path: Path, *, byte_cap: int) -> bytes:
    if type(byte_cap) is not int or byte_cap <= 0:
        raise TypeError("V180r12r2 verification input cap must be a positive integer")
    _require_symlink_free_existing_ancestors(path)
    directory_fd = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(descriptor)
            if before.st_size > byte_cap:
                raise RuntimeError("V180r12r2 terminal input exceeded its frozen cap")
            chunks: list[bytes] = []
            byte_count = 0
            while True:
                chunk = os.read(
                    descriptor,
                    authorization.FAILURE_OBSERVATION_STREAM_BUFFER_BYTES,
                )
                if not chunk:
                    break
                byte_count += len(chunk)
                if byte_count > byte_cap:
                    raise RuntimeError(
                        "V180r12r2 terminal input exceeded its frozen cap"
                    )
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    facts = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_mode,
        row.st_nlink,
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )
    raw = b"".join(chunks)
    if not (
        facts(before) == facts(after)
        and stat.S_ISREG(before.st_mode)
        and before.st_nlink == 1
        and len(raw) <= byte_cap
        and len(raw) == before.st_size
    ):
        raise RuntimeError("V180r12r2 verification input changed during read")
    return raw


def _write_once(path: Path, raw: bytes) -> None:
    if type(raw) is not bytes:
        raise TypeError("V180r12r2 verification output must be exact bytes")
    _require_symlink_free_existing_ancestors(path)
    directory_fd = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        descriptor = os.open(
            path.name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
            | os.O_NOFOLLOW,
            0o400,
            dir_fd=directory_fd,
        )
        try:
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("V180r12r2 verification short write")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _failure(
    failure_type: str,
    failure_message: str,
    *,
    failure_message_truncated: bool,
    alarm_teardown_failure: dict[str, object] | None,
    authorization_id: str,
    protocol_id: str,
    terminal_sha256: str | None,
) -> None:
    verification_observation = _progress_failure_observation(
        VERIFICATION,
        "verification output",
    )
    replay_observation = _progress_failure_observation(
        REPLAY,
        "retained replay",
    )
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_verification_failure.v180r12r2",
        "aggregation_protocol_id": protocol_id,
        "execution_authorization_id": authorization_id,
        "failure_type": failure_type,
        "failure_message": failure_message,
        "failure_message_truncated": failure_message_truncated,
        "alarm_teardown_failure": alarm_teardown_failure,
        "terminal_sha256": terminal_sha256,
        "verification_output_present": (
            verification_observation["state"] == "PRESENT"
        ),
        "verification_output_observation": verification_observation,
        "retained_replay_present": replay_observation["state"] == "PRESENT",
        "retained_replay_observation": replay_observation,
        "partial_progress_bytes_preserved": True,
        "same_verification_attempt_rerun_forbidden": True,
        "success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "failure_id": domains.extension_content_id_v180r12r2(
            domains.CONSTRUCTION_K7_FAILURE_V180R12R2_DOMAIN,
            payload,
        ),
    }
    _write_once(FAILURE, canonical_json_bytes(document))


def _detach_failure(error: BaseException) -> tuple[str, str, bool]:
    """Bound failure text and release non-running traceback frames before writing."""

    failure_type = _bounded_failure_type(error)
    message, truncated = _bounded_failure_text(error)
    try:
        retained_traceback = BaseException.__getattribute__(
            error,
            "__traceback__",
        )
    except BaseException:
        retained_traceback = None
    try:
        BaseException.__setattr__(error, "__traceback__", None)
    except BaseException:
        pass
    if retained_traceback is not None:
        try:
            traceback.clear_frames(retained_traceback)
        except BaseException:
            pass
    del retained_traceback
    return failure_type, message, truncated


def _bounded_failure_type(error: BaseException) -> str:
    try:
        error_class = type(error)
        candidate = type.__getattribute__(error_class, "__name__")
        prefix = str.__getitem__(candidate, slice(0, FAILURE_TYPE_BYTE_CAP))
        encoded = str.encode(prefix, "utf-8", "replace")[:FAILURE_TYPE_BYTE_CAP]
        while encoded:
            try:
                return bytes.decode(encoded, "utf-8")
            except UnicodeDecodeError:
                encoded = encoded[:-1]
    except BaseException:
        pass
    return "BaseException"


def _bounded_failure_text(error: BaseException) -> tuple[str, bool]:
    """Format hostile or memory-pressured exceptions with bounded allocation."""

    try:
        candidate = str(error)
        candidate_length = str.__len__(candidate)
        prefix = str.__getitem__(
            candidate,
            slice(0, FAILURE_MESSAGE_BYTE_CAP),
        )
        encoded = str.encode(prefix, "utf-8", "replace")
        truncated = (
            candidate_length > FAILURE_MESSAGE_BYTE_CAP
            or len(encoded) > FAILURE_MESSAGE_BYTE_CAP
        )
        if len(encoded) > FAILURE_MESSAGE_BYTE_CAP:
            encoded = encoded[:FAILURE_MESSAGE_BYTE_CAP]
            while encoded:
                try:
                    message = bytes.decode(encoded, "utf-8")
                    break
                except UnicodeDecodeError:
                    encoded = encoded[:-1]
            else:
                message = ""
        else:
            message = bytes.decode(encoded, "utf-8")
    except BaseException:
        return "<failure message unavailable>", True
    return message, truncated


def _release_failure_reserve(reserve: bytearray | None) -> None:
    """Release preregistered emergency memory before canonical failure emission."""

    if reserve is not None:
        reserve.clear()
    gc.collect()
    try:
        trim = ctypes.CDLL(None).malloc_trim
        trim.argtypes = (ctypes.c_size_t,)
        trim.restype = ctypes.c_int
        trim(0)
    except BaseException:
        # Failure emission remains authoritative even if best-effort heap return fails.
        pass


def _restore_alarm(previous_handler: object | None, installed: bool) -> None:
    if not installed:
        return
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous_handler)


def _suppress_alarm_before_reserve_release(
    installed: bool,
) -> BaseException | None:
    if not installed:
        return None
    cleanup_error: BaseException | None = None
    try:
        signal.alarm(0)
    except BaseException as error:
        cleanup_error = error
    try:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
    except BaseException as error:
        if cleanup_error is None:
            cleanup_error = error
    return cleanup_error


def _complete_alarm_cleanup_after_reserve_release(
    previous_handler: object | None,
    installed: bool,
    cleanup_error: BaseException | None,
) -> BaseException | None:
    if not installed:
        return cleanup_error
    try:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        signal.signal(signal.SIGALRM, previous_handler)
    except BaseException as error:
        if cleanup_error is None:
            cleanup_error = error
    return cleanup_error


def _alarm_cleanup_observation(
    cleanup_error: BaseException | None,
) -> dict[str, object] | None:
    if cleanup_error is None:
        return None
    cleanup_type, cleanup_message, cleanup_truncated = _detach_failure(cleanup_error)
    return {
        "failure_type": cleanup_type,
        "failure_message": cleanup_message,
        "failure_message_truncated": cleanup_truncated,
    }


def _progress_failure_observation(
    path: Path,
    label: str,
) -> dict[str, object]:
    """Best-effort typed fact for absent, partial, or unreadable progress."""

    if not _lexists(path):
        return {"state": "ABSENT", "byte_count": None, "sha256": None}
    try:
        metadata = os.lstat(path)
        if not stat.S_ISREG(metadata.st_mode):
            return {
                "state": "LINKED_OR_NONREGULAR",
                "byte_count": None,
                "sha256": None,
            }
        _require_symlink_free_existing_ancestors(path)
        directory_fd = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        try:
            descriptor = os.open(
                path.name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            try:
                before = os.fstat(descriptor)
                digest = hashlib.sha256()
                byte_count = 0
                while True:
                    chunk = os.read(
                        descriptor,
                        authorization.FAILURE_OBSERVATION_STREAM_BUFFER_BYTES,
                    )
                    if not chunk:
                        break
                    byte_count += len(chunk)
                    digest.update(chunk)
                after = os.fstat(descriptor)
            finally:
                os.close(descriptor)
        finally:
            os.close(directory_fd)
        stable = lambda row: (  # noqa: E731
            row.st_dev,
            row.st_ino,
            row.st_mode,
            row.st_nlink,
            row.st_size,
            row.st_mtime_ns,
            row.st_ctime_ns,
        )
        if not (
            stable(before) == stable(after)
            and stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and byte_count == before.st_size
        ):
            raise RuntimeError(f"{label} changed during failure observation")
        return {
            "state": "PRESENT",
            "byte_count": byte_count,
            "sha256": digest.hexdigest(),
        }
    except BaseException as error:
        error_message, error_message_truncated = _bounded_failure_text(error)
        return {
            "state": "READ_ERROR",
            "byte_count": None,
            "sha256": None,
            "error_type": _bounded_failure_type(error),
            "error_message": error_message,
            "error_message_truncated": error_message_truncated,
        }


def _timeout(_signum: int, _frame: object) -> None:
    raise TimeoutError("V180r12r2 verification crossed its frozen timeout")


def _release_transient_heap_and_require_cap_headroom(cap: int) -> int:
    """Release verifier arenas and prove the process remains under RLIMIT_AS."""

    gc.collect()
    try:
        trim = ctypes.CDLL(None).malloc_trim
        trim.argtypes = (ctypes.c_size_t,)
        trim.restype = ctypes.c_int
        trim_status = trim(0)
    except (AttributeError, OSError) as error:
        raise RuntimeError("V180r12r2 verifier glibc heap release is unavailable") from error
    if type(trim_status) is not int or trim_status not in {0, 1}:
        raise RuntimeError(
            "V180r12r2 verifier glibc heap release returned a foreign status"
        )
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        descriptor = os.open(
            f"/proc/{os.getpid()}/statm",
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        try:
            raw = os.read(descriptor, 4096)
            trailing = os.read(descriptor, 1)
        finally:
            os.close(descriptor)
        fields = raw.split()
        mapped_pages = int(fields[0])
    except (IndexError, OSError, ValueError) as error:
        raise RuntimeError("V180r12r2 verifier address-space proof failed") from error
    if not (
        type(cap) is int
        and cap > 0
        and type(page_size) is int
        and page_size > 0
        and mapped_pages > 0
        and not trailing
    ):
        raise RuntimeError("V180r12r2 verifier address-space proof is malformed")
    mapped_bytes = mapped_pages * page_size
    if mapped_bytes > cap:
        raise RuntimeError("V180r12r2 verifier address space exceeds the frozen cap")
    return mapped_bytes


def _require_fresh_verification_state() -> None:
    if (
        not TERMINAL.is_file()
        or _lexists(RUNTIME_CAS_ROOT)
        or _lexists(PRODUCTION_FAILURE)
        or _lexists(FAILURE)
        or _lexists(VERIFICATION)
        or _lexists(REPLAY)
    ):
        raise RuntimeError("V180r12r2 verification input or progress state changed")


def main() -> None:
    # First action inside runner main after the source-bound prelaunch dispatch;
    # no scientific output inspection or creation inside this runner precedes it.
    evidence = (
        authorization_evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2(
            source_boundary_commit=os.environ[
                "ACFQP_V180R12R2_PREREG_COMMIT"
            ]
        )
    )
    frozen = (
        authorization.freeze_ten_terminal_aggregation_execution_authorization_v180r12r2()
    )
    auth_document = frozen.to_document()
    if not (
        evidence.to_document()["execution_authorization_id"] == frozen.authorization_id
        and auth_document[
            "authorization_evidence_verification_is_first_action_inside_runner_"
            "main_after_prelaunch_dispatch"
        ]
        is True
        and auth_document[
            "authorization_evidence_verification_precedes_scientific_output_"
            "inspection_or_creation_inside_runner"
        ]
        is True
        and auth_document[
            "authorization_evidence_verification_is_process_first_action"
        ]
        is False
        and auth_document["prelaunch_contract"]["launch_rule_id"]
        == "57e88919b379a3fc2150dcefea46d30488b128832601e31269d225c4de37480b"
        and auth_document["prelaunch_contract"][
            "verification_launch_attempt_relative_path"
        ].endswith("/VERIFICATION_LAUNCH_ATTEMPT.json")
    ):
        raise RuntimeError("V180r12r2 verification authorization join changed")
    _require_fresh_verification_state()

    previous_alarm_handler: object | None = None
    alarm_installed = False
    alarm_teardown_in_progress = False
    terminal_sha256: str | None = None
    emergency_failure_reserve: bytearray | None = None
    try:
        emergency_failure_reserve = bytearray(FAILURE_EMERGENCY_RESERVE_BYTES)
        cap = authorization.ADDRESS_SPACE_HARD_CAP_BYTES
        _release_transient_heap_and_require_cap_headroom(cap)
        _old_soft, old_hard = resource.getrlimit(resource.RLIMIT_AS)
        if old_hard != resource.RLIM_INFINITY and old_hard < cap:
            raise RuntimeError(
                "V180r12r2 verifier address-space hard limit is below the frozen cap"
            )
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
        previous_alarm_handler = signal.signal(signal.SIGALRM, _timeout)
        alarm_installed = True
        signal.alarm(authorization.TIMEOUT_SECONDS)
        terminal_bytes = _read_regular(
            TERMINAL,
            byte_cap=authorization.VERIFICATION_TERMINAL_INPUT_BYTE_CAP,
        )
        terminal_sha256 = hashlib.sha256(terminal_bytes).hexdigest()
        first_document = verifier.verify_ten_terminal_aggregation_independently_v180r12r2(
            terminal_bytes,
            ROOT,
        )
        first_bytes = canonical_json_bytes(first_document)
        if len(first_bytes) > authorization.OUTPUT_TOTAL_BYTE_CAP:
            raise RuntimeError("V180r12r2 verification exceeded its output cap")
        _write_once(VERIFICATION, first_bytes)
        first_verification_id = first_document["verification_id"]
        del first_document
        _release_transient_heap_and_require_cap_headroom(cap)

        replay_document = verifier.verify_ten_terminal_aggregation_independently_v180r12r2(
            terminal_bytes,
            ROOT,
        )
        replay_bytes = canonical_json_bytes(replay_document)
        if (
            len(replay_bytes) > authorization.OUTPUT_TOTAL_BYTE_CAP
            or len(first_bytes) + len(replay_bytes)
            > authorization.OUTPUT_TOTAL_BYTE_CAP
        ):
            raise RuntimeError(
                "V180r12r2 verification and replay exceeded their output cap"
            )
        if replay_bytes != first_bytes:
            raise RuntimeError("V180r12r2 producer-free replay was not exact")
        _write_once(REPLAY, replay_bytes)
        alarm_teardown_in_progress = True
        _restore_alarm(previous_alarm_handler, alarm_installed)
        alarm_teardown_in_progress = False
        alarm_installed = False
    except BaseException as error:
        alarm_cleanup_error = _suppress_alarm_before_reserve_release(
            alarm_installed,
        )
        if emergency_failure_reserve is not None:
            emergency_failure_reserve.clear()
            emergency_failure_reserve = None
        alarm_cleanup_error = _complete_alarm_cleanup_after_reserve_release(
            previous_alarm_handler,
            alarm_installed,
            alarm_cleanup_error,
        )
        if alarm_teardown_in_progress and alarm_cleanup_error is None:
            alarm_cleanup_error = error
        alarm_installed = False
        alarm_teardown_failure = _alarm_cleanup_observation(alarm_cleanup_error)
        failure_type, failure_message, failure_message_truncated = _detach_failure(
            error
        )
        _release_failure_reserve(None)
        if not _lexists(FAILURE):
            _failure(
                failure_type,
                failure_message,
                failure_message_truncated=failure_message_truncated,
                alarm_teardown_failure=alarm_teardown_failure,
                authorization_id=frozen.authorization_id,
                protocol_id=auth_document["aggregation_protocol_id"],
                terminal_sha256=terminal_sha256,
            )
        raise
    emergency_failure_reserve = None

    print(
        canonical_json_bytes(
            {
                "execution_authorization_id": frozen.authorization_id,
                "production_aggregation_sha256": terminal_sha256,
                "verification_id": first_verification_id,
                "verification_byte_count": len(first_bytes),
                "verification_sha256": hashlib.sha256(first_bytes).hexdigest(),
                "retained_replay_exact": True,
            }
        ).decode("utf-8"),
        flush=True,
    )


if __name__ == "__main__":
    main()
