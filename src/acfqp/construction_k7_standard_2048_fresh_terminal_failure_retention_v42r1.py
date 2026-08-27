"""Retain the immutable V42 ordinal-1 formal failure without reclassification.

The V42 runner formally closed ordinal 1 as ``PRODUCER_EXCEPTION`` after its
isolated producer returned 70.  Operators separately reported that they had
sent SIGKILL to the two exact episode-worker PIDs after observing sustained D
state and severe host-memory pressure.  That report is useful operational
context, but it is post-hoc and is not an OOM event receipt, cgroup proof, or
formal V42 failure classifier input.  This successor copies the fixed bytes,
binds those two evidence classes without conflating them, and issues no
scientific result or ordinal-2 authority.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42r1.0.0"
PROFILE_KEY = "construction_k7_standard_2048_fresh_terminal_failure_retention_v42r1"
RETENTION_DOMAIN = (
    "acfqp:construction-k7-standard-2048-fresh-terminal-ordinal1-failure-retention:v42r1"
)
SOURCE_COMMIT = "c48f269b6293ad7a1d8f4e6ab5ff1b098357264b"
SOURCE_TREE = "4744cc0638fbfa4cd677c0701f003ce01eed1a86"
SOURCE_MANIFEST_ID = "11a897dfb2292f29f8048ea2f95dcacb552405b662775ae57a5d9adb6468401d"
HISTORY_MANIFEST_ID = "c94d62bbcaa3cea0869a4a00b0944808b5e893a7a4c276e93a3b583df4aa5d29"
PREREGISTRATION_ID = "575e06a306c9dcee816bc5d1ba431ef163d084ae174614d4b3b1b4b4358ff5b3"
PREPARE_RECEIPT_ID = "7fd00460ff58f4deacef516e40e3e2fc0f595e24a6db6f44d9baa25af638145c"
RUNNER_ATTEMPT_ID = "d42ed122534d87d60135a1c949872766d99ad15eaa1ac61dad6f3f040fddb58e"
WORKER_START_ID = "07a39b80b7e29b27af76a1e73ab9bd5df8728a69b07745dd31caa930ed046136"
AUTHORITY_CONSUMPTION_ID = "88946c26382cdcc9d8930fd30895df0cc98045e74445d9f3b4c8c3da2d6631b2"
RUNNER_FAILURE_ID = "c5ab25e29efef47c22d2ccbbaa5867f11b51e9fadaecab321e60fc3dc879d354"
FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_ORDINAL_1"
EVIDENCE_ROOT_RELATIVE = ".tmp/exact-freeze/v42_standard_2048_fresh_terminal_execution"
AUTHORITY_ROOT_RELATIVE = ".tmp/exact-freeze/v42_standard_2048_fresh_terminal_authority"
DEFAULT_RETENTION_ROOT_RELATIVE = (
    "retained_evidence/v42_standard_2048_fresh_terminal_ordinal1_failure"
)


_V42_DOMAINS = {
    "prepare_attempt_journal_id": "acfqp:construction-k7-standard-2048-fresh-terminal-prepare-journal:v42",
    "prepare_receipt_id": "acfqp:construction-k7-standard-2048-fresh-terminal-prepare-receipt:v42",
    "launch_attempt_journal_id": "acfqp:construction-k7-standard-2048-fresh-terminal-launch-journal:v42",
    "runner_attempt_id": "acfqp:construction-k7-standard-2048-fresh-terminal-runner-attempt:v42",
    "worker_start_id": "acfqp:construction-k7-standard-2048-fresh-terminal-worker-start:v42",
    "authority_consumption_id": "acfqp:construction-k7-standard-2048-fresh-terminal-authority-consumption:v42",
    "runner_failure_id": "acfqp:construction-k7-standard-2048-fresh-terminal-runner-failure:v42",
    "source_manifest_id": "acfqp:construction-k7-standard-2048-fresh-terminal-source-manifest:v42",
}


ARTIFACT_SPECS = (
    {
        "role": "PREPARE_ATTEMPT",
        "original_relative_path": ".V42_FRESH_TERMINAL_PREPARE_ATTEMPT.json",
        "retained_relative_path": "artifacts/00_PREPARE_ATTEMPT.json",
        "byte_count": 731,
        "sha256": "f33645d4f7436c12699019882bba5168a49f1ff834af710d382de7296599dfbf",
        "schema": "acfqp.standard_2048_fresh_terminal_prepare_attempt_journal.v42",
        "id_field": "prepare_attempt_journal_id",
        "content_id": "95b02e355ce79c791cb3170e10b7b1a88c490aab22f75ccfd9ac594753efcc76",
    },
    {
        "role": "PREPARE_RECEIPT",
        "original_relative_path": f"{AUTHORITY_ROOT_RELATIVE}/PREPARE_RECEIPT.json",
        "retained_relative_path": "artifacts/01_PREPARE_RECEIPT.json",
        "byte_count": 28_013,
        "sha256": "8624d184f980c2fed94b6140cf072ee1319fff91efb06d04a8c983ed975412a7",
        "schema": "acfqp.standard_2048_fresh_terminal_prepare_receipt.v42",
        "id_field": "prepare_receipt_id",
        "content_id": PREPARE_RECEIPT_ID,
    },
    {
        "role": "LAUNCH_ATTEMPT",
        "original_relative_path": ".V42_FRESH_TERMINAL_LAUNCH_ATTEMPT.json",
        "retained_relative_path": "artifacts/02_LAUNCH_ATTEMPT.json",
        "byte_count": 816,
        "sha256": "0be738711f8b685687c0cb4a0604187aff1d19cb767da836cae040a4bd2d554e",
        "schema": "acfqp.standard_2048_fresh_terminal_launch_attempt_journal.v42",
        "id_field": "launch_attempt_journal_id",
        "content_id": "5c02f1ca831eb275bf2d8e72d5147e453097d8ca73fea383fb74aa8c29350254",
    },
    {
        "role": "RUNNER_ATTEMPT",
        "original_relative_path": f"{EVIDENCE_ROOT_RELATIVE}/ATTEMPT.json",
        "retained_relative_path": "artifacts/03_ATTEMPT.json",
        "byte_count": 1_008,
        "sha256": "93b2b25944847eaa6f2f26314e10298b711ec2a0e7db4389d4e1aaad308e4981",
        "schema": "acfqp.standard_2048_fresh_terminal_runner_attempt.v42",
        "id_field": "runner_attempt_id",
        "content_id": RUNNER_ATTEMPT_ID,
    },
    {
        "role": "WORKER_START",
        "original_relative_path": f"{EVIDENCE_ROOT_RELATIVE}/WORKER_START.json",
        "retained_relative_path": "artifacts/04_WORKER_START.json",
        "byte_count": 930,
        "sha256": "9d32ce351e996f7e9f10ab0a50a548ebcc10464cf25eab14023e6f450cde2cd0",
        "schema": "acfqp.standard_2048_fresh_terminal_worker_start.v42",
        "id_field": "worker_start_id",
        "content_id": WORKER_START_ID,
    },
    {
        "role": "AUTHORITY_CONSUMPTION",
        "original_relative_path": f"{EVIDENCE_ROOT_RELATIVE}/AUTHORITY_CONSUMPTION.json",
        "retained_relative_path": "artifacts/05_AUTHORITY_CONSUMPTION.json",
        "byte_count": 777,
        "sha256": "97d97811620806534d23e35a61445243072589013e1ae483bff69578131b4074",
        "schema": "acfqp.standard_2048_fresh_terminal_authority_consumption.v42",
        "id_field": "authority_consumption_id",
        "content_id": AUTHORITY_CONSUMPTION_ID,
    },
    {
        "role": "EVIDENCE_ROOT_FAILURE",
        "original_relative_path": f"{EVIDENCE_ROOT_RELATIVE}/FAILURE.json",
        "retained_relative_path": "artifacts/06_FAILURE_EVIDENCE_ROOT.json",
        "byte_count": 1_864,
        "sha256": "1e06ba7fcf8f9f6e85f3f6a77eacc3cb4303e3b4f0f0a1e0b9bb40acb720495b",
        "schema": "acfqp.standard_2048_fresh_terminal_runner_failure.v42",
        "id_field": "runner_failure_id",
        "content_id": RUNNER_FAILURE_ID,
    },
    {
        "role": "FIXED_PARENT_FAILURE",
        "original_relative_path": ".V42_FRESH_TERMINAL_LAUNCH_FAILURE.json",
        "retained_relative_path": "artifacts/07_FAILURE_FIXED_PARENT.json",
        "byte_count": 1_864,
        "sha256": "1e06ba7fcf8f9f6e85f3f6a77eacc3cb4303e3b4f0f0a1e0b9bb40acb720495b",
        "schema": "acfqp.standard_2048_fresh_terminal_runner_failure.v42",
        "id_field": "runner_failure_id",
        "content_id": RUNNER_FAILURE_ID,
    },
)


INVOCATION_CAPTURE_SPECS = (
    {
        "role": "PREPARE_INVOCATION_STDOUT",
        "evidence_class": "NON_FORMAL_INVOCATION_CAPTURE",
        "original_absolute_path": "/tmp/acfqp-v42-formal-prepare.stdout",
        "retained_relative_path": "invocation_captures/00_PREPARE_STDOUT.bin",
        "byte_count": 28_014,
        "sha256": "4a21bd0f9ae0e3462f92cc452f0df24d23895489ef2ff690f73ba90f7f9e92fe",
        "interpretation": "PREPARE_RECEIPT_CANONICAL_BYTES_PLUS_SINGLE_LF",
    },
    {
        "role": "PREPARE_INVOCATION_STDERR",
        "evidence_class": "NON_FORMAL_INVOCATION_CAPTURE",
        "original_absolute_path": "/tmp/acfqp-v42-formal-prepare.stderr",
        "retained_relative_path": "invocation_captures/01_PREPARE_STDERR.bin",
        "byte_count": 0,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "interpretation": "EMPTY_PREPARE_INVOCATION_STDERR",
    },
    {
        "role": "LAUNCH_INVOCATION_STDOUT",
        "evidence_class": "NON_FORMAL_INVOCATION_CAPTURE",
        "original_absolute_path": "/tmp/acfqp-v42-formal-launch.stdout",
        "retained_relative_path": "invocation_captures/02_LAUNCH_STDOUT.bin",
        "byte_count": 0,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "interpretation": "EMPTY_LAUNCH_INVOCATION_STDOUT",
    },
    {
        "role": "LAUNCH_INVOCATION_STDERR",
        "evidence_class": "NON_FORMAL_INVOCATION_CAPTURE",
        "original_absolute_path": "/tmp/acfqp-v42-formal-launch.stderr",
        "retained_relative_path": "invocation_captures/03_LAUNCH_STDERR.bin",
        "byte_count": 935,
        "sha256": "9d0e5e67d434da33fb3446c29b18b7e9f4ad3d943df4b8cfefad101adc9cf059",
        "interpretation": "OUTER_LAUNCH_TRACEBACK_NOT_FORMAL_WORKER_STDERR",
    },
)


OPERATOR_OBSERVATION = {
    "evidence_class": "POST_HOC_OPERATOR_OBSERVATION_ONLY",
    "retention_document_constructed_after_formal_failure": True,
    "resource_observations_and_signal_preceded_failure_publication": True,
    "user_authorized_sigkill": True,
    "episode_worker_pids": [571800, 571801],
    "signal_name": "SIGKILL",
    "signal_number": 9,
    "approximate_elapsed_minutes": 56,
    "observed_worker_state": "D",
    "observed_mem_available_gib_range": [0.3, 0.4],
    "observed_swap_state": "NEAR_EXHAUSTED",
    "formal_oom_event_receipt_present": False,
    "formal_cgroup_oom_proof_present": False,
    "formal_kernel_oom_kill_proof_present": False,
    "formal_failure_reclassified_from_operator_observation": False,
    "general_oom_causality_claimed": False,
    "outer_runner_natural_exit_code_observed": 1,
    "outer_runner_exit_observation_is_not_formal_worker_returncode": True,
}

_EXPECTED_EVIDENCE_ROOT_ENTRIES = (
    "ATTEMPT.json",
    "AUTHORITY_CONSUMPTION.json",
    "FAILURE.json",
    "WORKER_START.json",
)
_ABSENT_FORMAL_ARTIFACTS = (
    "CAMPAIGN.json",
    "VERIFICATION.json",
    "TERMINAL.json",
)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class Standard2048FreshTerminalFailureRetentionV42R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise Standard2048FreshTerminalFailureRetentionV42R1Error(message)


def _cid(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _stable_read(path: Path, *, cap: int = 64 * 1024 * 1024) -> bytes:
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        _fail("V42r1 retained input is not one linked regular file")
    descriptor = os.open(path, os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("V42r1 retained input identity raced")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1 << 20, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > cap:
                _fail("V42r1 retained input exceeded its cap")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    named = os.lstat(path)
    identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if identity != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        _fail("V42r1 retained input changed during read")
    if identity != (named.st_dev, named.st_ino, named.st_size, named.st_mtime_ns):
        _fail("V42r1 retained input mapping changed")
    return b"".join(chunks)


def _document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise Standard2048FreshTerminalFailureRetentionV42R1Error(
            f"V42r1 {label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"V42r1 {label} bytes changed")
    return value


def _verify_v42_document(spec: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
    if len(raw) != spec["byte_count"] or hashlib.sha256(raw).hexdigest() != spec["sha256"]:
        _fail(f"V42r1 {spec['role']} bytes differ from the frozen failure")
    value = _document(raw, spec["role"])
    id_field = spec["id_field"]
    payload = dict(value)
    observed = payload.pop(id_field, None)
    if (
        value.get("schema") != spec["schema"]
        or observed != spec["content_id"]
        or observed != _cid(_V42_DOMAINS[id_field], payload)
    ):
        _fail(f"V42r1 {spec['role']} content ID changed")
    return value


def _verify_invocation_capture(spec: Mapping[str, Any], raw: bytes) -> None:
    if (
        spec.get("evidence_class") != "NON_FORMAL_INVOCATION_CAPTURE"
        or len(raw) != spec["byte_count"]
        or hashlib.sha256(raw).hexdigest() != spec["sha256"]
    ):
        _fail(f"V42r1 {spec['role']} invocation capture changed")


def _git(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ("git", *arguments),
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0 or result.stderr:
        _fail("V42r1 committed source audit failed")
    return result.stdout


def _verify_source_manifest(root: Path, receipt: Mapping[str, Any]) -> None:
    source = receipt.get("source_manifest")
    if type(source) is not dict:
        _fail("V42r1 prepare receipt lost its source manifest")
    payload = dict(source)
    observed = payload.pop("source_manifest_id", None)
    if (
        observed != SOURCE_MANIFEST_ID
        or receipt.get("source_manifest_id") != SOURCE_MANIFEST_ID
        or observed != _cid(_V42_DOMAINS["source_manifest_id"], payload)
        or source.get("source_commit") != SOURCE_COMMIT
        or source.get("source_tree") != SOURCE_TREE
        or source.get("source_path_count") != 90
        or source.get("allowed_source_git_modes") != ["100644"]
        or source.get("source_closure_scope")
        != "COMMITTED_REPOSITORY_PYTHON_SOURCE_ONLY"
    ):
        _fail("V42r1 source-manifest identity changed")
    if _git(root, "rev-parse", f"{SOURCE_COMMIT}^{{tree}}") != (SOURCE_TREE + "\n").encode():
        _fail("V42r1 committed source tree changed")
    facts = source.get("source_facts")
    if type(facts) is not list or len(facts) != 90:
        _fail("V42r1 source fact denominator changed")
    listing = _git(root, "ls-tree", "-r", "--full-tree", SOURCE_COMMIT)
    tree_rows = {}
    for line in listing.splitlines():
        head, path = line.split(b"\t", 1)
        mode, object_type, object_id = head.split()
        tree_rows[path.decode()] = (
            mode.decode(), object_type.decode(), object_id.decode()
        )
    for fact in facts:
        path = fact.get("relative_path")
        expected = (
            fact.get("git_mode"),
            fact.get("git_object_type"),
            fact.get("git_blob_id"),
        )
        if tree_rows.get(path) != expected or expected[:2] != ("100644", "blob"):
            _fail("V42r1 committed source fact changed")
        blob = _git(root, "cat-file", "blob", fact["git_blob_id"])
        if (
            len(blob) != fact.get("byte_count")
            or hashlib.sha256(blob).hexdigest() != fact.get("sha256")
        ):
            _fail("V42r1 committed source blob bytes changed")


def audit_original_v42_ordinal1_failure(
    repository_root: Path,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    if not isinstance(repository_root, Path) or not repository_root.is_dir():
        _fail("V42r1 repository root changed")
    raw_by_role = {}
    documents = {}
    for spec in ARTIFACT_SPECS:
        raw = _stable_read(repository_root / spec["original_relative_path"])
        raw_by_role[spec["role"]] = raw
        documents[spec["role"]] = _verify_v42_document(spec, raw)
    for spec in INVOCATION_CAPTURE_SPECS:
        raw = _stable_read(Path(spec["original_absolute_path"]))
        _verify_invocation_capture(spec, raw)
        raw_by_role[spec["role"]] = raw
    prepare = documents["PREPARE_ATTEMPT"]
    receipt = documents["PREPARE_RECEIPT"]
    launch = documents["LAUNCH_ATTEMPT"]
    attempt = documents["RUNNER_ATTEMPT"]
    worker = documents["WORKER_START"]
    consumption = documents["AUTHORITY_CONSUMPTION"]
    failure = documents["EVIDENCE_ROOT_FAILURE"]
    if raw_by_role["EVIDENCE_ROOT_FAILURE"] != raw_by_role["FIXED_PARENT_FAILURE"]:
        _fail("V42r1 two formal failure copies differ")
    if raw_by_role["PREPARE_INVOCATION_STDOUT"] != (
        raw_by_role["PREPARE_RECEIPT"] + b"\n"
    ):
        _fail("V42r1 prepare invocation stdout lost its receipt-plus-LF relation")
    common = (SOURCE_COMMIT, SOURCE_TREE, SOURCE_MANIFEST_ID)
    for document in (receipt, launch, attempt, worker):
        if tuple(document.get(key) for key in ("source_commit", "source_tree", "source_manifest_id")) != common:
            _fail("V42r1 source commit/tree/manifest join changed")
    if (
        prepare.get("prepare_ordinal") != 1
        or receipt.get("launch_ordinal") != 1
        or launch.get("launch_ordinal") != 1
        or attempt.get("attempt_ordinal") != 1
        or worker.get("worker_start_ordinal") != 1
        or consumption.get("consumption_ordinal") != 1
        or launch.get("prepare_receipt_id") != PREPARE_RECEIPT_ID
        or attempt.get("prepare_receipt_id") != PREPARE_RECEIPT_ID
        or attempt.get("runner_attempt_id") != RUNNER_ATTEMPT_ID
        or worker.get("runner_attempt_id") != RUNNER_ATTEMPT_ID
        or worker.get("worker_start_id") != WORKER_START_ID
        or consumption.get("worker_start_id") != WORKER_START_ID
        or consumption.get("authority_consumption_id") != AUTHORITY_CONSUMPTION_ID
    ):
        _fail("V42r1 ordinal or authority chain changed")
    if (
        failure.get("formal_identity") != FORMAL_IDENTITY
        or failure.get("worker_failure_classification") != "PRODUCER_EXCEPTION"
        or failure.get("failure_type") != "V42WorkerProcessError"
        or failure.get("worker_returncode") != 70
        or failure.get("runner_failure_id") != RUNNER_FAILURE_ID
        or failure.get("same_identity_rerun_forbidden") is not True
        or failure.get("scientific_success") is not False
        or failure.get("official_execution_allowed") is not False
        or failure.get("crash_resume_claimed") is not False
        or failure.get("broad_iid_or_total_work_claimed") is not False
        or failure.get("worker_stdout")
        != {
            "capture_cap_bytes": 603_979_776,
            "capture_was_bounded": True,
            "captured_byte_count": 0,
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        }
        or failure.get("worker_stderr")
        != {
            "capture_cap_bytes": 603_979_776,
            "capture_was_bounded": True,
            "captured_byte_count": 730,
            "sha256": "b8452a577a73d74b8fc26c1d01cf085a38f02388d2f5eaa8ace8101c8382e8fe",
        }
    ):
        _fail("V42r1 formal failure classification or stream hashes changed")
    evidence_root = repository_root / EVIDENCE_ROOT_RELATIVE
    entries = tuple(sorted(path.name for path in evidence_root.iterdir()))
    if entries != _EXPECTED_EVIDENCE_ROOT_ENTRIES:
        _fail("V42r1 original evidence-root inventory changed")
    if any((evidence_root / name).exists() for name in _ABSENT_FORMAL_ARTIFACTS):
        _fail("V42r1 scientific or terminal artifact unexpectedly appeared")
    authority_entries = tuple(
        sorted(path.name for path in (repository_root / AUTHORITY_ROOT_RELATIVE).iterdir())
    )
    if authority_entries != ("PREPARE_RECEIPT.json",):
        _fail("V42r1 original authority-root inventory changed")
    _verify_source_manifest(repository_root, receipt)
    inventory = [
        {
            "role": spec["role"],
            "original_relative_path": spec["original_relative_path"],
            "retained_relative_path": spec["retained_relative_path"],
            "byte_count": spec["byte_count"],
            "sha256": spec["sha256"],
            "schema": spec["schema"],
            "content_id_field": spec["id_field"],
            "content_id": spec["content_id"],
        }
        for spec in ARTIFACT_SPECS
    ]
    invocation_inventory = [
        {
            "role": spec["role"],
            "evidence_class": spec["evidence_class"],
            "original_absolute_path": spec["original_absolute_path"],
            "retained_relative_path": spec["retained_relative_path"],
            "byte_count": spec["byte_count"],
            "sha256": spec["sha256"],
            "interpretation": spec["interpretation"],
        }
        for spec in INVOCATION_CAPTURE_SPECS
    ]
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_failure_retention.v42r1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "formal_identity": FORMAL_IDENTITY,
        "retained_attempt_ordinal": 1,
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "source_manifest_id": SOURCE_MANIFEST_ID,
        "history_freshness_manifest_id": HISTORY_MANIFEST_ID,
        "fresh_terminal_preregistration_id": PREREGISTRATION_ID,
        "prepare_receipt_id": PREPARE_RECEIPT_ID,
        "runner_attempt_id": RUNNER_ATTEMPT_ID,
        "worker_start_id": WORKER_START_ID,
        "authority_consumption_id": AUTHORITY_CONSUMPTION_ID,
        "runner_failure_id": RUNNER_FAILURE_ID,
        "formal_artifact_inventory": inventory,
        "formal_artifact_count": len(inventory),
        "non_formal_invocation_capture_inventory": invocation_inventory,
        "non_formal_invocation_capture_count": len(invocation_inventory),
        "retained_file_count_excluding_manifest_and_verification": (
            len(inventory) + len(invocation_inventory)
        ),
        "retention_mode_profiles": {
            "MATERIALIZED_PRIVATE_MODE_POLICY": {
                "directory_mode_octal": "0700",
                "file_mode_octal": "0400",
            },
            "GIT_RETAINED_REGULAR_MODE": {
                "directory_mode_octal": "0755",
                "file_mode_octal": "0644",
            },
        },
        "materializer_emits_mode_profile": "MATERIALIZED_PRIVATE_MODE_POLICY",
        "git_retained_mode_profile_supported": True,
        "retained_bundle_fresh_clone_self_sufficient": True,
        "live_original_paths_required_for_independent_reverification": False,
        "live_original_bytes_if_present_must_match": True,
        "invocation_captures_are_not_fixed_formal_evidence": True,
        "invocation_captures_are_not_formal_worker_streams": True,
        "two_failure_copies_byte_identical": True,
        "original_evidence_root_entries": list(entries),
        "original_authority_root_entries": list(authority_entries),
        "formal_artifact_absence": {name: True for name in _ABSENT_FORMAL_ARTIFACTS},
        "formal_worker_failure_classification": "PRODUCER_EXCEPTION",
        "formal_failure_type": "V42WorkerProcessError",
        "formal_worker_returncode": 70,
        "formal_stdout_fact": failure["worker_stdout"],
        "formal_stderr_fact": failure["worker_stderr"],
        "formal_worker_stdout_or_stderr_capture_bytes_retained_separately": False,
        "formal_worker_stream_content_reconstruction_claimed": False,
        "operator_observation": dict(OPERATOR_OBSERVATION),
        "operator_observation_is_not_formal_oom_proof": True,
        "formal_classification_rewritten_as_oom": False,
        "same_identity_rerun_forbidden": True,
        "ordinal2_authority_constructed": False,
        "ordinal2_execution_performed": False,
        "formal_campaign_artifact_present": False,
        "formal_verification_artifact_present": False,
        "formal_terminal_artifact_present": False,
        "scientific_success": False,
        "scientific_claim_issued": False,
        "broad_iid_or_total_work_claimed": False,
        "crash_resume_claimed": False,
        "official_execution_allowed": False,
    }
    manifest = {
        **payload,
        "retention_manifest_id": _cid(RETENTION_DOMAIN, payload),
    }
    return manifest, raw_by_role


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_CLOEXEC | _O_NOFOLLOW,
        0o400,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                _fail("V42r1 retained write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)


def materialize_v42_ordinal1_failure_retention(
    *, repository_root: Path, retention_root: Path
) -> dict[str, Any]:
    if retention_root.exists() or not retention_root.parent.is_dir():
        _fail("V42r1 retention root must be absent under an existing parent")
    manifest, raw_by_role = audit_original_v42_ordinal1_failure(repository_root)
    retention_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(retention_root, 0o700)
    _fsync_directory(retention_root.parent)
    artifacts = retention_root / "artifacts"
    artifacts.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(artifacts, 0o700)
    _fsync_directory(retention_root)
    invocation_captures = retention_root / "invocation_captures"
    invocation_captures.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(invocation_captures, 0o700)
    _fsync_directory(retention_root)
    for spec in ARTIFACT_SPECS:
        _write_once(
            retention_root / spec["retained_relative_path"],
            raw_by_role[spec["role"]],
        )
    for spec in INVOCATION_CAPTURE_SPECS:
        _write_once(
            retention_root / spec["retained_relative_path"],
            raw_by_role[spec["role"]],
        )
    _write_once(
        retention_root / "RETENTION_MANIFEST.json",
        canonical_json_bytes(manifest),
    )
    return manifest


__all__ = (
    "ARTIFACT_SPECS",
    "DEFAULT_RETENTION_ROOT_RELATIVE",
    "INVOCATION_CAPTURE_SPECS",
    "OPERATOR_OBSERVATION",
    "RETENTION_DOMAIN",
    "Standard2048FreshTerminalFailureRetentionV42R1Error",
    "audit_original_v42_ordinal1_failure",
    "materialize_v42_ordinal1_failure_retention",
)
