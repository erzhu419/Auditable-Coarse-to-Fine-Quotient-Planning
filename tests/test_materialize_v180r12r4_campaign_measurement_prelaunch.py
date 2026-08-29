from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

import pytest

from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from scripts import launch_v180r12r4_campaign_measurement_prelaunch as launcher
from scripts import materialize_v180r12r4_campaign_measurement_prelaunch as materializer


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MATERIALIZER = ROOT / materializer.MATERIALIZER_RELATIVE_PATH
SOURCE_LAUNCHER = ROOT / materializer.SOURCE_LAUNCHER_RELATIVE_PATH
SOURCE_BOOTSTRAP = ROOT / materializer.SOURCE_BOOTSTRAP_RELATIVE_PATH
PYTHON = "/usr/bin/python3"
GIT = "/usr/bin/git"
ISOLATED_FLAGS = (
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={materializer.PYCACHE_PREFIX}",
)
ZERO_ID = "0" * 64
TEST_SOURCE_CLOSURE_RULE_ID = hashlib.sha256(
    _canonical(materializer.SOURCE_CLOSURE_RULE_DOCUMENT)
    if "_canonical" in globals()
    else json.dumps(
        materializer.SOURCE_CLOSURE_RULE_DOCUMENT,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
).hexdigest()
TEST_MATERIALIZATION_RULE_ID = hashlib.sha256(
    json.dumps(
        materializer.MATERIALIZATION_RULE_DOCUMENT,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
).hexdigest()
_TEST_LAUNCH_RULE_DOCUMENT = copy.deepcopy(launcher.LAUNCH_RULE_DOCUMENT)
_TEST_LAUNCH_RULE_DOCUMENT["source_closure_rule_id"] = TEST_SOURCE_CLOSURE_RULE_ID
_TEST_LAUNCH_RULE_DOCUMENT["materialization_rule_id"] = (
    TEST_MATERIALIZATION_RULE_ID
)
TEST_LAUNCH_RULE_ID = hashlib.sha256(
    json.dumps(
        _TEST_LAUNCH_RULE_DOCUMENT,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
).hexdigest()


@pytest.fixture
def tmp_path() -> Path:
    """Use the native Linux filesystem so POSIX mode assertions are meaningful."""

    path = Path(tempfile.mkdtemp(prefix="v180r12r4-materializer-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _git(repository: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        [GIT, "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        env={
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        },
    )
    assert completed.stderr == b""
    return completed.stdout


def _commit(repository: Path, message: str, *, allow_empty: bool = False) -> str:
    arguments = [
        "-c",
        "user.name=V180r12r4 Test",
        "-c",
        "user.email=v180r12r4@example.invalid",
        "commit",
        "-q",
    ]
    if allow_empty:
        arguments.append("--allow-empty")
    arguments.extend(["-m", message])
    subprocess.run(
        [GIT, "-C", str(repository), *arguments],
        check=True,
        env={
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
        },
    )
    return _git(repository, "rev-parse", "HEAD").decode("ascii").strip()


def _write(repository: Path, relative: str, source: str | bytes) -> None:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(source, bytes):
        path.write_bytes(source)
    else:
        path.write_text(source, encoding="utf-8")


def _freeze_test_materializer_source(raw: bytes) -> bytes:
    text = raw.decode("utf-8")
    replacements = {
        "EXPECTED_SOURCE_CLOSURE_RULE_ID": TEST_SOURCE_CLOSURE_RULE_ID,
        "EXPECTED_MATERIALIZATION_RULE_ID": TEST_MATERIALIZATION_RULE_ID,
    }
    for name, value in replacements.items():
        current = getattr(materializer, name)
        assert current in {ZERO_ID, value}
        old = f'{name} = (\n    "{current}"\n)'
        new = f'{name} = (\n    "{value}"\n)'
        assert text.count(old) == 1
        text = text.replace(old, new)
    return text.encode("utf-8")


def _freeze_test_launcher_source(
    raw: bytes,
    *,
    launch_rule_id: str = TEST_LAUNCH_RULE_ID,
) -> bytes:
    text = raw.decode("utf-8")
    replacements = {
        "EXPECTED_SOURCE_CLOSURE_RULE_ID": TEST_SOURCE_CLOSURE_RULE_ID,
        "EXPECTED_MATERIALIZATION_RULE_ID": TEST_MATERIALIZATION_RULE_ID,
        "EXPECTED_LAUNCH_RULE_ID": launch_rule_id,
    }
    base_expected = {
        "EXPECTED_SOURCE_CLOSURE_RULE_ID": TEST_SOURCE_CLOSURE_RULE_ID,
        "EXPECTED_MATERIALIZATION_RULE_ID": TEST_MATERIALIZATION_RULE_ID,
        "EXPECTED_LAUNCH_RULE_ID": TEST_LAUNCH_RULE_ID,
    }
    for name, value in replacements.items():
        current = getattr(launcher, name)
        assert current in {ZERO_ID, base_expected[name]}
        old = f'{name} = (\n    "{current}"\n)'
        new = f'{name} = (\n    "{value}"\n)'
        assert text.count(old) == 1
        text = text.replace(old, new)
    return text.encode("utf-8")


def _direct_anchor_source(
    values: dict[str, object],
    names: tuple[str, ...],
    *,
    nonliteral_name: str | None = None,
) -> str:
    lines = [f'ZERO_ID = "{ZERO_ID}"'] if nonliteral_name is not None else []
    for name in names:
        if name == nonliteral_name:
            lines.append(f"{name} = ZERO_ID")
        else:
            lines.append(f"{name} = {values[name]!r}")
    lines.append("from acfqp import leaf")
    return "\n".join(lines) + "\n"


def _protocol_anchor_values() -> dict[str, object]:
    context = _frozen_authorization_context()
    return {
        "EXPECTED_PROTOCOL_ID": context["protocol_id"],
        "EXPECTED_CANONICAL_BYTE_COUNT": context["protocol_byte_count"],
        "EXPECTED_CANONICAL_SHA256": context["protocol_sha256"],
        "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID": context[
            "campaign_measurement_execution_slot_id"
        ],
        "LOGICAL_OCCURRENCE_ID": context["logical_occurrence_id"],
        "EXECUTION_NONCE": context["execution_nonce"],
        "EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID": (
            TEST_SOURCE_CLOSURE_RULE_ID
        ),
        "EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID": (
            TEST_MATERIALIZATION_RULE_ID
        ),
        "EXPECTED_PRELAUNCH_LAUNCH_RULE_ID": TEST_LAUNCH_RULE_ID,
    }


def _wrapper_source(value: str, count: int, *, suffix: str = "") -> str:
    values = {
        name: (
            value
            if name in materializer._WRAPPER_STRING_CONSTANT_NAMES
            else count
        )
        for name in materializer.WRAPPER_REDACTED_CONSTANT_NAMES
    }
    return _wrapper_source_values(values, suffix=suffix)


def _wrapper_source_values(
    values: dict[str, object],
    *,
    suffix: str = "",
) -> str:
    names = materializer.WRAPPER_REDACTED_CONSTANT_NAMES
    assert set(values) == set(names)
    lines: list[str] = []
    for name in names:
        if name in materializer._WRAPPER_STRING_CONSTANT_NAMES:
            assert type(values[name]) is str
            lines.append(f'{name} = "{values[name]}"')
        else:
            assert type(values[name]) is int
            lines.append(f"{name} = {values[name]}")
    return "\n".join(lines) + "\n" + suffix


def _frozen_wrapper_values(
    repository: Path,
    c_pre: str,
    external: dict[str, object],
) -> dict[str, object]:
    facts: list[dict[str, object]] = []
    for relative in materializer.SOURCE_CLOSURE_REQUIRED_ROOTS:
        raw = _git(repository, "show", f"{c_pre}:{relative}")
        if relative == materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH:
            raw, _values = materializer._normalize_wrapper(raw)
        facts.append(materializer._raw_fact(relative, raw))
    source_payload = {
        "schema": "acfqp.v180r12r4_authorization_source_closure.v1",
        "source_facts": facts,
        "source_fact_count": len(facts),
        "source_total_byte_count": sum(row["byte_count"] for row in facts),
        "required_static_roots": list(
            materializer.SOURCE_CLOSURE_REQUIRED_ROOTS
        ),
        "transitive_local_import_closure_required": True,
        "authorization_self_normalized_by_evidence_freeze": True,
    }
    source_raw = _canonical(source_payload)
    source_id = hashlib.sha256(source_raw).hexdigest()
    authorization_fact = next(
        row
        for row in facts
        if row["relative_path"] == materializer.AUTHORIZATION_SELF_RELATIVE_PATH
    )
    context = external["frozen_authorization_context"]
    assert type(context) is dict
    return {
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID": context[
            "authorization_evidence_id"
        ],
        "EXPECTED_CANONICAL_BYTE_COUNT": context[
            "authorization_evidence_byte_count"
        ],
        "EXPECTED_CANONICAL_SHA256": context[
            "authorization_evidence_sha256"
        ],
        "EXPECTED_AUTHORIZATION_ID": context["authorization_id"],
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT": context[
            "authorization_byte_count"
        ],
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256": context[
            "authorization_sha256"
        ],
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT": authorization_fact[
            "byte_count"
        ],
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256": authorization_fact["sha256"],
        "EXPECTED_SOURCE_CLOSURE_ID": source_id,
        "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT": len(source_raw),
        "EXPECTED_SOURCE_CLOSURE_SHA256": source_id,
        "EXPECTED_SOURCE_CLOSURE_FILE_COUNT": len(facts),
    }


def _raw_git_fact(repository: Path, commit: str, relative: str) -> dict[str, object]:
    line = _git(repository, "ls-tree", commit, "--", relative).decode("utf-8").strip()
    prefix, observed = line.split("\t", 1)
    mode, kind, object_id = prefix.split(" ")
    assert observed == relative and kind == "blob"
    raw = _git(repository, "cat-file", "blob", object_id)
    return {
        "relative_path": relative,
        "git_mode": mode,
        "git_blob_id": object_id,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _source_fixture(
    repository: Path,
    *,
    anchor_mutation: str | None = None,
) -> None:
    protocol_values = _protocol_anchor_values()
    protocol_nonliteral: str | None = None
    authorization_values = {
        "EXPECTED_PROTOCOL_ID": protocol_values["EXPECTED_PROTOCOL_ID"],
        "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID": protocol_values[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ],
    }
    authorization_nonliteral: str | None = None
    launcher_launch_rule_id = TEST_LAUNCH_RULE_ID
    if anchor_mutation == "protocol_zero":
        protocol_values["EXPECTED_PROTOCOL_ID"] = ZERO_ID
    elif anchor_mutation == "protocol_nonliteral":
        protocol_nonliteral = "EXPECTED_PROTOCOL_ID"
    elif anchor_mutation == "protocol_launch_rule_mismatch":
        protocol_values["EXPECTED_PRELAUNCH_LAUNCH_RULE_ID"] = "a" * 64
    elif anchor_mutation == "coordinated_launch_rule_resign":
        protocol_values["EXPECTED_PRELAUNCH_LAUNCH_RULE_ID"] = "a" * 64
        launcher_launch_rule_id = "a" * 64
    elif anchor_mutation == "authorization_slot_mismatch":
        authorization_values[
            "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID"
        ] = "f" * 64
    elif anchor_mutation == "authorization_nonliteral":
        authorization_nonliteral = "EXPECTED_PROTOCOL_ID"
    elif anchor_mutation not in {None, "context_protocol_sha_mismatch"}:
        raise AssertionError(f"unknown anchor mutation: {anchor_mutation}")
    _write(
        repository,
        materializer.MATERIALIZER_RELATIVE_PATH,
        _freeze_test_materializer_source(SOURCE_MATERIALIZER.read_bytes()),
    )
    _write(
        repository,
        materializer.SOURCE_LAUNCHER_RELATIVE_PATH,
        _freeze_test_launcher_source(
            SOURCE_LAUNCHER.read_bytes(),
            launch_rule_id=launcher_launch_rule_id,
        ),
    )
    _write(
        repository,
        materializer.SOURCE_BOOTSTRAP_RELATIVE_PATH,
        SOURCE_BOOTSTRAP.read_bytes(),
    )
    _write(repository, "src/acfqp/__init__.py", "")
    _write(repository, "src/acfqp/abstraction/__init__.py", "")
    _write(repository, "src/acfqp/leaf.py", "VALUE = 7\n")
    _write(
        repository,
        materializer.AUTHORIZATION_SELF_RELATIVE_PATH,
        _direct_anchor_source(
            authorization_values,
            materializer.AUTHORIZATION_FINAL_ANCHOR_NAMES,
            nonliteral_name=authorization_nonliteral,
        ),
    )
    _write(
        repository,
        materializer.PROTOCOL_SOURCE_RELATIVE_PATH,
        _direct_anchor_source(
            protocol_values,
            materializer.PROTOCOL_FINAL_ANCHOR_NAMES,
            nonliteral_name=protocol_nonliteral,
        ),
    )
    _write(
        repository,
        materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
        _wrapper_source("0" * 64, 0),
    )
    for relative in materializer.SOURCE_CLOSURE_REQUIRED_ROOTS:
        if (repository / relative).exists():
            continue
        _write(repository, relative, "from acfqp import leaf\n")


def _third_party_fixture(tmp_path: Path) -> dict[str, str]:
    packaging_root = (tmp_path / "packaging-root").absolute()
    tomli_root = (tmp_path / "tomli-root").absolute()
    _write(packaging_root, "packaging/__init__.py", "")
    _write(
        packaging_root,
        "packaging/utils.py",
        "def canonicalize_name(value):\n    return value.lower()\n",
    )
    _write(tomli_root, "tomli/__init__.py", "def loads(value):\n    return {}\n")
    return {"packaging": str(packaging_root), "tomli": str(tomli_root)}


def _frozen_authorization_context() -> dict[str, object]:
    values = {
        "protocol_id": "1" * 64,
        "authorization_id": "2" * 64,
        "authorization_evidence_id": "3" * 64,
        "campaign_measurement_execution_slot_id": "4" * 64,
        "logical_occurrence_id": "5" * 64,
        "execution_nonce": "6" * 64,
    }
    attempt_payload = {
        "schema": "acfqp.campaign_measurement_attempt.v180r12r4",
        **values,
    }
    attempt_id = hashlib.sha256(
        b"acfqp:construction-k7-campaign-measurement-attempt:v180r12r4\x00"
        + materializer.canonical_json_bytes(attempt_payload)
    ).hexdigest()
    return {
        "schema": materializer.FROZEN_AUTHORIZATION_CONTEXT_SCHEMA,
        "protocol_id": values["protocol_id"],
        "protocol_byte_count": 101,
        "protocol_sha256": "7" * 64,
        "authorization_id": values["authorization_id"],
        "authorization_byte_count": 102,
        "authorization_sha256": "8" * 64,
        "authorization_evidence_id": values["authorization_evidence_id"],
        "authorization_evidence_byte_count": 103,
        "authorization_evidence_sha256": "9" * 64,
        "campaign_measurement_execution_slot_id": values[
            "campaign_measurement_execution_slot_id"
        ],
        "logical_occurrence_id": values["logical_occurrence_id"],
        "execution_nonce": values["execution_nonce"],
        "campaign_attempt_id": attempt_id,
        "cgroup_parent_fact": {
            "schema": "acfqp.v180r12r4_cgroup_parent_fact.v1",
            "mount_point": "/sys/fs/cgroup",
            "mount_fstype": "cgroup2",
            "mount_device": 25,
            "mount_inode": 1,
            "mount_options": ["rw"],
            "parent_path": "/sys/fs/cgroup/delegated",
            "parent_device": 25,
            "parent_inode": 2,
            "owner_uid": 1000,
            "owner_gid": 1000,
            "mode": 0o755,
            "controllers": ["memory", "pids"],
            "subtree_control": ["memory", "pids"],
            "cgroup_type": "domain",
            "cgroup_namespace_inode": 3,
            "cgroup_events_present": True,
            "memory_events_present": True,
            "pids_events_present": True,
            "cgroup_kill_present": True,
            "cgroup_procs_present": True,
            "memory_peak_present": True,
            "pids_peak_present": True,
            "self_membership": "0::/",
        },
        "runtime_capability_fact": {
            "schema": "acfqp.v180r12r4_runtime_capability_fact.v1",
            "machine_architecture": "x86_64",
            "single_threaded": True,
            "clone3_probe_errno": 22,
            "clone3_syscall_recognized": True,
            "pidfd_send_signal_probe_errno": 9,
            "pidfd_send_signal_recognized": True,
            "execveat_probe_errno": 9,
            "execveat_recognized": True,
            "pidfd_wait_present": True,
            "landlock_abi": 7,
            "uid": 1000,
            "gid": 1000,
            "effective_capability_mask": 0,
            "admitted": True,
        },
    }


def _external_document(
    repository: Path,
    c_pre: str,
    c_pre_tree: str,
    third_party_roots: dict[str, str],
) -> dict[str, object]:
    return {
        "schema": materializer.EXTERNAL_ROOT_SCHEMA,
        "materialization_rule_id": TEST_MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": TEST_SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository),
        "git_directory": str(repository / ".git"),
        "c_pre_commit_id": c_pre,
        "c_pre_tree_id": c_pre_tree,
        "bootstrap_git_blob": _raw_git_fact(
            repository, c_pre, materializer.SOURCE_BOOTSTRAP_RELATIVE_PATH
        ),
        "launcher_git_blob": _raw_git_fact(
            repository, c_pre, materializer.SOURCE_LAUNCHER_RELATIVE_PATH
        ),
        "materializer_git_blob": _raw_git_fact(
            repository, c_pre, materializer.MATERIALIZER_RELATIVE_PATH
        ),
        "third_party_source_roots": third_party_roots,
        "frozen_authorization_context": _frozen_authorization_context(),
        "atomic_cgroup_birth_preflight_receipt_interface": (
            materializer._zero_preflight_receipt_interface()
        ),
        "created_before_v180r12r4_authorized_measurement_execution": True,
        "v180r12r4_outcome_bytes_accessed": False,
    }


def _write_external_root(repository: Path, document: dict[str, object]) -> tuple[Path, str]:
    path = repository / materializer.EXTERNAL_ROOT_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o600)
    raw = _canonical(document)
    path.write_bytes(raw)
    path.chmod(0o400)
    return path, hashlib.sha256(raw).hexdigest()


def _build_repository(
    tmp_path: Path,
    *,
    wrapper_suffix: str = "",
    later_commit: bool = False,
    anchor_mutation: str | None = None,
    wrapper_mutation: str | None = None,
) -> tuple[Path, Path, str, str, dict[str, object]]:
    repository = (tmp_path / "repository").absolute()
    repository.mkdir()
    subprocess.run([GIT, "-C", str(repository), "init", "-q"], check=True)
    _source_fixture(repository, anchor_mutation=anchor_mutation)
    subprocess.run([GIT, "-C", str(repository), "add", "."], check=True)
    c_pre = _commit(repository, "C_pre")
    c_pre_tree = _git(repository, "rev-parse", f"{c_pre}^{{tree}}").decode("ascii").strip()
    external = _external_document(
        repository,
        c_pre,
        c_pre_tree,
        _third_party_fixture(tmp_path),
    )
    if anchor_mutation == "context_protocol_sha_mismatch":
        external["frozen_authorization_context"]["protocol_sha256"] = "f" * 64
    _commit(repository, "empty same-tree bridge", allow_empty=True)
    wrapper_values = _frozen_wrapper_values(repository, c_pre, external)
    if wrapper_mutation is not None:
        assert wrapper_mutation in wrapper_values
        original = wrapper_values[wrapper_mutation]
        wrapper_values[wrapper_mutation] = (
            original + 1
            if type(original) is int
            else ("f" * 64 if original != "f" * 64 else "e" * 64)
        )
    _write(
        repository,
        materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
        _wrapper_source_values(wrapper_values, suffix=wrapper_suffix),
    )
    subprocess.run(
        [GIT, "-C", str(repository), "add", materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH],
        check=True,
    )
    _commit(repository, "freeze wrapper literals")
    if later_commit:
        _write(repository, "UNBOUND", "later\n")
        subprocess.run([GIT, "-C", str(repository), "add", "UNBOUND"], check=True)
        _commit(repository, "forbidden later commit")
    external_path, digest = _write_external_root(repository, external)
    return repository, external_path, digest, c_pre, external


def _invoke(repository: Path, external_path: Path, digest: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            PYTHON,
            *ISOLATED_FLAGS,
            str(repository / materializer.MATERIALIZER_RELATIVE_PATH),
            str(repository),
            str(external_path),
        ],
        cwd=repository,
        env={materializer.EXTERNAL_ROOT_SHA256_ENV: digest},
        check=False,
        capture_output=True,
        text=True,
    )


def test_public_schemas_paths_and_phase_aware_rule_identities() -> None:
    assert materializer.EXTERNAL_ROOT_RELATIVE_PATH == (
        ".tmp/exact-freeze/"
        "v180r12r4_campaign_measurement_prelaunch_external_root.json"
    )
    assert materializer.OUTPUT_ROOT_RELATIVE_PATH == (
        ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch"
    )
    assert materializer.BOOTSTRAP_RELATIVE_PATH.endswith("/bootstrap.py")
    assert materializer.RETAINED_LAUNCHER_RELATIVE_PATH.endswith("/launcher.py")
    assert materializer.LAUNCH_MANIFEST_RELATIVE_PATH.endswith("/launch_manifest.json")
    assert materializer.MATERIALIZATION_TERMINAL_RELATIVE_PATH.endswith(
        "/MATERIALIZATION_TERMINAL.json"
    )
    assert materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH == (
        ".tmp/exact-freeze/"
        "v180r12r4_campaign_measurement_prelaunch_failure.json"
    )
    rules = (
        materializer.EXPECTED_SOURCE_CLOSURE_RULE_ID,
        materializer.EXPECTED_MATERIALIZATION_RULE_ID,
    )
    assert materializer.SOURCE_CLOSURE_RULE_ID == rules[0]
    assert materializer.MATERIALIZATION_RULE_ID == rules[1]
    if all(value != ZERO_ID for value in rules):
        assert all(len(value) == 64 for value in rules)
    else:
        assert rules == (ZERO_ID, ZERO_ID)
    assert len(materializer.SOURCE_CLOSURE_REQUIRED_ROOTS) == 23
    assert materializer.SOURCE_CLOSURE_REQUIRED_ROOTS == (
        protocol.SOURCE_CLOSURE_REQUIRED_ROOTS
    )
    assert (
        "src/acfqp/construction_k7_campaign_measurement_"
        "prelaunch_failure_freeze_v180r12r3.py"
        in materializer.SOURCE_CLOSURE_REQUIRED_ROOTS
    )
    assert (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r2.py"
        in materializer.SOURCE_CLOSURE_REQUIRED_ROOTS
    )
    assert materializer.EXPECTED_SOURCE_CLOSURE_RULE_ID == (
        protocol.EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID
    )
    assert materializer.EXPECTED_MATERIALIZATION_RULE_ID == (
        protocol.EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID
    )


@pytest.mark.parametrize(
    "rule_name",
    ("SOURCE_CLOSURE_RULE_ID", "MATERIALIZATION_RULE_ID"),
)
def test_zero_rule_sentinels_refuse_before_any_durable_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule_name: str,
) -> None:
    repository = (tmp_path / "zero-sentinel-repository").absolute()
    repository.mkdir()
    external = repository / materializer.EXTERNAL_ROOT_RELATIVE_PATH
    monkeypatch.setattr(materializer, rule_name, ZERO_ID)
    with pytest.raises(
        materializer.V180r12r4PrelaunchMaterializationError,
        match="remain zero sentinels",
    ):
        materializer.materialize_prelaunch_v180r12r4(
            repository,
            external,
            ZERO_ID,
            enforce_process_boundary=False,
        )
    assert not (repository / ".tmp").exists()


def test_rule_identity_recomputes_exact_canonical_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        materializer,
        "SOURCE_CLOSURE_RULE_ID",
        hashlib.sha256(
            _canonical(materializer.SOURCE_CLOSURE_RULE_DOCUMENT)
        ).hexdigest(),
    )
    monkeypatch.setattr(
        materializer,
        "MATERIALIZATION_RULE_ID",
        hashlib.sha256(
            _canonical(materializer.MATERIALIZATION_RULE_DOCUMENT)
        ).hexdigest(),
    )
    materializer._require_rule_identities_frozen()
    monkeypatch.setitem(
        materializer.MATERIALIZATION_RULE_DOCUMENT,
        "write_rule",
        "RESIGNED_BUT_WEAKENED",
    )
    with pytest.raises(
        materializer.V180r12r4PrelaunchMaterializationError,
        match="identity binding changed",
    ):
        materializer._require_rule_identities_frozen()


def test_restricted_static_launcher_reconstruction_matches_live_semantics() -> None:
    reconstructed = materializer._reconstructed_launcher_rule_v180r12r4(
        SOURCE_LAUNCHER.read_bytes()
    )
    assert reconstructed == launcher.LAUNCH_RULE_DOCUMENT
    assert _canonical(reconstructed) == _canonical(launcher.LAUNCH_RULE_DOCUMENT)
    mutated = SOURCE_LAUNCHER.read_bytes() + (
        b'\nLAUNCH_RULE_DOCUMENT["campaign_actual_measurement"] = True\n'
    )
    with pytest.raises(
        materializer.V180r12r4PrelaunchMaterializationError,
        match="normalized static rule source changed",
    ):
        materializer._reconstructed_launcher_rule_v180r12r4(mutated)


@pytest.mark.parametrize(
    "mutated",
    (
        SOURCE_LAUNCHER.read_bytes().replace(
            b"LAUNCH_RULE_DOCUMENT = {",
            b'SUCCESS_DURABLE_WRITE_ORDER += ("EVIL",)\nLAUNCH_RULE_DOCUMENT = {',
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b"LAUNCH_RULE_DOCUMENT = {",
            b'SUCCESS_DURABLE_WRITE_ORDER.append("EVIL")\nLAUNCH_RULE_DOCUMENT = {',
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b"LAUNCH_RULE_DOCUMENT = {",
            b"FORWARD_REFERENCE = LATER_VALUE\nLATER_VALUE = 1\n"
            b"LAUNCH_RULE_DOCUMENT = {",
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b"LAUNCH_RULE_DOCUMENT = {",
            b"RuntimeError = 1\nLAUNCH_RULE_DOCUMENT = {",
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b"import hashlib\n",
            b"import hostile_import as hashlib\n",
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b"LAUNCH_RULE_ID = EXPECTED_LAUNCH_RULE_ID",
            b"hashlib = EXPECTED_LAUNCH_RULE_ID",
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b"LAUNCH_RULE_ID = EXPECTED_LAUNCH_RULE_ID",
            b'LAUNCH_RULE_ID = "ffffffffffffffffffffffffffffffff'
            b'ffffffffffffffffffffffffffffffff"',
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b"_NORMALIZED_WRAPPER_FACT_KEYS = _RAW_FACT_KEYS | {",
            b"_NORMALIZED_WRAPPER_FACT_KEYS = UNDEFINED_NAME | {",
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b"class V180r12r4PrelaunchLaunchError",
            b"def _evil(_value=LAUNCH_RULE_DOCUMENT.pop("
            b'"campaign_actual_measurement")):\n    pass\n\nclass '
            b"V180r12r4PrelaunchLaunchError",
            1,
        ),
        SOURCE_LAUNCHER.read_bytes().replace(
            b'if __name__ == "__main__":\n    main()',
            b'if __name__ == "__main__":\n'
            b'    LAUNCH_RULE_DOCUMENT["campaign_actual_measurement"] = True\n'
            b"    main()",
            1,
        ),
    ),
)
def test_launcher_rule_reconstruction_rejects_every_import_time_mutation(
    mutated: bytes,
) -> None:
    assert mutated != SOURCE_LAUNCHER.read_bytes()
    with pytest.raises(
        materializer.V180r12r4PrelaunchMaterializationError,
    ):
        materializer._RestrictedStaticLauncherEvaluator(mutated).value(
            "LAUNCH_RULE_DOCUMENT"
        )


@pytest.mark.parametrize(
    "anchor_mutation",
    (
        "protocol_zero",
        "protocol_nonliteral",
        "protocol_launch_rule_mismatch",
        "coordinated_launch_rule_resign",
        "authorization_slot_mismatch",
        "authorization_nonliteral",
        "context_protocol_sha_mismatch",
    ),
)
def test_c_pre_final_anchor_mutations_fail_before_output_root_creation(
    tmp_path: Path,
    anchor_mutation: str,
) -> None:
    repository, external_path, digest, _c_pre, _external = _build_repository(
        tmp_path,
        anchor_mutation=anchor_mutation,
    )
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert not (repository / materializer.OUTPUT_ROOT_RELATIVE_PATH).exists()
    failure_path = repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH
    assert failure_path.exists()
    failure_raw = failure_path.read_bytes()
    failure = json.loads(failure_raw)
    assert _canonical(failure) == failure_raw
    assert failure["failed_phase"] == "C_PRE_SOURCE_CLOSURE"


@pytest.mark.parametrize(
    "wrapper_mutation",
    materializer.WRAPPER_REDACTED_CONSTANT_NAMES,
)
def test_resigned_wrapper_authority_mutations_fail_before_output_root_creation(
    tmp_path: Path,
    wrapper_mutation: str,
) -> None:
    repository, external_path, digest, _c_pre, _external = _build_repository(
        tmp_path,
        wrapper_mutation=wrapper_mutation,
    )
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert not (repository / materializer.OUTPUT_ROOT_RELATIVE_PATH).exists()
    failure_path = repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH
    assert failure_path.exists()
    failure_raw = failure_path.read_bytes()
    failure = json.loads(failure_raw)
    assert _canonical(failure) == failure_raw
    assert failure["failed_phase"] == "C_PRE_SOURCE_CLOSURE"


def test_success_materializes_exact_bootstrap_manifest_and_terminal_last(
    tmp_path: Path,
) -> None:
    repository, external_path, digest, c_pre, external = _build_repository(tmp_path)
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode == 0, completed.stderr
    output = repository / materializer.OUTPUT_ROOT_RELATIVE_PATH
    bootstrap = repository / materializer.BOOTSTRAP_RELATIVE_PATH
    launcher = repository / materializer.RETAINED_LAUNCHER_RELATIVE_PATH
    manifest_path = repository / materializer.LAUNCH_MANIFEST_RELATIVE_PATH
    terminal_path = repository / materializer.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    failure = repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o400
        for path in (bootstrap, launcher, manifest_path, terminal_path)
    )
    assert not failure.exists()
    assert bootstrap.read_bytes() == _git(
        repository,
        "cat-file",
        "blob",
        external["bootstrap_git_blob"]["git_blob_id"],
    )
    assert launcher.read_bytes() == _git(
        repository,
        "cat-file",
        "blob",
        external["launcher_git_blob"]["git_blob_id"],
    )

    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    assert _canonical(manifest) == manifest_raw
    assert manifest["schema"] == materializer.LAUNCH_MANIFEST_SCHEMA
    assert manifest["c_pre_commit_id"] == c_pre
    assert manifest["c_pre_root"] == str(output)
    assert manifest["manifest_relative_path"] == "launch_manifest.json"
    assert manifest["bootstrap"]["relative_path"] == "bootstrap.py"
    assert set(manifest["targets"]) == {
        "measurement",
        "verification",
        "supervisor",
        "worker",
    }
    assert manifest["internal_target_contract"] == (
        materializer.INTERNAL_TARGET_CONTRACT
    )
    assert manifest["internal_target_contract"][
        "sock_seqpacket_buffer_request_bytes"
    ] == 1_048_576
    assert manifest["internal_target_contract"][
        "sock_seqpacket_effective_min_bytes"
    ] == 2_097_152
    module_contract = manifest["internal_target_contract"][
        "precompiled_runner_module_contract"
    ]
    assert module_contract["target_order"] == [
        "measurement",
        "verification",
        "supervisor",
        "worker",
    ]
    assert [row["module_name"] for row in module_contract["target_rows"]] == [
        f"_acfqp_v180r12r4_precompiled_runner_{target}"
        for target in module_contract["target_order"]
    ]
    assert module_contract["registered_before_runner_exec"] is True
    assert module_contract["preexisting_registration_is_preserved"] is True
    assert module_contract[
        "registration_removed_after_postchecks_on_success_or_failure"
    ] is True
    mutated_internal_contract = dict(manifest["internal_target_contract"])
    mutated_internal_contract["sock_seqpacket_effective_min_bytes"] -= 1
    assert mutated_internal_contract != materializer.INTERNAL_TARGET_CONTRACT
    assert manifest["git"]["runner_process_count"] == 6
    assert manifest["git"]["runner_environment_template"][
        materializer.MANIFEST_SHA256_ENV
    ] == materializer.MANIFEST_SHA256_TEMPLATE
    wrapper_source = next(
        row
        for row in manifest["source_modules"]
        if row["module"] == materializer.AUTHORIZATION_EVIDENCE_MODULE
    )
    current_wrapper = (
        repository / materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH
    ).read_bytes()
    assert wrapper_source == {
        "module": materializer.AUTHORIZATION_EVIDENCE_MODULE,
        "is_package": False,
        **materializer._raw_fact(
            materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
            current_wrapper,
        ),
    }
    normalized = next(
        row
        for row in manifest["authorization_source_closure"]["facts"]
        if row["relative_path"] == materializer.AUTHORIZATION_EVIDENCE_RELATIVE_PATH
    )
    assert normalized["binding_kind"] == materializer.NORMALIZED_WRAPPER_BINDING_KIND
    assert normalized["redacted_constant_names"] == list(
        materializer.WRAPPER_REDACTED_CONSTANT_NAMES
    )
    assert normalized["sha256"] != wrapper_source["sha256"]

    bootstrap_spec = importlib.util.spec_from_file_location(
        "synthetic_retained_bootstrap", bootstrap
    )
    assert bootstrap_spec is not None and bootstrap_spec.loader is not None
    bootstrap_module = importlib.util.module_from_spec(bootstrap_spec)
    bootstrap_spec.loader.exec_module(bootstrap_module)
    validated_manifest = bootstrap_module._validated_manifest(
        manifest, repository, output, "launch_manifest.json"
    )
    third_party_facts, wrapper_fact = (
        bootstrap_module._validate_manifest_resource_contract(
            validated_manifest, repository
        )
    )
    bound_records = bootstrap_module._compile_bound_sources(
        validated_manifest, repository, wrapper_fact
    )
    third_party_records = bootstrap_module._compile_third_party_sources(
        third_party_facts
    )
    assert materializer.AUTHORIZATION_SELF_MODULE in bound_records
    assert materializer.AUTHORIZATION_EVIDENCE_MODULE in bound_records
    assert {"packaging", "tomli"} <= set(third_party_records)

    terminal_raw = terminal_path.read_bytes()
    terminal = json.loads(terminal_raw)
    assert _canonical(terminal) == terminal_raw
    assert terminal["schema"] == materializer.MATERIALIZATION_TERMINAL_SCHEMA
    assert terminal["launch_manifest"] == materializer._raw_fact(
        materializer.LAUNCH_MANIFEST_RELATIVE_PATH, manifest_raw
    )
    assert (
        terminal["external_root_created_before_authorized_measurement_execution"]
        is True
    )
    assert terminal["external_root_required_before_authorization_issuance"] is False
    assert terminal["materialization_terminal_written_last"] is True
    assert terminal["campaign_actual_measurement"] is False
    assert terminal["scientific_occurrence_executed"] is False
    assert terminal["v180r12r4_outcome_bytes_accessed"] is False
    stdout = json.loads(completed.stdout)
    assert stdout["materialization_terminal_id"] == terminal[
        "materialization_terminal_id"
    ]


def test_exact_completed_materialization_cannot_be_rerun(tmp_path: Path) -> None:
    repository, external_path, digest, _, _ = _build_repository(tmp_path)
    first = _invoke(repository, external_path, digest)
    assert first.returncode == 0, first.stderr
    terminal = (
        repository / materializer.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    ).read_bytes()
    second = _invoke(repository, external_path, digest)
    assert second.returncode != 0
    assert "terminal already exists; rerun forbidden" in second.stderr
    assert (
        repository / materializer.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    ).read_bytes() == terminal
    assert not (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).exists()


def test_wrong_external_digest_freezes_typed_failure_without_output(
    tmp_path: Path,
) -> None:
    repository, external_path, _, _, _ = _build_repository(tmp_path)
    completed = _invoke(repository, external_path, "0" * 64)
    assert completed.returncode != 0
    assert not (repository / materializer.OUTPUT_ROOT_RELATIVE_PATH).exists()
    failure_path = repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH
    failure_raw = failure_path.read_bytes()
    failure = json.loads(failure_raw)
    assert _canonical(failure) == failure_raw
    assert failure["schema"] == materializer.MATERIALIZATION_FAILURE_SCHEMA
    assert failure["failed_phase"] == "EXTERNAL_ROOT_VALIDATION"
    assert failure["same_materialization_identity_rerun_forbidden"] is True
    assert failure["campaign_actual_measurement"] is False
    assert stat.S_IMODE(failure_path.stat().st_mode) == 0o400
    again = _invoke(repository, external_path, "0" * 64)
    assert again.returncode != 0
    assert "failure already exists; rerun forbidden" in again.stderr
    assert failure_path.read_bytes() == failure_raw


def test_external_root_c_pre_is_not_substituted_from_head(tmp_path: Path) -> None:
    repository, external_path, _, _, external = _build_repository(tmp_path)
    head = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    head_tree = _git(repository, "rev-parse", "HEAD^{tree}").decode("ascii").strip()
    external["c_pre_commit_id"] = head
    external["c_pre_tree_id"] = head_tree
    external["bootstrap_git_blob"] = _raw_git_fact(
        repository, head, materializer.SOURCE_BOOTSTRAP_RELATIVE_PATH
    )
    external["materializer_git_blob"] = _raw_git_fact(
        repository, head, materializer.MATERIALIZER_RELATIVE_PATH
    )
    external["launcher_git_blob"] = _raw_git_fact(
        repository, head, materializer.SOURCE_LAUNCHER_RELATIVE_PATH
    )
    external_path, digest = _write_external_root(repository, external)
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "exactly C_pre -> bridge -> literal HEAD" in completed.stderr
    failure = json.loads(
        (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["failed_phase"] == "GIT_TOPOLOGY_VALIDATION"


def test_later_commit_after_literal_head_is_rejected(tmp_path: Path) -> None:
    repository, external_path, digest, _, _ = _build_repository(
        tmp_path, later_commit=True
    )
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "exactly C_pre -> bridge -> literal HEAD" in completed.stderr
    assert not (repository / materializer.OUTPUT_ROOT_RELATIVE_PATH).exists()


def test_wrapper_change_outside_twelve_literals_is_rejected(tmp_path: Path) -> None:
    repository, external_path, digest, _, _ = _build_repository(
        tmp_path, wrapper_suffix="EXTRA_WRAPPER_LOGIC = True\n"
    )
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "outside the twelve literals" in completed.stderr
    failure = json.loads(
        (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["failed_phase"] == "C_PRE_SOURCE_CLOSURE"


def test_symlinked_external_root_is_rejected_and_preserved(tmp_path: Path) -> None:
    repository, external_path, digest, _, external = _build_repository(tmp_path)
    external_path.chmod(0o600)
    external_path.unlink()
    target = tmp_path / "external-target.json"
    target.write_bytes(_canonical(external))
    target.chmod(0o400)
    external_path.symlink_to(target)
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "unavailable or symlinked" in completed.stderr
    assert external_path.is_symlink()
    assert (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).exists()


def test_preexisting_partial_output_is_frozen_without_mutation(tmp_path: Path) -> None:
    repository, external_path, digest, _, _ = _build_repository(tmp_path)
    output = repository / materializer.OUTPUT_ROOT_RELATIVE_PATH
    output.mkdir(mode=0o700)
    partial = output / "bootstrap.py"
    partial.write_bytes(b"partial")
    partial.chmod(0o400)
    completed = _invoke(repository, external_path, digest)
    assert completed.returncode != 0
    assert "partial output exists; rerun forbidden" in completed.stderr
    assert partial.read_bytes() == b"partial"
    failure = json.loads(
        (repository / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).read_bytes()
    )
    assert failure["failed_phase"] == "PREEXISTING_PROGRESS_CHECK"
    assert failure["partial_artifact_observations"]["bootstrap"]["sha256"] == hashlib.sha256(
        b"partial"
    ).hexdigest()


def test_materializer_is_stdlib_only_and_never_executes_campaign_code() -> None:
    source = SOURCE_MATERIALIZER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.add((node.module or "").split(".", 1)[0])
    assert imported == {
        "ast",
        "hashlib",
        "io",
        "json",
        "os",
        "pathlib",
        "re",
        "stat",
        "subprocess",
        "sys",
        "sysconfig",
        "tarfile",
        "tokenize",
        "typing",
    }
    assert "from acfqp" not in source
    assert "CounterRecord" not in source
    assert "WorkVector" not in source
    assert "ComparisonVector" not in source
    assert "os.O_EXCL" in source
    assert "os.O_NOFOLLOW" in source
    assert "os.O_CLOEXEC" in source
    assert "os.fsync" in source
    assert not (ROOT / materializer.OUTPUT_ROOT_RELATIVE_PATH).exists()
    assert not (ROOT / materializer.MATERIALIZATION_FAILURE_RELATIVE_PATH).exists()
