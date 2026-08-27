"""Independently verify the immutable V42 ordinal-1 failure retention.

This verifier deliberately does not import the V42 producer, campaign,
execution-authority, runner, supervisor, or the V42r1 retention producer.  It
accepts only the frozen bytes listed below, independently recomputes every
content ID, rechecks the committed 90-path source closure, and preserves the
formal ``PRODUCER_EXCEPTION`` classification.  The separately recorded
operator observation is post-hoc context only and is never treated as formal
OOM proof.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42r1.0.0"
PROFILE_KEY = (
    "construction_k7_standard_2048_fresh_terminal_failure_retention_"
    "independent_verifier_v42r1"
)
RETENTION_DOMAIN = (
    "acfqp:construction-k7-standard-2048-fresh-terminal-ordinal1-"
    "failure-retention:v42r1"
)
VERIFICATION_DOMAIN = (
    "acfqp:construction-k7-standard-2048-fresh-terminal-ordinal1-"
    "failure-retention-independent-verification:v42r1"
)
EXPECTED_RETENTION_MANIFEST_ID = (
    "5ab73d90b63675fe4255c0bf6cd2116444a52b5b0009cd6cf822f4fbf7b6ce66"
)
EXPECTED_INDEPENDENT_VERIFICATION_ID = (
    "6c088a5515a096ce363c7ab9a834d9ed9c22da87a63d4ed59d1d68e78167db3b"
)
SOURCE_COMMIT = "c48f269b6293ad7a1d8f4e6ab5ff1b098357264b"
SOURCE_TREE = "4744cc0638fbfa4cd677c0701f003ce01eed1a86"
SOURCE_MANIFEST_ID = "11a897dfb2292f29f8048ea2f95dcacb552405b662775ae57a5d9adb6468401d"
HISTORY_MANIFEST_ID = "c94d62bbcaa3cea0869a4a00b0944808b5e893a7a4c276e93a3b583df4aa5d29"
PREREGISTRATION_ID = "575e06a306c9dcee816bc5d1ba431ef163d084ae174614d4b3b1b4b4358ff5b3"
PREPARE_RECEIPT_ID = "7fd00460ff58f4deacef516e40e3e2fc0f595e24a6db6f44d9baa25af638145c"
RUNNER_ATTEMPT_ID = "d42ed122534d87d60135a1c949872766d99ad15eaa1ac61dad6f3f040fddb58e"
WORKER_START_ID = "07a39b80b7e29b27af76a1e73ab9bd5df8728a69b07745dd31caa930ed046136"
AUTHORITY_CONSUMPTION_ID = (
    "88946c26382cdcc9d8930fd30895df0cc98045e74445d9f3b4c8c3da2d6631b2"
)
RUNNER_FAILURE_ID = "c5ab25e29efef47c22d2ccbbaa5867f11b51e9fadaecab321e60fc3dc879d354"
FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_ORDINAL_1"
EVIDENCE_ROOT_RELATIVE = ".tmp/exact-freeze/v42_standard_2048_fresh_terminal_execution"
AUTHORITY_ROOT_RELATIVE = ".tmp/exact-freeze/v42_standard_2048_fresh_terminal_authority"


_V42_DOMAINS = {
    "prepare_attempt_journal_id": (
        "acfqp:construction-k7-standard-2048-fresh-terminal-prepare-journal:v42"
    ),
    "prepare_receipt_id": (
        "acfqp:construction-k7-standard-2048-fresh-terminal-prepare-receipt:v42"
    ),
    "launch_attempt_journal_id": (
        "acfqp:construction-k7-standard-2048-fresh-terminal-launch-journal:v42"
    ),
    "runner_attempt_id": (
        "acfqp:construction-k7-standard-2048-fresh-terminal-runner-attempt:v42"
    ),
    "worker_start_id": (
        "acfqp:construction-k7-standard-2048-fresh-terminal-worker-start:v42"
    ),
    "authority_consumption_id": (
        "acfqp:construction-k7-standard-2048-fresh-terminal-authority-consumption:v42"
    ),
    "runner_failure_id": (
        "acfqp:construction-k7-standard-2048-fresh-terminal-runner-failure:v42"
    ),
    "source_manifest_id": (
        "acfqp:construction-k7-standard-2048-fresh-terminal-source-manifest:v42"
    ),
}


_ARTIFACTS = (
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

_INVOCATION_CAPTURES = (
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

_OPERATOR_OBSERVATION = {
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

_EVIDENCE_ENTRIES = (
    "ATTEMPT.json",
    "AUTHORITY_CONSUMPTION.json",
    "FAILURE.json",
    "WORKER_START.json",
)
_ABSENT_FORMAL_ARTIFACTS = ("CAMPAIGN.json", "VERIFICATION.json", "TERMINAL.json")
_FORBIDDEN_MODULES = (
    "acfqp.construction_k7_standard_2048_execution_authority_v42",
    "acfqp.construction_k7_standard_2048_fresh_terminal_campaign_v42",
    "acfqp.construction_k7_standard_2048_fresh_terminal_independent_verifier_v42",
    "acfqp.construction_k7_standard_2048_fresh_terminal_failure_retention_v42r1",
    "scripts.run_v42_standard_2048_fresh_terminal_campaign",
    "scripts.supervise_v42_standard_2048_fresh_terminal_campaign",
)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class Standard2048FreshTerminalFailureRetentionIndependentVerificationV42R1Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise Standard2048FreshTerminalFailureRetentionIndependentVerificationV42R1Error(
        message
    )


def _cid(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _stable_read(
    path: Path, *, cap: int = 64 * 1024 * 1024, expected_mode: int | None = None
) -> bytes:
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        _fail("V42r1 verifier input is not one linked regular file")
    if expected_mode is not None and stat.S_IMODE(before.st_mode) != expected_mode:
        _fail("V42r1 retained file mode changed")
    descriptor = os.open(path, os.O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("V42r1 verifier input identity raced")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1 << 20, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > cap:
                _fail("V42r1 verifier input exceeded its cap")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    named = os.lstat(path)
    identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if identity != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        _fail("V42r1 verifier input changed during read")
    if identity != (named.st_dev, named.st_ino, named.st_size, named.st_mtime_ns):
        _fail("V42r1 verifier input mapping changed")
    return b"".join(chunks)


def _document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise Standard2048FreshTerminalFailureRetentionIndependentVerificationV42R1Error(
            f"V42r1 {label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"V42r1 {label} bytes changed")
    return value


def _git(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ("git", *arguments),
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0 or result.stderr:
        _fail("V42r1 verifier committed-source audit failed")
    return result.stdout


def _verify_document(spec: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
    if len(raw) != spec["byte_count"] or hashlib.sha256(raw).hexdigest() != spec["sha256"]:
        _fail(f"V42r1 retained {spec['role']} bytes changed")
    value = _document(raw, spec["role"])
    payload = dict(value)
    observed = payload.pop(spec["id_field"], None)
    if (
        value.get("schema") != spec["schema"]
        or observed != spec["content_id"]
        or observed != _cid(_V42_DOMAINS[spec["id_field"]], payload)
    ):
        _fail(f"V42r1 retained {spec['role']} content ID changed")
    return value


def _verify_source_manifest(root: Path, receipt: Mapping[str, Any]) -> None:
    source = receipt.get("source_manifest")
    if type(source) is not dict:
        _fail("V42r1 retained receipt lost its source manifest")
    payload = dict(source)
    observed = payload.pop("source_manifest_id", None)
    if (
        observed != SOURCE_MANIFEST_ID
        or receipt.get("source_manifest_id") != SOURCE_MANIFEST_ID
        or observed != _cid(_V42_DOMAINS["source_manifest_id"], payload)
        or source.get("schema")
        != "acfqp.standard_2048_fresh_terminal_source_manifest.v42"
        or source.get("source_commit") != SOURCE_COMMIT
        or source.get("source_tree") != SOURCE_TREE
        or source.get("source_path_count") != 90
        or source.get("allowed_source_git_modes") != ["100644"]
        or source.get("source_closure_scope")
        != "COMMITTED_REPOSITORY_PYTHON_SOURCE_ONLY"
        or source.get("resolver_version") != "PYTHON_STATIC_IMPORT_CLOSURE_V2"
        or source.get("external_python_distributions_excluded") is not True
        or source.get("non_python_resources_excluded") is not True
        or source.get("stdlib_and_interpreter_sources_excluded") is not True
    ):
        _fail("V42r1 retained source-manifest identity or scope changed")
    if _git(root, "rev-parse", f"{SOURCE_COMMIT}^{{tree}}") != (
        SOURCE_TREE + "\n"
    ).encode():
        _fail("V42r1 retained committed source tree changed")
    facts = source.get("source_facts")
    if type(facts) is not list or len(facts) != 90:
        _fail("V42r1 retained source-fact denominator changed")
    listing = _git(root, "ls-tree", "-r", "--full-tree", SOURCE_COMMIT)
    tree_rows = {}
    for line in listing.splitlines():
        head, encoded_path = line.split(b"\t", 1)
        mode, object_type, object_id = head.split()
        tree_rows[encoded_path.decode("utf-8", errors="strict")] = (
            mode.decode(),
            object_type.decode(),
            object_id.decode(),
        )
    observed_paths = []
    for fact in facts:
        if type(fact) is not dict:
            _fail("V42r1 retained source fact is not an object")
        path = fact.get("relative_path")
        expected = (
            fact.get("git_mode"),
            fact.get("git_object_type"),
            fact.get("git_blob_id"),
        )
        if type(path) is not str or tree_rows.get(path) != expected:
            _fail("V42r1 retained source fact changed")
        if expected[:2] != ("100644", "blob"):
            _fail("V42r1 retained source mode or object type changed")
        blob = _git(root, "cat-file", "blob", expected[2])
        if (
            len(blob) != fact.get("byte_count")
            or hashlib.sha256(blob).hexdigest() != fact.get("sha256")
        ):
            _fail("V42r1 retained committed source blob bytes changed")
        observed_paths.append(path)
    if len(set(observed_paths)) != 90 or observed_paths != sorted(observed_paths):
        _fail("V42r1 retained source paths are duplicate or unsorted")


def _expected_manifest() -> dict[str, Any]:
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
        for spec in _ARTIFACTS
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
        for spec in _INVOCATION_CAPTURES
    ]
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_failure_retention.v42r1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": (
            "construction_k7_standard_2048_fresh_terminal_failure_retention_v42r1"
        ),
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
        "formal_artifact_count": 8,
        "non_formal_invocation_capture_inventory": invocation_inventory,
        "non_formal_invocation_capture_count": 4,
        "retained_file_count_excluding_manifest_and_verification": 12,
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
        "original_evidence_root_entries": list(_EVIDENCE_ENTRIES),
        "original_authority_root_entries": ["PREPARE_RECEIPT.json"],
        "formal_artifact_absence": {name: True for name in _ABSENT_FORMAL_ARTIFACTS},
        "formal_worker_failure_classification": "PRODUCER_EXCEPTION",
        "formal_failure_type": "V42WorkerProcessError",
        "formal_worker_returncode": 70,
        "formal_stdout_fact": {
            "capture_cap_bytes": 603_979_776,
            "capture_was_bounded": True,
            "captured_byte_count": 0,
            "sha256": (
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            ),
        },
        "formal_stderr_fact": {
            "capture_cap_bytes": 603_979_776,
            "capture_was_bounded": True,
            "captured_byte_count": 730,
            "sha256": (
                "b8452a577a73d74b8fc26c1d01cf085a38f02388d2f5eaa8ace8101c8382e8fe"
            ),
        },
        "formal_worker_stdout_or_stderr_capture_bytes_retained_separately": False,
        "formal_worker_stream_content_reconstruction_claimed": False,
        "operator_observation": dict(_OPERATOR_OBSERVATION),
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
    return {**payload, "retention_manifest_id": _cid(RETENTION_DOMAIN, payload)}


def _verify_root_inventory(retention_root: Path) -> tuple[str, int]:
    root_stat = os.lstat(retention_root)
    root_mode = stat.S_IMODE(root_stat.st_mode)
    mode_profiles = {
        0o700: ("MATERIALIZED_PRIVATE_MODE_POLICY", 0o400),
        0o755: ("GIT_RETAINED_REGULAR_MODE", 0o644),
    }
    if not stat.S_ISDIR(root_stat.st_mode) or root_mode not in mode_profiles:
        _fail("V42r1 retention root type or mode profile changed")
    profile_name, file_mode = mode_profiles[root_mode]
    allowed = {
        "artifacts",
        "invocation_captures",
        "RETENTION_MANIFEST.json",
        "INDEPENDENT_VERIFICATION.json",
    }
    entries = {entry.name for entry in retention_root.iterdir()}
    if entries not in (
        {"artifacts", "invocation_captures", "RETENTION_MANIFEST.json"},
        allowed,
    ):
        _fail("V42r1 retention-root inventory changed")
    artifacts = retention_root / "artifacts"
    artifacts_stat = os.lstat(artifacts)
    if (
        not stat.S_ISDIR(artifacts_stat.st_mode)
        or stat.S_IMODE(artifacts_stat.st_mode) != root_mode
    ):
        _fail("V42r1 retained artifact directory type or mode changed")
    expected = {Path(spec["retained_relative_path"]).name for spec in _ARTIFACTS}
    if {entry.name for entry in artifacts.iterdir()} != expected:
        _fail("V42r1 retained artifact inventory changed")
    captures = retention_root / "invocation_captures"
    captures_stat = os.lstat(captures)
    if (
        not stat.S_ISDIR(captures_stat.st_mode)
        or stat.S_IMODE(captures_stat.st_mode) != root_mode
    ):
        _fail("V42r1 invocation-capture directory type or mode changed")
    expected_captures = {
        Path(spec["retained_relative_path"]).name for spec in _INVOCATION_CAPTURES
    }
    if {entry.name for entry in captures.iterdir()} != expected_captures:
        _fail("V42r1 invocation-capture inventory changed")
    return profile_name, file_mode


def _verification_document(manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": (
            "acfqp.standard_2048_fresh_terminal_failure_retention_"
            "independent_verification.v42r1"
        ),
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "formal_identity": FORMAL_IDENTITY,
        "retention_manifest_id": manifest["retention_manifest_id"],
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
        "verified_formal_artifact_count": 8,
        "verified_non_formal_invocation_capture_count": 4,
        "verified_retained_file_count_excluding_manifest_and_verification": 12,
        "all_retained_artifact_bytes_exact": True,
        "all_non_formal_invocation_capture_bytes_exact": True,
        "invocation_captures_are_not_fixed_formal_evidence": True,
        "invocation_captures_are_not_formal_worker_streams": True,
        "all_retained_v42_content_ids_recomputed": True,
        "all_retained_artifact_bytes_match_frozen_original_hashes": True,
        "retained_bundle_fresh_clone_self_sufficient": True,
        "live_original_paths_required_for_independent_reverification": False,
        "live_original_bytes_if_present_must_match": True,
        "accepted_retention_mode_profiles": [
            "MATERIALIZED_PRIVATE_MODE_POLICY",
            "GIT_RETAINED_REGULAR_MODE",
        ],
        "one_complete_retention_mode_profile_verified": True,
        "source_closure_path_count": 90,
        "source_closure_commit_tree_blob_bytes_reverified": True,
        "two_failure_copies_byte_identical": True,
        "formal_worker_failure_classification": "PRODUCER_EXCEPTION",
        "operator_observation_evidence_class": "POST_HOC_OPERATOR_OBSERVATION_ONLY",
        "operator_observation_is_not_formal_oom_proof": True,
        "formal_oom_proof_present": False,
        "formal_classification_rewritten_as_oom": False,
        "stdout_hash_verified": True,
        "stderr_hash_verified": True,
        "formal_worker_stdout_or_stderr_capture_bytes_retained_separately": False,
        "formal_campaign_artifact_absent": True,
        "formal_verification_artifact_absent": True,
        "formal_terminal_artifact_absent": True,
        "same_identity_rerun_forbidden": True,
        "ordinal2_authority_constructed": False,
        "ordinal2_execution_performed": False,
        "scientific_success": False,
        "scientific_claim_issued": False,
        "official_execution_allowed": False,
        "producer_or_v42_formal_module_imported": False,
        "fresh_python_isolated_flag": True,
        "fresh_python_no_site_flag": True,
        "fresh_python_no_bytecode_flag": True,
    }
    return {
        **payload,
        "independent_verification_id": _cid(VERIFICATION_DOMAIN, payload),
    }


def verify_v42_ordinal1_failure_retention_independently(
    *, repository_root: Path, retention_root: Path
) -> dict[str, Any]:
    if any(name in sys.modules for name in _FORBIDDEN_MODULES):
        _fail("V42r1 verifier process imported a producer or V42 formal module")
    if not (
        sys.flags.isolated == 1
        and sys.flags.no_site == 1
        and sys.flags.dont_write_bytecode == 1
    ):
        _fail("V42r1 verifier requires a fresh python -I -S -B process")
    if not isinstance(repository_root, Path) or not repository_root.is_dir():
        _fail("V42r1 verifier repository root changed")
    if not isinstance(retention_root, Path):
        _fail("V42r1 verifier retention root changed")
    _mode_profile, retained_file_mode = _verify_root_inventory(retention_root)

    manifest_raw = _stable_read(
        retention_root / "RETENTION_MANIFEST.json",
        expected_mode=retained_file_mode,
    )
    manifest = _document(manifest_raw, "retention manifest")
    expected_manifest = _expected_manifest()
    if (
        expected_manifest["retention_manifest_id"] != EXPECTED_RETENTION_MANIFEST_ID
        or manifest != expected_manifest
    ):
        _fail("V42r1 retention manifest changed or self-rebound")

    raw_by_role = {}
    documents = {}
    for spec in _ARTIFACTS:
        retained = _stable_read(
            retention_root / spec["retained_relative_path"],
            expected_mode=retained_file_mode,
        )
        original_path = repository_root / spec["original_relative_path"]
        try:
            original = _stable_read(original_path)
        except FileNotFoundError:
            original = None
        if original is not None and retained != original:
            _fail(f"V42r1 retained {spec['role']} no longer matches its original")
        raw_by_role[spec["role"]] = retained
        documents[spec["role"]] = _verify_document(spec, retained)

    capture_raw_by_role = {}
    for spec in _INVOCATION_CAPTURES:
        retained = _stable_read(
            retention_root / spec["retained_relative_path"],
            expected_mode=retained_file_mode,
        )
        if (
            spec["evidence_class"] != "NON_FORMAL_INVOCATION_CAPTURE"
            or len(retained) != spec["byte_count"]
            or hashlib.sha256(retained).hexdigest() != spec["sha256"]
        ):
            _fail(f"V42r1 retained {spec['role']} invocation capture changed")
        capture_raw_by_role[spec["role"]] = retained

    if raw_by_role["EVIDENCE_ROOT_FAILURE"] != raw_by_role["FIXED_PARENT_FAILURE"]:
        _fail("V42r1 retained formal failure copies differ")
    if capture_raw_by_role["PREPARE_INVOCATION_STDOUT"] != (
        raw_by_role["PREPARE_RECEIPT"] + b"\n"
    ):
        _fail("V42r1 retained prepare invocation capture relation changed")
    receipt = documents["PREPARE_RECEIPT"]
    failure = documents["EVIDENCE_ROOT_FAILURE"]
    if (
        failure.get("worker_failure_classification") != "PRODUCER_EXCEPTION"
        or failure.get("failure_type") != "V42WorkerProcessError"
        or failure.get("worker_returncode") != 70
        or failure.get("scientific_success") is not False
        or failure.get("same_identity_rerun_forbidden") is not True
        or failure.get("artifact_states")
        != {
            "ATTEMPT.json": "EXACT",
            "AUTHORITY_CONSUMPTION.json": "PRESENT_UNCHECKED",
            "CAMPAIGN.json": "ABSENT",
            "TERMINAL.json": "ABSENT",
            "VERIFICATION.json": "ABSENT",
            "WORKER_START.json": "PRESENT_UNCHECKED",
        }
    ):
        _fail("V42r1 retained formal failure semantics changed")

    evidence_root = repository_root / EVIDENCE_ROOT_RELATIVE
    try:
        evidence_root_stat = os.lstat(evidence_root)
    except FileNotFoundError:
        evidence_root_stat = None
    if evidence_root_stat is not None:
        if not stat.S_ISDIR(evidence_root_stat.st_mode):
            _fail("V42r1 original evidence root is not a directory")
        if tuple(sorted(entry.name for entry in evidence_root.iterdir())) != _EVIDENCE_ENTRIES:
            _fail("V42r1 original evidence-root inventory changed")
        if any((evidence_root / name).exists() for name in _ABSENT_FORMAL_ARTIFACTS):
            _fail("V42r1 original formal success artifact appeared")
    authority_root = repository_root / AUTHORITY_ROOT_RELATIVE
    try:
        authority_root_stat = os.lstat(authority_root)
    except FileNotFoundError:
        authority_root_stat = None
    if authority_root_stat is not None:
        if not stat.S_ISDIR(authority_root_stat.st_mode):
            _fail("V42r1 original authority root is not a directory")
        if tuple(sorted(entry.name for entry in authority_root.iterdir())) != (
            "PREPARE_RECEIPT.json",
        ):
            _fail("V42r1 original authority-root inventory changed")
    _verify_source_manifest(repository_root, receipt)

    verification = _verification_document(manifest)
    if (
        verification.get("independent_verification_id")
        != EXPECTED_INDEPENDENT_VERIFICATION_ID
    ):
        _fail("V42r1 independent verification identity changed")
    verification_path = retention_root / "INDEPENDENT_VERIFICATION.json"
    if verification_path.exists():
        observed = _document(
            _stable_read(verification_path, expected_mode=retained_file_mode),
            "independent verification",
        )
        if observed != verification:
            _fail("V42r1 retained independent verification changed")
    return verification


__all__ = (
    "EXPECTED_INDEPENDENT_VERIFICATION_ID",
    "EXPECTED_RETENTION_MANIFEST_ID",
    "Standard2048FreshTerminalFailureRetentionIndependentVerificationV42R1Error",
    "VERIFICATION_DOMAIN",
    "verify_v42_ordinal1_failure_retention_independently",
)
