from __future__ import annotations

import ast
import fcntl
from functools import lru_cache
import hashlib
import importlib.util
import json
import marshal
import os
from pathlib import Path
import py_compile
import shutil
import socket
import stat
import subprocess
import tempfile
import time

import pytest

from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts/bootstrap_v180r12r4_campaign_measurement.py"
PYTHON = "/usr/bin/python3"
PYCACHE_PREFIX = "/dev/null/v180r12r4"
MANIFEST_SHA_ENV = "ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256"
SCHEMA = "acfqp.v180r12r4_source_bound_launch_manifest.v1"
AUTHORIZATION_SELF_MODULE = (
    "acfqp."
    "construction_k7_campaign_measurement_execution_authorization_v180r12r4"
)
AUTHORIZATION_EVIDENCE_MODULE = (
    "acfqp.construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r4"
)
AUTHORIZATION_EVIDENCE_RELATIVE = (
    "src/acfqp/construction_k7_campaign_measurement_"
    "authorization_evidence_freeze_v180r12r4.py"
)
WRAPPER_REDACTED_CONSTANTS = (
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "EXPECTED_SOURCE_CLOSURE_BYTE_COUNT",
    "EXPECTED_SOURCE_CLOSURE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_FILE_COUNT",
)
WRAPPER_STRING_CONSTANTS = {
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "EXPECTED_SOURCE_CLOSURE_SHA256",
}
ISOLATED_FLAGS = (
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={PYCACHE_PREFIX}",
)
RUNNER_PATHS = {
    "measurement": "scripts/run_v180r12r4_campaign_measurement.py",
    "verification": "scripts/verify_v180r12r4_campaign_measurement.py",
    "supervisor": "scripts/supervise_v180r12r4_campaign_measurement.py",
    "worker": "scripts/work_v180r12r4_campaign_measurement.py",
}
RUNNER_MODULE_NAMES = {
    target: f"_acfqp_v180r12r4_precompiled_runner_{target}"
    for target in RUNNER_PATHS
}
SOURCE_CLOSURE_REQUIRED_ROOTS = tuple(
    sorted(
        (
            "scripts/bootstrap_v180r12r4_campaign_measurement.py",
            "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py",
            "scripts/materialize_v180r12r4_campaign_measurement_prelaunch.py",
            RUNNER_PATHS["measurement"],
            "scripts/supervise_v180r12r4_campaign_measurement.py",
            RUNNER_PATHS["verification"],
            "scripts/work_v180r12r4_campaign_measurement.py",
            "src/acfqp/construction_accounting_registry_v6.py",
            "src/acfqp/construction_k7_domain_registry_extension_v180r12r4.py",
            "src/acfqp/construction_k7_domain_registry_extension_v180r12r4e.py",
            "src/acfqp/construction_k7_campaign_measurement_ledger_v180r12r4.py",
            "src/acfqp/construction_k7_campaign_measurement_protocol_v180r12r4.py",
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "execution_authorization_v180r12r4.py"
            ),
            AUTHORIZATION_EVIDENCE_RELATIVE,
            "src/acfqp/construction_k7_campaign_measurement_supervisor_v180r12r4.py",
            "src/acfqp/construction_k7_campaign_measurement_worker_v180r12r4.py",
            "src/acfqp/construction_k7_campaign_measurement_finalizer_v180r12r4.py",
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "prelaunch_failure_freeze_v180r12r3.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "prelaunch_failure_freeze_v180r12r3r1.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "failure_freeze_v180r12r3r2.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "failure_freeze_v180r12r4r2.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "failure_freeze_v180r12r4r4.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "failure_freeze_v180r12r4r5.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "failure_freeze_v180r12r4r6.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "failure_freeze_v180r12r4r7.py"
            ),
            (
                "src/acfqp/construction_k7_campaign_measurement_"
                "independent_verifier_v180r12r4.py"
            ),
            (
                "src/acfqp/construction_k7_ten_terminal_aggregation_"
                "production_evidence_freeze_v180r12r2.py"
            ),
        )
    )
)
GIT = "/usr/bin/git"
COMMIT_ENV = "ACFQP_V180R12R4_PREREG_COMMIT"
MANIFEST_SHA_TEMPLATE = "__V180R12R4_MANIFEST_SHA256__"


@lru_cache(maxsize=1)
def _bootstrap_module():
    spec = importlib.util.spec_from_file_location("v180r12r4_bootstrap_test", BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _first_real_top_level_dataclass_source(target: str) -> tuple[str, str]:
    source_path = ROOT / RUNNER_PATHS[target]
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    lines = source.splitlines(keepends=True)
    for statement in tree.body:
        if not isinstance(statement, ast.ClassDef):
            continue
        decorators = [
            decorator.func if isinstance(decorator, ast.Call) else decorator
            for decorator in statement.decorator_list
        ]
        if not any(
            isinstance(decorator, ast.Name) and decorator.id == "dataclass"
            for decorator in decorators
        ):
            continue
        start_line = min(
            [statement.lineno]
            + [decorator.lineno for decorator in statement.decorator_list]
        )
        return statement.name, "".join(
            lines[start_line - 1 : statement.end_lineno]
        )
    raise AssertionError(f"no top-level dataclass found in {source_path}")


def _runner_module_lifecycle_probe(
    *,
    target: str,
    mode: str,
    real_dataclass_source: str | None = None,
    real_dataclass_name: str | None = None,
) -> dict[str, object]:
    if real_dataclass_source is None:
        class_source = (
            "@dataclass(frozen=True, slots=True)\n"
            "class RunnerDataclassProbe:\n"
            "    value: str\n"
        )
        class_name = "RunnerDataclassProbe"
    else:
        assert type(real_dataclass_name) is str and real_dataclass_name
        class_source = real_dataclass_source
        class_name = real_dataclass_name
    runner_source = (
        "from __future__ import annotations\n"
        "from dataclasses import dataclass, field\n"
        + class_source
        + "\nclass PrimaryRunnerError(RuntimeError):\n"
        "    pass\n"
        "\ndef bootstrap_entrypoint_v180r12r4(context):\n"
        "    import sys, types\n"
        "    registered = sys.modules.get(__name__)\n"
        "    if registered is None or registered.__dict__ is not globals():\n"
        "        raise RuntimeError('ENTRYPOINT_MODULE_REGISTRATION_MISSING')\n"
        f"    if context['target'] != {target!r}:\n"
        "        raise RuntimeError('ENTRYPOINT_TARGET_CHANGED')\n"
        f"    dataclass_type = globals()[{class_name!r}]\n"
        "    if dataclass_type.__module__ != __name__:\n"
        "        raise RuntimeError('DATACLASS_MODULE_CHANGED')\n"
        "    if not hasattr(dataclass_type, '__dataclass_fields__'):\n"
        "        raise RuntimeError('DATACLASS_DECORATION_MISSING')\n"
        + (
            "    del sys.modules[__name__]\n"
            if mode == "deleted"
            else "    sys.modules[__name__] = types.ModuleType(__name__)\n"
            if mode in {"replaced", "primary_secondary"}
            else "    globals()['__file__'] = 'foreign-runner.py'\n"
            if mode == "metadata_drift"
            else (
                "    class EqualitySpoof:\n"
                "        def __eq__(self, other):\n"
                "            del other\n"
                "            return True\n"
                "    globals()['__loader__'] = EqualitySpoof()\n"
            )
            if mode == "metadata_equality_spoof"
            else ""
        )
        + (
            "    raise PrimaryRunnerError('PRIMARY_RUNNER_FAILURE')\n"
            if mode in {"primary", "primary_secondary"}
            else "    return None\n"
        )
    )
    program = f"""
import importlib.util
import inspect
import json
import sys
import types

spec = importlib.util.spec_from_file_location(
    "v180r12r4_bootstrap_lifecycle_probe", {str(BOOTSTRAP)!r}
)
bootstrap = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bootstrap
spec.loader.exec_module(bootstrap)

class Audit:
    def __call__(self, event, arguments):
        del event, arguments

    def require_complete(self):
        return None

target = {target!r}
mode = {mode!r}
module_name = bootstrap._RUNNER_MODULE_NAMES[target]
original_registry = sys.modules
preexisting = None
if mode == "collision":
    preexisting = types.ModuleType(module_name)
    sys.modules[module_name] = preexisting
trace_state = {{"injected": False}}
trace_needles = {{
    "interrupt_after_registration": "runner_namespace = runner_module.__dict__",
    "interrupt_secondary": "secondary = (",
}}
if mode in trace_needles:
    function_lines, function_start = inspect.getsourcelines(
        bootstrap._execute_precompiled_runner
    )
    matching_lines = [
        function_start + offset
        for offset, line in enumerate(function_lines)
        if line.strip() == trace_needles[mode]
    ]
    if len(matching_lines) != 1:
        raise RuntimeError("ASYNC_INJECTION_LINE_CHANGED")
    injection_line = matching_lines[0]

    def inject_once(frame, event, argument):
        del argument
        if (
            event == "line"
            and frame.f_code is bootstrap._execute_precompiled_runner.__code__
            and frame.f_lineno == injection_line
            and not trace_state["injected"]
        ):
            trace_state["injected"] = True
            sys.settrace(None)
            raise KeyboardInterrupt("INJECTED_RUNNER_LIFECYCLE_INTERRUPT")
        return inject_once

    sys.settrace(inject_once)
result = {{}}
try:
    bootstrap._execute_precompiled_runner(
        compile({runner_source!r}, {str(ROOT / RUNNER_PATHS[target])!r}, "exec"),
        {str(ROOT / RUNNER_PATHS[target])!r},
        {{}},
        Audit(),
        verified_internal_context=types.MappingProxyType({{"target": target}}),
    )
except BaseException as error:
    cause = BaseException.__getattribute__(error, "__cause__")
    result.update({{
        "error_type": type(error).__name__,
        "error_message": str(error),
        "cause_type": None if cause is None else type(cause).__name__,
        "cause_message": None if cause is None else str(cause),
    }})
else:
    result.update({{
        "error_type": None,
        "error_message": None,
        "cause_type": None,
        "cause_message": None,
    }})
finally:
    sys.settrace(None)
result.update({{
    "module_name": module_name,
    "registry_is_original": sys.modules is original_registry,
    "slot_present": module_name in sys.modules,
    "slot_is_preexisting": (
        preexisting is not None and sys.modules.get(module_name) is preexisting
    ),
}})
if mode in trace_needles:
    result["trace_injected"] = trace_state["injected"]
print(json.dumps(result, sort_keys=True))
"""
    completed = subprocess.run(
        [PYTHON, *ISOLATED_FLAGS, "-c", program],
        cwd=ROOT,
        env={},
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _file_fact(root: Path, relative: str) -> dict[str, object]:
    raw = (root / relative).read_bytes()
    return {
        "relative_path": relative,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _normalize_wrapper(raw: bytes) -> bytes:
    tree = ast.parse(raw)
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    replacements = []
    for statement in tree.body:
        if not (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id in WRAPPER_REDACTED_CONSTANTS
        ):
            continue
        name = statement.targets[0].id
        value = statement.value
        start = offsets[value.lineno - 1] + value.col_offset
        end = offsets[value.end_lineno - 1] + value.end_col_offset
        replacement = (
            b'"0000000000000000000000000000000000000000000000000000000000000000"'
            if name in WRAPPER_STRING_CONSTANTS
            else b"0"
        )
        replacements.append((start, end, replacement))
    assert len(replacements) == 12
    result = raw
    for start, end, replacement in sorted(replacements, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result


def _normalized_wrapper_fact(root: Path, relative: str) -> dict[str, object]:
    normalized = _normalize_wrapper((root / relative).read_bytes())
    return {
        "relative_path": relative,
        "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
        "byte_count": len(normalized),
        "sha256": hashlib.sha256(normalized).hexdigest(),
        "redacted_constant_names": list(WRAPPER_REDACTED_CONSTANTS),
    }


def _closure(facts: list[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(facts, key=lambda row: row["relative_path"])
    return {
        "facts": ordered,
        "file_count": len(ordered),
        "total_byte_count": sum(int(row["byte_count"]) for row in ordered),
        "facts_sha256": hashlib.sha256(_canonical_bytes(ordered)).hexdigest(),
    }


def _third_party_closure(facts: list[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(facts, key=lambda row: row["module"])
    return {
        "facts": ordered,
        "file_count": len(ordered),
        "total_byte_count": sum(int(row["byte_count"]) for row in ordered),
        "facts_sha256": hashlib.sha256(_canonical_bytes(ordered)).hexdigest(),
    }


@lru_cache(maxsize=1)
def _runtime_fact() -> dict[str, object]:
    probe = subprocess.run(
        [
            PYTHON,
            *ISOLATED_FLAGS,
            "-c",
            (
                "import json,os,sys,sysconfig;"
                "p=os.path.realpath(sys.executable);"
                "print(json.dumps({"
                "'resolved_executable':p,"
                "'version':sys.version,"
                "'version_info':list(sys.version_info),"
                "'soabi':sysconfig.get_config_var('SOABI'),"
                "'base_sys_path':sys.path"
                "},sort_keys=True))"
            ),
        ],
        env={},
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(probe.stdout)
    executable_raw = Path(result["resolved_executable"]).read_bytes()
    return {
        "requested_executable": PYTHON,
        "resolved_executable": result["resolved_executable"],
        "executable_byte_count": len(executable_raw),
        "executable_sha256": hashlib.sha256(executable_raw).hexdigest(),
        "version": result["version"],
        "version_info": result["version_info"],
        "soabi": result["soabi"],
        "base_sys_path": result["base_sys_path"],
        "orig_argv_prefix": [PYTHON, *ISOLATED_FLAGS],
        "pycache_prefix": PYCACHE_PREFIX,
        "flags": {
            "isolated": 1,
            "no_site": 1,
            "no_user_site": 1,
            "ignore_environment": 1,
            "dont_write_bytecode": 1,
        },
    }


def _git_identity(repository: Path) -> tuple[str, list[list[str]]]:
    (repository / "README").write_text("bound launch\n", encoding="utf-8")
    subprocess.run([GIT, "-C", str(repository), "init", "-q"], check=True)
    subprocess.run([GIT, "-C", str(repository), "add", "README"], check=True)
    subprocess.run(
        [
            GIT,
            "-C",
            str(repository),
            "-c",
            "user.name=V180r12r4 Test",
            "-c",
            "user.email=v180r12r4@example.invalid",
            "commit",
            "-q",
            "-m",
            "bound launch",
        ],
        env={
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
        },
        check=True,
    )
    commit_id = subprocess.run(
        [GIT, "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    prefix = [GIT, "-C", str(repository)]
    return commit_id, [
        [*prefix, "rev-parse", "--show-toplevel"],
        [*prefix, "log", "-1", "--format=%H"],
        [*prefix, "diff-tree", "--no-commit-id", "--raw", "-r", "HEAD"],
        [*prefix, "log", "-1", "--format=%H"],
        [*prefix, "archive", "--format=tar", "HEAD", "--", "README"],
        [*prefix, "cat-file", "-t", "HEAD"],
    ]


def _runner_prefix(commit_id: str, git_argv: list[list[str]]) -> str:
    return (
        "import os\n"
        "import subprocess\n"
        f"if os.environ[{COMMIT_ENV!r}] != {commit_id!r}:\n"
        "    raise RuntimeError('pre-main commit injection changed')\n"
        "git_environment = {\n"
        "    key: value for key, value in os.environ.items()\n"
        "    if not key.startswith('GIT_')\n"
        "}\n"
        "git_environment.update({\n"
        "    'GIT_CONFIG_GLOBAL': os.devnull,\n"
        "    'GIT_CONFIG_NOSYSTEM': '1',\n"
        "    'GIT_NO_REPLACE_OBJECTS': '1',\n"
        "    'GIT_OPTIONAL_LOCKS': '0',\n"
        "    'LC_ALL': 'C',\n"
        "})\n"
        f"for git_argv in {git_argv!r}:\n"
        "    completed = subprocess.run(\n"
        "        git_argv, check=False, stdout=subprocess.PIPE,\n"
        "        stderr=subprocess.PIPE, env=git_environment,\n"
        "    )\n"
        "    if completed.returncode != 0:\n"
        "        raise RuntimeError('synthetic Git contract failed')\n"
    )


def _git_manifest_fact(
    repository: Path,
    commit_id: str,
    git_argv: list[list[str]],
) -> dict[str, object]:
    del repository
    git_path = Path(GIT).resolve(strict=True)
    git_raw = git_path.read_bytes()
    git_version = subprocess.run(
        [GIT, "--version"],
        env={
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "LC_ALL": "C",
        },
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    return {
        "requested_executable": GIT,
        "resolved_executable": str(git_path),
        "executable_mode": git_path.stat().st_mode,
        "executable_byte_count": len(git_raw),
        "executable_sha256": hashlib.sha256(git_raw).hexdigest(),
        "version_argv": [GIT, "--version"],
        "version_environment": {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "LC_ALL": "C",
        },
        "version_stdout": git_version,
        "runner_process_count": 6,
        "runner_argv": git_argv,
        "runner_environment_template": {
            MANIFEST_SHA_ENV: MANIFEST_SHA_TEMPLATE,
            COMMIT_ENV: commit_id,
            "LC_CTYPE": "C.UTF-8",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        },
    }


def _default_runner_body() -> str:
    return (
        "import json\n"
        "from acfqp import bound\n"
        f"from acfqp import {AUTHORIZATION_SELF_MODULE.split('.', 1)[1]} as authorization\n"
        "print(json.dumps({\n"
        "    'authorization': authorization.BOUND_AUTHORIZATION,\n"
        "    'cached': bound.__cached__,\n"
        "    'file': bound.__file__,\n"
        "    'loader': type(bound.__loader__).__name__,\n"
        "    'value': bound.VALUE,\n"
        "    'packaging': bound.PACKAGING_VALUE,\n"
        "    'tomli': bound.TOMLI_VALUE,\n"
        f"    'commit': __import__('os').environ[{COMMIT_ENV!r}],\n"
        "    'sys_path': __import__('sys').path,\n"
        "}, sort_keys=True), flush=True)\n"
    )


def _complete_required_static_roots(repository: Path) -> None:
    for relative in SOURCE_CLOSURE_REQUIRED_ROOTS:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            continue
        if relative == "scripts/bootstrap_v180r12r4_campaign_measurement.py":
            shutil.copyfile(BOOTSTRAP, path)
        else:
            path.write_text("# bound static root\n", encoding="utf-8")


def _static_root_facts(repository: Path) -> list[dict[str, object]]:
    facts = []
    for relative in SOURCE_CLOSURE_REQUIRED_ROOTS:
        if relative == AUTHORIZATION_EVIDENCE_RELATIVE:
            facts.append(_normalized_wrapper_fact(repository, relative))
        else:
            facts.append(_file_fact(repository, relative))
    return facts


def _working_tree_source_conformance(
    repository: Path, closure: dict[str, object]
) -> dict[str, object]:
    facts = closure["facts"]
    assert isinstance(facts, list) and facts
    snapshots = []
    for fact in facts:
        assert isinstance(fact, dict)
        relative = str(fact["relative_path"])
        path = repository / relative
        raw = path.read_bytes()
        effective_raw = (
            _normalize_wrapper(raw)
            if relative == AUTHORIZATION_EVIDENCE_RELATIVE
            else raw
        )
        binding_kind = str(
            fact.get("binding_kind", "EXACT_C_PRE_GIT_BLOB")
        )
        assert len(effective_raw) == fact["byte_count"]
        assert hashlib.sha256(effective_raw).hexdigest() == fact["sha256"]
        metadata = path.stat()
        assert stat.S_ISREG(metadata.st_mode)
        assert stat.S_IMODE(metadata.st_mode) == 0o644
        assert metadata.st_nlink == 1
        observed_stat = {
            "file_type": "REGULAR_FILE",
            "st_dev": metadata.st_dev,
            "st_ino": metadata.st_ino,
            "st_mode": metadata.st_mode,
            "mode": stat.S_IMODE(metadata.st_mode),
            "st_nlink": metadata.st_nlink,
            "st_uid": metadata.st_uid,
            "st_gid": metadata.st_gid,
            "st_size": metadata.st_size,
            "st_mtime_ns": metadata.st_mtime_ns,
            "st_ctime_ns": metadata.st_ctime_ns,
        }
        effective_blob = hashlib.sha1(
            b"blob "
            + str(len(effective_raw)).encode("ascii")
            + b"\x00"
            + effective_raw
        ).hexdigest()
        physical_blob = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
        ).hexdigest()
        snapshots.append(
            {
                "relative_path": relative,
                "expected": {
                    "file_type": "REGULAR_FILE",
                    "git_mode": "100644",
                    "mode": 0o644,
                    "st_nlink": 1,
                    "binding_kind": binding_kind,
                    "byte_count": len(effective_raw),
                    "sha256": hashlib.sha256(effective_raw).hexdigest(),
                    "git_blob_id": effective_blob,
                },
                "observed_before": observed_stat,
                "observed_after": dict(observed_stat),
                "observed_content": {
                    "binding_kind": binding_kind,
                    "byte_count": len(effective_raw),
                    "sha256": hashlib.sha256(effective_raw).hexdigest(),
                    "git_blob_id": effective_blob,
                    "physical_byte_count": len(raw),
                    "physical_sha256": hashlib.sha256(raw).hexdigest(),
                    "physical_git_blob_id": physical_blob,
                },
                "mismatch_fields": [],
                "conformant": True,
            }
        )
    return {
        "schema": (
            "acfqp.v180r12r4_working_tree_source_conformance_diagnostic.v1"
        ),
        "phase": "BEFORE_PRELAUNCH_OUTPUT_AND_SCIENTIFIC_CAMPAIGN",
        "source_root_count": len(snapshots),
        "snapshots": snapshots,
        "mismatch_count": 0,
        "per_field_mismatches": [],
        "unit_ownership_evaluated": False,
        "full_source_conformance": True,
        "cause": None,
    }


def _frozen_authorization_context(
    repository: Path, *, local_capture: bool = False
) -> dict[str, object]:
    mount = repository / "fake-cgroup2"
    parent = mount / "app.slice"
    parent.mkdir(parents=True, exist_ok=True)
    mount_stat = os.stat(mount)
    parent_stat = os.stat(parent)
    six = {
        "protocol_id": "1" * 64,
        "authorization_id": "2" * 64,
        "authorization_evidence_id": "3" * 64,
        "campaign_measurement_execution_slot_id": "4" * 64,
        "logical_occurrence_id": "5" * 64,
        "execution_nonce": "6" * 64,
    }
    attempt_payload = {
        "schema": "acfqp.campaign_measurement_attempt.v180r12r4",
        **six,
    }
    attempt_id = hashlib.sha256(
        b"acfqp:construction-k7-campaign-measurement-attempt:v180r12r4\x00"
        + _canonical_bytes(attempt_payload)
    ).hexdigest()
    context = {
        "schema": "acfqp.v180r12r4_frozen_authorization_context.v1",
        "protocol_id": six["protocol_id"],
        "protocol_byte_count": 101,
        "protocol_sha256": "7" * 64,
        "authorization_id": six["authorization_id"],
        "authorization_byte_count": 102,
        "authorization_sha256": "8" * 64,
        "authorization_evidence_id": six["authorization_evidence_id"],
        "authorization_evidence_byte_count": 103,
        "authorization_evidence_sha256": "9" * 64,
        "campaign_measurement_execution_slot_id": six[
            "campaign_measurement_execution_slot_id"
        ],
        "logical_occurrence_id": six["logical_occurrence_id"],
        "execution_nonce": six["execution_nonce"],
        "campaign_attempt_id": attempt_id,
        "cgroup_parent_fact": {
            "schema": "acfqp.v180r12r4_cgroup_parent_fact.v1",
            "mount_point": str(mount), "mount_fstype": "cgroup2",
            "mount_device": mount_stat.st_dev, "mount_inode": mount_stat.st_ino,
            "mount_options": ["rw"], "parent_path": str(parent),
            "parent_device": parent_stat.st_dev, "parent_inode": parent_stat.st_ino,
            "owner_uid": parent_stat.st_uid, "owner_gid": parent_stat.st_gid,
            "mode": stat.S_IMODE(parent_stat.st_mode),
            "controllers": ["cpu", "memory", "pids"],
            "subtree_control": ["cpu", "memory", "pids"], "cgroup_type": "domain",
            "cgroup_namespace_inode": 3, "cgroup_events_present": True,
            "memory_events_present": True, "pids_events_present": True,
            "cgroup_kill_present": True, "cgroup_procs_present": True,
            "memory_peak_present": True, "pids_peak_present": True,
            "self_membership": (
                "0::/app.slice/"
                "acfqp-v180r12r4r5-freeze-capture-20260829.service"
            ),
        },
        "runtime_capability_fact": {
            "schema": "acfqp.v180r12r4_runtime_capability_fact.v1",
            "machine_architecture": "x86_64", "single_threaded": True,
            "clone3_probe_errno": 22, "clone3_syscall_recognized": True,
            "pidfd_send_signal_probe_errno": 9,
            "pidfd_send_signal_recognized": True, "execveat_probe_errno": 9,
            "execveat_recognized": True, "pidfd_wait_present": True,
            "landlock_abi": 7, "uid": os.getuid(), "gid": os.getgid(),
            "effective_capability_mask": 0, "admitted": True,
        },
    }
    if not local_capture:
        context["cgroup_parent_fact"] = json.loads(
            json.dumps(protocol.SERVICE_CONTEXT_CAPTURE_CGROUP_PARENT_FACT)
        )
        context["runtime_capability_fact"] = json.loads(
            json.dumps(protocol.SERVICE_CONTEXT_CAPTURE_RUNTIME_CAPABILITY_FACT)
        )
    return context


def _bootstrap_source_for_local_capture(context: dict[str, object]) -> bytes:
    capture_raw = _canonical_bytes(
        {
            "capture_purpose": protocol.SERVICE_CONTEXT_CAPTURE_PURPOSE,
            "cgroup_parent_fact": context["cgroup_parent_fact"],
            "runtime_capability_fact": context["runtime_capability_fact"],
            "schema": protocol.SERVICE_CONTEXT_CAPTURE_SCHEMA,
        }
    ) + b"\n"
    source = BOOTSTRAP.read_text(encoding="utf-8")
    source = source.replace(
        "_SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT = 1_459",
        f"_SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT = {len(capture_raw)}",
    )
    source = source.replace(
        protocol.SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256,
        hashlib.sha256(capture_raw).hexdigest(),
    )
    return source.encode("utf-8")


def _external_entrypoint(source: str) -> str:
    return (
        "def bootstrap_entrypoint_v180r12r4(verified_context):\n"
        "    assert verified_context['context_consumed_once'] is True\n"
        + "".join("    " + line for line in source.splitlines(keepends=True))
    )


def _service_manifest_contract(repository: Path) -> tuple[dict, dict[str, list[str]]]:
    contract = protocol.production_systemd_service_contract_v180r12r4()
    templates = {
        row["target"]: [
            value.replace("{repository_root}", str(repository))
            for value in row["systemd_run_argv_template"]
        ]
        for row in contract["target_rows"]
    }
    return contract, templates


def _service_artifact_paths() -> dict[str, dict[str, str]]:
    return {
        "measurement": {
            "attempt": protocol.PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
            "receipt": protocol.PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
            "failure": protocol.PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH,
        },
        "verification": {
            "attempt": protocol.PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
            "receipt": protocol.PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
            "failure": protocol.PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH,
        },
    }


def _build_launch(
    tmp_path: Path,
    *,
    measurement_body: str | None = None,
    measurement_failure_mode: str | None = None,
) -> tuple[Path, Path, Path, dict[str, object], str]:
    repository = (tmp_path / "repository").absolute()
    c_pre = (tmp_path / "c_pre").absolute()
    (repository / "scripts").mkdir(parents=True)
    (repository / "src/acfqp").mkdir(parents=True)
    (c_pre / "scripts").mkdir(parents=True)
    frozen_authorization_context = _frozen_authorization_context(
        repository, local_capture=True
    )
    (c_pre / "scripts/bootstrap_v180r12r4_campaign_measurement.py").write_bytes(
        _bootstrap_source_for_local_capture(frozen_authorization_context)
    )
    (repository / "src/acfqp/__init__.py").write_text("", encoding="utf-8")
    (repository / "src/acfqp/bound.py").write_text(
        "from packaging.utils import canonicalize_name\n"
        "import tomli\n"
        "VALUE = 'IN_MEMORY_BOUND_SOURCE'\n"
        "PACKAGING_VALUE = canonicalize_name('Bound_Source')\n"
        "TOMLI_VALUE = tomli.loads('value = 7')['value']\n",
        encoding="utf-8",
    )
    authorization_relative = (
        "src/acfqp/"
        "construction_k7_campaign_measurement_execution_authorization_v180r12r4.py"
    )
    (repository / authorization_relative).write_text(
        "BOUND_AUTHORIZATION = True\n", encoding="utf-8"
    )
    wrapper_lines = []
    for name in WRAPPER_REDACTED_CONSTANTS:
        literal = "'f' * 64" if name in WRAPPER_STRING_CONSTANTS else "17"
        if name in WRAPPER_STRING_CONSTANTS:
            literal = repr("f" * 64)
        wrapper_lines.append(f"{name} = {literal}\n")
    (repository / AUTHORIZATION_EVIDENCE_RELATIVE).write_text(
        "".join(wrapper_lines), encoding="utf-8"
    )
    third_party_root = (tmp_path / "third_party").absolute()
    (third_party_root / "packaging").mkdir(parents=True)
    (third_party_root / "tomli").mkdir(parents=True)
    (third_party_root / "packaging/__init__.py").write_text("", encoding="utf-8")
    (third_party_root / "packaging/utils.py").write_text(
        "def canonicalize_name(value):\n"
        "    return value.replace('_', '-').lower()\n",
        encoding="utf-8",
    )
    (third_party_root / "tomli/__init__.py").write_text(
        "def loads(value):\n    return {'value': int(value.split('=')[1])}\n",
        encoding="utf-8",
    )
    commit_id, git_argv = _git_identity(repository)
    runner_prefix = _runner_prefix(commit_id, git_argv)
    if measurement_failure_mode == "partial_git":
        runner_source = _external_entrypoint(
            _runner_prefix(commit_id, git_argv[:1])
            + "raise RuntimeError('PRIMARY_PARTIAL_GIT_FAILURE')\n"
        )
    elif measurement_failure_mode == "pre_main_import":
        runner_source = "import acfqp.pre_main_missing\n"
    elif measurement_failure_mode == "no_primary_incomplete":
        runner_source = _external_entrypoint("PASSIVE_RETURN = True\n")
    elif measurement_failure_mode is None:
        runner_source = _external_entrypoint(
            runner_prefix + (measurement_body or _default_runner_body())
        )
    else:
        raise AssertionError("unknown measurement failure mode")
    for target, relative in RUNNER_PATHS.items():
        source = (
            runner_source
            if target == "measurement"
            else _external_entrypoint(runner_prefix + _default_runner_body())
        )
        (repository / relative).write_text(source, encoding="utf-8")
    _complete_required_static_roots(repository)

    module_bindings = [
        ("acfqp", "src/acfqp/__init__.py", True),
        ("acfqp.bound", "src/acfqp/bound.py", False),
        (AUTHORIZATION_EVIDENCE_MODULE, AUTHORIZATION_EVIDENCE_RELATIVE, False),
        (AUTHORIZATION_SELF_MODULE, authorization_relative, False),
    ]
    source_modules = []
    for module, relative, is_package in sorted(module_bindings):
        source_modules.append(
            {
                "module": module,
                "is_package": is_package,
                **_file_fact(repository, relative),
            }
        )
    third_party_bindings = [
        ("packaging", "packaging/__init__.py", True),
        ("packaging.utils", "packaging/utils.py", False),
        ("tomli", "tomli/__init__.py", True),
    ]
    third_party_facts = [
        {
            "module": module,
            "is_package": is_package,
            "source_root": str(third_party_root),
            **_file_fact(third_party_root, relative),
        }
        for module, relative, is_package in third_party_bindings
    ]
    target_facts = {
        target: _file_fact(repository, relative)
        for target, relative in RUNNER_PATHS.items()
    }
    authorization_raw_facts = _static_root_facts(repository)
    authorization_closure = _closure(authorization_raw_facts)
    source_conformance = _working_tree_source_conformance(
        repository, authorization_closure
    )
    service_contract, service_templates = _service_manifest_contract(repository)
    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "repository_root": str(repository),
        "c_pre_root": str(c_pre),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": commit_id,
        "bootstrap": _file_fact(
            c_pre, "scripts/bootstrap_v180r12r4_campaign_measurement.py"
        ),
        "runtime": _runtime_fact(),
        "git": _git_manifest_fact(repository, commit_id, git_argv),
        "authorization_source_closure_kind": (
            "EXACT_RAW_AUTHORIZATION_SOURCE_CLOSURE_PLUS_AUTH_SELF_AND_BOUND_RUNNERS"
        ),
        "authorization_self_module": AUTHORIZATION_SELF_MODULE,
        "authorization_raw_source_modules": sorted(
            module
            for module, _, _ in module_bindings
            if module != AUTHORIZATION_SELF_MODULE
        ),
        "authorization_source_closure": authorization_closure,
        "working_tree_source_conformance": source_conformance,
        "source_modules": source_modules,
        "third_party_source_closure": _third_party_closure(third_party_facts),
        "targets": target_facts,
        "internal_target_contract": _bootstrap_module()._INTERNAL_TARGET_CONTRACT,
        "production_systemd_service_contract": service_contract,
        "production_systemd_run_argv_templates": service_templates,
        "production_service_launch_artifact_paths": _service_artifact_paths(),
        "production_service_launch_modes": {
            "outer_dispatch": "dispatch",
            "retained_service_entry": "service-entry",
        },
        "atomic_cgroup_birth_preflight_receipt_interface": dict(
            protocol.ZERO_ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE
        ),
        "frozen_authorization_context": frozen_authorization_context,
        "working_tree_mutation_after_snapshot_in_scope": False,
    }
    manifest_path = c_pre / "launch_manifest.json"
    manifest_raw = _canonical_bytes(manifest)
    manifest_path.write_bytes(manifest_raw)
    return (
        repository,
        c_pre,
        manifest_path,
        manifest,
        hashlib.sha256(manifest_raw).hexdigest(),
    )


def _invoke(
    repository: Path,
    c_pre: Path,
    manifest_path: Path,
    manifest_digest: str,
    *,
    target: str = "measurement",
    extra_argv: tuple[str, ...] = (),
    extra_env: dict[str, str] | None = None,
    external_context_updates: dict[str, object] | None = None,
    external_context_remove: str | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = {MANIFEST_SHA_ENV: manifest_digest}
    if extra_env:
        environment.update(extra_env)
    bootstrap = c_pre / "scripts/bootstrap_v180r12r4_campaign_measurement.py"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frozen = manifest["frozen_authorization_context"]
    current_attempt_id = ("a" if target == "measurement" else "b") * 64
    current_attempt_sha256 = ("c" if target == "measurement" else "d") * 64
    measurement_attempt_id = "a" * 64
    measurement_attempt_sha256 = "c" * 64
    monotonic_origin_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    hard_deadline_ns = monotonic_origin_ns + 14_400 * 1_000_000_000
    campaign_deadline_ns = hard_deadline_ns - 600 * 1_000_000_000
    service_contract = manifest["production_systemd_service_contract"]
    service_row = next(
        row for row in service_contract["target_rows"] if row["target"] == target
    )
    systemd_argv = list(
        manifest["production_systemd_run_argv_templates"][target]
    )
    placeholder = (
        "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
        "__V180R12R4_MATERIALIZATION_TERMINAL_SHA256__"
    )
    assert systemd_argv.count(placeholder) == 1
    systemd_argv[systemd_argv.index(placeholder)] = (
        "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256=" + "f" * 64
    )
    production_invocation = {
        "schema": protocol.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_SCHEMA,
        "token_domain": protocol.PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN,
        "target": target,
        "token_input": service_row["token_input"],
        "token": service_row["token"],
        "unit_name": service_row["unit_name"],
        "unit_kind": "SERVICE_NOT_SCOPE",
        "slice": "app.slice",
        "service_type": "exec",
        "delegate": True,
        "umask": "0077",
        "launcher_command": systemd_argv[
            systemd_argv.index("/usr/bin/env") :
        ],
        "systemd_run_argv": systemd_argv,
    }
    cgroup = frozen["cgroup_parent_fact"]
    parent_path = Path(cgroup["parent_path"])
    mount_path = Path(cgroup["mount_point"])
    service_path = parent_path / service_row["unit_name"]
    service_path.mkdir(exist_ok=True)

    def directory_fact(
        path: Path, descriptor: int, role: str, access: str
    ) -> dict[str, object]:
        metadata = path.stat()
        return {
            "fd": descriptor,
            "role": role,
            "access": access,
            "path": str(path),
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode),
            "owner_uid": metadata.st_uid,
            "owner_gid": metadata.st_gid,
            "nlink": metadata.st_nlink,
        }

    membership = "0::/app.slice/" + service_row["unit_name"]
    placement_t1 = {
        "schema": "acfqp.v180r12r4_production_runtime_placement_t1.v1",
        "target": target,
        "token": service_row["token"],
        "unit_name": service_row["unit_name"],
        "slice": "app.slice",
        "source_membership": membership,
        "expected_source_membership": membership,
        "self_pid": os.getpid(),
        "self_pid_in_source_cgroup_procs": True,
        "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
        "delegated_parent_fd_fact": directory_fact(
            parent_path, 250, "DELEGATED_CGROUP_PARENT_DIRECTORY", "O_RDONLY"
        ),
        "cgroup2_mount_fd_fact": directory_fact(
            mount_path, 251, "CGROUP2_MOUNT_DIRECTORY", "O_PATH"
        ),
        "source_service_fd_fact": directory_fact(
            service_path, 252, "SOURCE_SYSTEMD_SERVICE_DIRECTORY", "O_RDONLY"
        ),
        "nearest_common_ancestor_path": str(parent_path),
        "nearest_common_ancestor_is_app_slice": True,
        "parent_cgroup_procs_o_wronly_openable": True,
        "planned_measurement_root_observation": {"root_state": "ABSENT"},
        "planned_measurement_root_absent": True,
        "t1_complete_before_child_popen": True,
    }
    context = {
        "schema": "acfqp.v180r12r4_external_launch_context.v1",
        "target": target,
        "actor_role": {"measurement": "OBSERVER", "verification": "VERIFIER"}[
            target
        ],
        "repository_root": str(repository),
        "c_pre_root": str(c_pre),
        "prereg_commit_id": manifest["c_pre_commit_id"],
        "prelaunch_materialization_terminal_id": "e" * 64,
        "prelaunch_materialization_terminal_byte_count": 1,
        "prelaunch_materialization_terminal_sha256": "f" * 64,
        "prelaunch_launch_manifest_sha256": manifest_digest,
        "prelaunch_launch_rule_id": "1" * 64,
        "current_launch_attempt_id": current_attempt_id,
        "current_launch_attempt_byte_count": 1,
        "current_launch_attempt_sha256": current_attempt_sha256,
        "measurement_launch_attempt_id": measurement_attempt_id,
        "measurement_launch_attempt_byte_count": 1,
        "measurement_launch_attempt_sha256": measurement_attempt_sha256,
        "protocol_id": frozen["protocol_id"],
        "protocol_byte_count": frozen["protocol_byte_count"],
        "protocol_sha256": frozen["protocol_sha256"],
        "authorization_id": frozen["authorization_id"],
        "authorization_byte_count": frozen["authorization_byte_count"],
        "authorization_sha256": frozen["authorization_sha256"],
        "authorization_evidence_id": frozen["authorization_evidence_id"],
        "authorization_evidence_byte_count": frozen[
            "authorization_evidence_byte_count"
        ],
        "authorization_evidence_sha256": frozen[
            "authorization_evidence_sha256"
        ],
        "campaign_measurement_execution_slot_id": frozen[
            "campaign_measurement_execution_slot_id"
        ],
        "logical_occurrence_id": frozen["logical_occurrence_id"],
        "execution_nonce": frozen["execution_nonce"],
        "campaign_attempt_id": frozen["campaign_attempt_id"],
        "monotonic_origin_ns": monotonic_origin_ns,
        "hard_deadline_ns": hard_deadline_ns,
        "campaign_deadline_ns": campaign_deadline_ns,
        "cgroup_parent_fact": frozen["cgroup_parent_fact"],
        "runtime_capability_fact": frozen["runtime_capability_fact"],
        "production_systemd_service_invocation": production_invocation,
        "production_runtime_placement_t1": placement_t1,
        "inherited_fd_roles": (
            [
                [249, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"],
                [250, "DELEGATED_CGROUP_PARENT_DIRECTORY"],
                [251, "CGROUP2_MOUNT_DIRECTORY"],
                [252, "SOURCE_SYSTEMD_SERVICE_DIRECTORY"],
            ]
            if target == "measurement"
            else [[249, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"]]
        ),
        "target_payload": (
            {
                "delegated_cgroup_parent_fd": 250,
                "cgroup2_mount_fd": 251,
                "source_systemd_service_fd": 252,
            }
            if target == "measurement"
            else {}
        ),
        "one_shot": True,
    }
    if external_context_updates:
        context.update(external_context_updates)
    if external_context_remove is not None:
        context.pop(external_context_remove)
    sources: list[int] = []
    fixed = [249]
    context_source = _sealed_read_only_memfd(
        "v180r12r4-test-external-context", _canonical_bytes(context)
    )
    sources.append(context_source)
    os.dup2(context_source, 249, inheritable=True)
    if target == "measurement":
        parent_source = os.open(
            frozen["cgroup_parent_fact"]["parent_path"],
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        mount_source = os.open(
            frozen["cgroup_parent_fact"]["mount_point"],
            os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        service_source = os.open(
            service_path,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        sources.extend((parent_source, mount_source, service_source))
        os.dup2(parent_source, 250, inheritable=True)
        os.dup2(mount_source, 251, inheritable=True)
        os.dup2(service_source, 252, inheritable=True)
        fixed.extend((250, 251, 252))
    try:
        return subprocess.run(
            [
                PYTHON,
                *ISOLATED_FLAGS,
                str(bootstrap),
                target,
                str(repository),
                str(c_pre),
                str(manifest_path),
                *extra_argv,
            ],
            cwd=repository,
            env=environment,
            pass_fds=tuple(fixed),
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        for descriptor in fixed:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for descriptor in sources:
            if descriptor not in fixed:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _marshaled_row(code: object) -> dict[str, object]:
    raw = marshal.dumps(code)
    return {
        "marshal_byte_count": len(raw),
        "marshal_sha256": hashlib.sha256(raw).hexdigest(),
        "marshal_hex": raw.hex(),
    }


def _sealed_read_only_memfd(name: str, raw: bytes) -> int:
    descriptor = os.memfd_create(name, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        assert written > 0
        view = view[written:]
    os.fchmod(descriptor, 0o400)
    bootstrap = _bootstrap_module()
    fcntl.fcntl(
        descriptor,
        fcntl.F_ADD_SEALS,
        bootstrap._REQUIRED_MEMFD_SEAL_MASK,
    )
    read_only = os.open(f"/proc/self/fd/{descriptor}", os.O_RDONLY | os.O_CLOEXEC)
    os.close(descriptor)
    return read_only


def test_worker_staged_descriptor_bootstrap_validation_reads_zero_payload_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = _bootstrap_module()
    terminal_fd = _sealed_read_only_memfd("terminal-metadata-only", b"T" * 199_755)
    verification_fd = _sealed_read_only_memfd(
        "verification-metadata-only", b"V" * 2_752
    )
    for descriptor in (terminal_fd, verification_fd):
        os.set_inheritable(descriptor, True)
    reads: list[tuple[int, int]] = []
    native_read = bootstrap.os.read

    def observed_read(descriptor: int, byte_count: int) -> bytes:
        reads.append((descriptor, byte_count))
        return native_read(descriptor, byte_count)

    monkeypatch.setattr(bootstrap.os, "read", observed_read)
    context = {
        "target_payload": {
            "terminal_stage_byte_count": 199_755,
            "verification_stage_byte_count": 2_752,
            "subject_result_initial_byte_count": 0,
        }
    }
    try:
        bootstrap._validate_operational_descriptor(
            terminal_fd,
            "TERMINAL_STAGE_READ_ONLY_MEMFD",
            context=context,
        )
        bootstrap._validate_operational_descriptor(
            verification_fd,
            "VERIFICATION_STAGE_READ_ONLY_MEMFD",
            context=context,
        )
        assert reads == []
        assert os.lseek(terminal_fd, 0, os.SEEK_CUR) == 0
        assert os.lseek(verification_fd, 0, os.SEEK_CUR) == 0
    finally:
        os.close(terminal_fd)
        os.close(verification_fd)


def test_bootstrap_failure_path_bypasses_hostile_type_message_and_traceback_hooks() -> None:
    bootstrap = _bootstrap_module()

    class HostileMeta(type):
        def __getattribute__(cls, name: str):
            if name == "__name__":
                raise RuntimeError("HOSTILE_TYPE_NAME")
            return type.__getattribute__(cls, name)

    class HostilePrimary(RuntimeError, metaclass=HostileMeta):
        def __getattribute__(self, name: str):
            if name == "__traceback__":
                raise RuntimeError("HOSTILE_TRACEBACK")
            return RuntimeError.__getattribute__(self, name)

        def with_traceback(self, traceback):
            del traceback
            return RuntimeError("REPLACED_PRIMARY")

        def __str__(self) -> str:
            raise RuntimeError("HOSTILE_PRIMARY_MESSAGE")

    class HostileSecondary(RuntimeError, metaclass=HostileMeta):
        def __str__(self) -> str:
            raise RuntimeError("HOSTILE_SECONDARY_MESSAGE")

    try:
        raise HostilePrimary("PRIMARY")
    except BaseException as error:
        primary = error
        traceback = BaseException.__getattribute__(error, "__traceback__")
    secondary = bootstrap._RunnerSecondaryObservation(
        (HostileSecondary("S" * 10_000),)
    )
    rendered = RuntimeError.__str__(secondary)
    assert "HostileSecondary" in rendered
    assert "HOSTILE_SECONDARY_MESSAGE" not in rendered
    assert len(rendered.encode("utf-8")) < 2_000
    with pytest.raises(HostilePrimary) as caught:
        bootstrap._raise_preserved_runner_primary(primary, traceback, secondary)
    assert caught.value is primary
    assert BaseException.__getattribute__(caught.value, "__cause__") is secondary


def _internal_bundle(
    repository: Path,
    c_pre: Path,
    manifest_path: Path,
    manifest_digest: str,
) -> bytes:
    bootstrap = _bootstrap_module()
    package_path = repository / "src/acfqp/__init__.py"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text("", encoding="utf-8")
    package_code = compile("", str(package_path), "exec", dont_inherit=True)
    source_rows = [
        {
            "module": "acfqp",
            "source_path": str(package_path),
            "is_package": True,
            **_marshaled_row(package_code),
        }
    ]
    runner_source = (
        "def bootstrap_entrypoint_v180r12r4(context):\n"
        "    import hashlib, json, os\n"
        "    operational = [\n"
        "        fd for fd, role in context['inherited_fd_roles']\n"
        "        if role not in {\n"
        "            'PARENT_TO_CHILD_MAC_KEY_MEMFD',\n"
        "            'INTERNAL_LAUNCH_CONTEXT_MEMFD',\n"
        "        }\n"
        "    ]\n"
        "    closed_context_fds = []\n"
        "    for fd in (242, 243):\n"
        "        try:\n"
        "            os.fstat(fd)\n"
        "        except OSError:\n"
        "            closed_context_fds.append(fd)\n"
        "    print(json.dumps({\n"
        "        'actor_role': context['actor_role'],\n"
        "        'closed_context_fds': closed_context_fds,\n"
        "        'context_consumed_once': context['context_consumed_once'],\n"
        "        'key_sha256': hashlib.sha256(\n"
        "            context['parent_to_child_mac_key']\n"
        "        ).hexdigest(),\n"
        "        'operational_fds_are_cloexec': all(\n"
        "            not os.get_inheritable(fd) for fd in operational\n"
        "        ),\n"
        "        'target': context['target'],\n"
        "        'target_payload_keys': sorted(context['target_payload']),\n"
        "    }, sort_keys=True), flush=True)\n"
    )
    target_rows = []
    for target in bootstrap._MEASURED_TARGETS:
        path = repository / RUNNER_PATHS[target]
        path.parent.mkdir(parents=True, exist_ok=True)
        # A hostile working-tree body demonstrates that the internal branch
        # dispatches only the sealed precompiled record below.
        path.write_text("raise RuntimeError('WORKING_TREE_EXECUTED')\n", encoding="utf-8")
        code = compile(runner_source, str(path), "exec", dont_inherit=True)
        target_rows.append(
            {
                "target": target,
                "source_path": str(path),
                **_marshaled_row(code),
            }
        )
    return _canonical_bytes(
        {
            "schema": bootstrap._PRECOMPILED_BUNDLE_SCHEMA,
            "manifest_sha256": manifest_digest,
            "c_pre_commit_id": "b" * 40,
            "repository_root": str(repository),
            "c_pre_root": str(c_pre),
            "manifest_path": str(manifest_path),
            "measured_target_contract": list(bootstrap._MEASURED_TARGETS),
            "source_records": source_rows,
            "target_records": target_rows,
        }
    )


def test_native_zero_summary_rejects_acfqp_prefix_confusion(tmp_path: Path) -> None:
    bootstrap = _bootstrap_module()
    application = tmp_path / "src/acfqp/real.py"
    application.parent.mkdir(parents=True)
    application.write_text("value = 1\n", encoding="utf-8")
    foreign = tmp_path / "src/acfqp_evil.py"
    foreign.write_text("value = 2\n", encoding="utf-8")

    def source(module: str, path: Path) -> dict:
        code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
        return {
            "module": module,
            "source_path": str(path),
            "is_package": False,
            **_marshaled_row(code),
        }

    target_rows = []
    for target in bootstrap._MEASURED_TARGETS:
        relative = RUNNER_PATHS[target]
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pass\n", encoding="utf-8")
        target_rows.append(
            {
                "target": target,
                "source_path": str(path),
                **_marshaled_row(compile("pass\n", str(path), "exec")),
            }
        )
    rows = bootstrap._native_zero_precompiled_source_rows(
        source_rows=[
            source("acfqp.real", application),
            source("acfqp_evil", foreign),
        ],
        target_rows=target_rows,
        repository_root=tmp_path,
    )
    assert "acfqp.real" in {row["name"] for row in rows}
    assert "acfqp_evil" not in {row["name"] for row in rows}
    assert {
        row["name"] for row in rows if row["source_kind"] == "TARGET"
    } == set(bootstrap._MEASURED_TARGETS)


def _invoke_internal(
    tmp_path: Path,
    *,
    target: str,
    context_updates: dict[str, object] | None = None,
    extra_inherited_file: bool = False,
) -> subprocess.CompletedProcess[str]:
    bootstrap = _bootstrap_module()
    repository = (tmp_path / f"repository-{target}").absolute()
    c_pre = (tmp_path / f"c-pre-{target}").absolute()
    repository.mkdir()
    c_pre.mkdir()
    retained_bootstrap = c_pre / "bootstrap.py"
    shutil.copyfile(BOOTSTRAP, retained_bootstrap)
    manifest_path = c_pre / "launch_manifest.json"
    manifest_digest = "a" * 64
    bundle_raw = _internal_bundle(
        repository, c_pre, manifest_path, manifest_digest
    )
    bundle_digest = hashlib.sha256(bundle_raw).hexdigest()
    key_raw = b"v180r12r4-parent-to-child-key!"[:32].ljust(32, b"!")
    target_payload = (
        {
            "repository_root_fd": 244,
            "worker_cgroup_fd": 245,
        }
        if target == "supervisor"
        else {
            "terminal_stage_byte_count": 199_755,
            "verification_stage_byte_count": 2_752,
            "subject_result_initial_byte_count": 0,
        }
    )
    context: dict[str, object] = {
        "schema": bootstrap._INTERNAL_CONTEXT_SCHEMA,
        "target": target,
        "actor_role": bootstrap._INTERNAL_ACTOR_ROLE[target],
        "parent_actor_role": bootstrap._INTERNAL_PARENT_ROLE[target],
        "protocol_id": "1" * 64,
        "authorization_id": "2" * 64,
        "authorization_evidence_id": "6" * 64,
        "attempt_id": "3" * 64,
        "campaign_measurement_execution_slot_id": "7" * 64,
        "logical_occurrence_id": "8" * 64,
        "execution_nonce": "9" * 64,
        "prelaunch_materialization_terminal_id": "c" * 64,
        "prelaunch_launch_rule_id": "d" * 64,
        "measurement_launch_attempt_id": "4" * 64,
        "launch_operation_id": "5" * 64,
        "repository_root": str(repository),
        "c_pre_root": str(c_pre),
        "manifest_path": str(manifest_path),
        "launch_manifest_sha256": manifest_digest,
        "c_pre_commit_id": "b" * 40,
        "precompiled_source_bundle_sha256": bundle_digest,
        "runner_relative_path": RUNNER_PATHS[target],
        "inherited_fd_roles": [
            {"fd": descriptor, "role": role}
            for descriptor, role in bootstrap._INTERNAL_FD_ROLE_MAP[target]
        ],
        "target_payload": target_payload,
        "one_shot": True,
        "context_mac_algorithm": bootstrap._INTERNAL_CONTEXT_MAC_ALGORITHM,
        "context_mac_direction": "PARENT_TO_CHILD_ONLY",
    }
    if context_updates:
        context.update(context_updates)
    context["context_mac"] = hashlib.blake2s(
        _canonical_bytes(context), key=key_raw, digest_size=32
    ).hexdigest()
    context_raw = _canonical_bytes(context)

    resources: list[object] = []
    source_by_destination: dict[int, int] = {
        240: _sealed_read_only_memfd("bundle", bundle_raw),
        242: _sealed_read_only_memfd("key", key_raw),
        243: _sealed_read_only_memfd("context", context_raw),
    }
    ipc_left, ipc_right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    for endpoint in (ipc_left, ipc_right):
        endpoint.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            bootstrap._SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
        )
        endpoint.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            bootstrap._SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
        )
        assert endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF) >= (
            bootstrap._SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        )
        assert endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF) >= (
            bootstrap._SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        )
    resources.extend((ipc_left, ipc_right))
    source_by_destination[241] = ipc_right.fileno()
    native_subject_root: Path | None = None
    if target == "supervisor":
        worker_cgroup = tmp_path / "worker-cgroup"
        worker_cgroup.mkdir()
        source_by_destination[244] = os.open(repository, os.O_PATH | os.O_DIRECTORY)
        source_by_destination[245] = os.open(
            worker_cgroup, os.O_RDONLY | os.O_DIRECTORY
        )
    else:
        native_subject_root = Path(
            tempfile.mkdtemp(prefix="v180r12r4-bootstrap-subject-", dir="/tmp")
        )
        source_by_destination[246] = _sealed_read_only_memfd(
            "terminal", b"T" * 199_755
        )
        source_by_destination[247] = _sealed_read_only_memfd(
            "verification", b"V" * 2_752
        )
        source_by_destination[248] = os.open(
            native_subject_root / "SUBJECT_RESULT.partial",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    extra_descriptor = -1
    if extra_inherited_file:
        extra_descriptor = os.open(retained_bootstrap, os.O_RDONLY)

    source_descriptors = sorted(set(source_by_destination.values()))
    fixed_descriptors = sorted(source_by_destination)
    for destination, source in source_by_destination.items():
        os.dup2(source, destination, inheritable=True)
    pass_descriptors = [*fixed_descriptors]
    if extra_descriptor >= 0:
        pass_descriptors.append(extra_descriptor)

    try:
        return subprocess.run(
            [
                PYTHON,
                *ISOLATED_FLAGS,
                str(retained_bootstrap),
                target,
                str(repository),
                str(c_pre),
                str(manifest_path),
            ],
            cwd=repository,
            env={MANIFEST_SHA_ENV: manifest_digest, "LC_CTYPE": "C.UTF-8"},
            pass_fds=tuple(pass_descriptors),
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        for descriptor in fixed_descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for value in resources:
            value.close()
        for descriptor in source_descriptors:
            if descriptor != ipc_right.fileno():
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if extra_descriptor >= 0:
            os.close(extra_descriptor)
        if native_subject_root is not None:
            shutil.rmtree(native_subject_root)


def _rewrite_manifest(
    manifest_path: Path, manifest: dict[str, object]
) -> str:
    raw = _canonical_bytes(manifest)
    manifest_path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=1)
def _real_authorization_closure_paths() -> tuple[str, ...]:
    completed = subprocess.run(
        [
            PYTHON,
            "-c",
            (
                "import json;"
                    "from acfqp import construction_k7_campaign_measurement_"
                    "authorization_evidence_freeze_v180r12r4 as a;"
                "print(json.dumps(a.SOURCE_CLOSURE_REQUIRED_ROOTS))"
            ),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(json.loads(completed.stdout))


@lru_cache(maxsize=1)
def _installed_third_party_root() -> Path:
    completed = subprocess.run(
        [
            PYTHON,
            "-c",
            (
                "import json,packaging,tomli;"
                "print(json.dumps([str(__import__('pathlib').Path(packaging.__file__).parent.parent),"
                "str(__import__('pathlib').Path(tomli.__file__).parent.parent)]))"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    roots = json.loads(completed.stdout)
    assert roots[0] == roots[1]
    return Path(roots[0]).resolve(strict=True)


def _module_binding(relative: str, *, prefix: str = "src/") -> tuple[str, bool]:
    path = Path(relative.removeprefix(prefix))
    is_package = path.name == "__init__.py"
    parts = list(path.parts[:-1])
    if not is_package:
        parts.append(path.stem)
    return ".".join(parts), is_package


def _real_third_party_facts() -> list[dict[str, object]]:
    root = _installed_third_party_root()
    facts = []
    for namespace in ("packaging", "tomli"):
        for source in sorted((root / namespace).rglob("*.py")):
            relative = source.relative_to(root).as_posix()
            module, is_package = _module_binding(relative, prefix="")
            facts.append(
                {
                    "module": module,
                    "is_package": is_package,
                    "source_root": str(root),
                    **_file_fact(root, relative),
                }
            )
    return sorted(facts, key=lambda row: row["module"])


def _build_real_closure_launch(
    tmp_path: Path,
    *,
    real_runner_pre_main_stub: bool = False,
) -> tuple[Path, Path, Path, dict[str, object], str]:
    repository = (tmp_path / "real_repository").absolute()
    c_pre = (tmp_path / "real_c_pre").absolute()
    c_pre_bootstrap = c_pre / "scripts/bootstrap_v180r12r4_campaign_measurement.py"
    c_pre_bootstrap.parent.mkdir(parents=True)
    shutil.copyfile(BOOTSTRAP, c_pre_bootstrap)
    paths = _real_authorization_closure_paths()
    assert len(paths) == 27
    for relative in paths:
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    authorization_relative = (
        "src/acfqp/"
        "construction_k7_campaign_measurement_execution_authorization_v180r12r4.py"
    )
    assert authorization_relative in paths

    commit_id, git_argv = _git_identity(repository)
    module_bindings = [
        (*_module_binding(relative), relative)
        for relative in paths
        if relative.startswith("src/acfqp/")
    ]
    module_bindings = [
        (module, relative, is_package)
        for module, is_package, relative in module_bindings
    ]
    auth_module, auth_is_package = _module_binding(authorization_relative)
    assert auth_module == AUTHORIZATION_SELF_MODULE and not auth_is_package
    module_bindings.append((auth_module, authorization_relative, False))
    module_names = sorted(module for module, _, _ in module_bindings)
    runner_body = (
        "import importlib\n"
        "import json\n"
        f"module_names = {module_names!r}\n"
        "for module_name in module_names:\n"
        "    importlib.import_module(module_name)\n"
        "import packaging.markers\n"
        "import tomli\n"
        "print(json.dumps({\n"
        "    'imported_count': len(module_names),\n"
        "    'packaging_loader': type(packaging.markers.__loader__).__name__,\n"
        "    'tomli_loader': type(tomli.__loader__).__name__,\n"
        "}, sort_keys=True), flush=True)\n"
    )
    if real_runner_pre_main_stub:
        stub_body = ast.parse(
            _runner_prefix(commit_id, git_argv)
            + "import json\n"
            + "print(json.dumps({\n"
            + f"    'commit': os.environ[{COMMIT_ENV!r}],\n"
            + "    'runner': __file__.rsplit('/', 1)[1],\n"
            + "}, sort_keys=True), flush=True)\n"
        ).body
        for relative in RUNNER_PATHS.values():
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            mains = [
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main"
            ]
            assert len(mains) == 1
            mains[0].body = stub_body
            ast.fix_missing_locations(tree)
            (repository / relative).write_text(
                ast.unparse(tree) + "\n", encoding="utf-8"
            )
    else:
        runner_source = _runner_prefix(commit_id, git_argv) + runner_body
        for relative in RUNNER_PATHS.values():
            (repository / relative).write_text(runner_source, encoding="utf-8")

    source_modules = [
        {
            "module": module,
            "is_package": is_package,
            **_file_fact(repository, relative),
        }
        for module, relative, is_package in sorted(module_bindings)
    ]
    target_facts = {
        target: _file_fact(repository, relative)
        for target, relative in RUNNER_PATHS.items()
    }
    authorization_raw_facts = []
    for fact in source_modules:
        if fact["module"] == AUTHORIZATION_SELF_MODULE:
            continue
        if fact["module"] == AUTHORIZATION_EVIDENCE_MODULE:
            authorization_raw_facts.append(
                _normalized_wrapper_fact(repository, AUTHORIZATION_EVIDENCE_RELATIVE)
            )
        else:
            authorization_raw_facts.append(
                {
                    key: fact[key]
                    for key in ("relative_path", "byte_count", "sha256")
                }
            )
    authorization_raw_facts += list(target_facts.values())
    third_party_facts = _real_third_party_facts()
    authorization_closure = _closure(authorization_raw_facts)
    source_conformance = _working_tree_source_conformance(
        repository, authorization_closure
    )
    service_contract, service_templates = _service_manifest_contract(repository)
    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "repository_root": str(repository),
        "c_pre_root": str(c_pre),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": commit_id,
        "bootstrap": _file_fact(
            c_pre, "scripts/bootstrap_v180r12r4_campaign_measurement.py"
        ),
        "runtime": _runtime_fact(),
        "git": _git_manifest_fact(repository, commit_id, git_argv),
        "authorization_source_closure_kind": (
            "EXACT_RAW_AUTHORIZATION_SOURCE_CLOSURE_PLUS_AUTH_SELF_AND_BOUND_RUNNERS"
        ),
        "authorization_self_module": AUTHORIZATION_SELF_MODULE,
        "authorization_raw_source_modules": sorted(
            module
            for module, _, _ in module_bindings
            if module != AUTHORIZATION_SELF_MODULE
        ),
        "authorization_source_closure": authorization_closure,
        "working_tree_source_conformance": source_conformance,
        "source_modules": source_modules,
        "third_party_source_closure": _third_party_closure(third_party_facts),
        "targets": target_facts,
        "internal_target_contract": _bootstrap_module()._INTERNAL_TARGET_CONTRACT,
        "production_systemd_service_contract": service_contract,
        "production_systemd_run_argv_templates": service_templates,
        "production_service_launch_artifact_paths": _service_artifact_paths(),
        "production_service_launch_modes": {
            "outer_dispatch": "dispatch",
            "retained_service_entry": "service-entry",
        },
        "atomic_cgroup_birth_preflight_receipt_interface": dict(
            protocol.ZERO_ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE
        ),
        "frozen_authorization_context": _frozen_authorization_context(repository),
        "working_tree_mutation_after_snapshot_in_scope": False,
    }
    manifest_path = c_pre / "launch_manifest.json"
    manifest_raw = _canonical_bytes(manifest)
    manifest_path.write_bytes(manifest_raw)
    return repository, c_pre, manifest_path, manifest, hashlib.sha256(manifest_raw).hexdigest()


def test_bootstrap_has_only_stdlib_imports_and_no_filesystem_dispatch() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.add((node.module or "").split(".", 1)[0])
    assert imported == {
        "ast",
        "fcntl",
        "hashlib",
        "importlib",
        "io",
        "json",
        "marshal",
        "os",
        "pathlib",
        "re",
        "socket",
        "stat",
        "subprocess",
        "sys",
        "sysconfig",
        "time",
        "tokenize",
        "types",
    }
    assert "from acfqp" not in source
    assert "runpy" not in source
    assert "runner_module = types.ModuleType(module_name)" in source
    assert "module_registry[module_name] = runner_module" in source
    assert "exec(code, runner_namespace)" in source
    assert "class _BoundSourceLoader" in source


def test_successful_dispatch_uses_only_in_memory_bound_source(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, manifest, digest = _build_launch(tmp_path)
    expected = {
        "authorization": True,
        "cached": None,
        "file": str(repository / "src/acfqp/bound.py"),
        "loader": "_BoundSourceLoader",
        "value": "IN_MEMORY_BOUND_SOURCE",
        "packaging": "bound-source",
        "tomli": 7,
        "commit": manifest["c_pre_commit_id"],
        "sys_path": _runtime_fact()["base_sys_path"],
    }
    for target in ("measurement", "verification"):
        completed = _invoke(
            repository, c_pre, manifest_path, digest, target=target
        )
        assert completed.returncode == 0, completed.stderr
        assert json.loads(completed.stdout) == expected
    assert list(repository.rglob("__pycache__")) == []
    assert list(c_pre.rglob("__pycache__")) == []


@pytest.mark.parametrize(
    ("updates", "removed", "expected"),
    (
        ({}, "current_launch_attempt_id", "schema is not exact"),
        ({"actor_role": "OBSERVER"}, None, "role/path/FD binding changed"),
        ({"protocol_id": "f" * 64}, None, "differs from manifest authority"),
    ),
)
def test_real_bootstrap_verification_target_rejects_missing_or_resigned_foreign_context(
    tmp_path: Path,
    updates: dict[str, object],
    removed: str | None,
    expected: str,
) -> None:
    repository, c_pre, manifest_path, _manifest, digest = _build_launch(tmp_path)
    completed = _invoke(
        repository,
        c_pre,
        manifest_path,
        digest,
        target="verification",
        external_context_updates=updates,
        external_context_remove=removed,
    )
    assert completed.returncode != 0
    assert expected in completed.stderr


def test_bootstrap_prework_exhausted_absolute_campaign_deadline_never_dispatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bootstrap = _bootstrap_module()
    deadline_ns = 123_456_789
    dispatches: list[object] = []
    monkeypatch.setattr(
        bootstrap.time,
        "clock_gettime_ns",
        lambda clock_id: deadline_ns
        if clock_id == bootstrap.time.CLOCK_MONOTONIC
        else pytest.fail("unexpected clock"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_execute_precompiled_runner",
        lambda *args, **kwargs: dispatches.append((args, kwargs)),
    )
    with pytest.raises(
        RuntimeError,
        match="bootstrap prework exhausted the shared campaign deadline",
    ):
        bootstrap._execute_precompiled_runner_before_campaign_deadline(
            object(),
            "runner.py",
            {},
            object(),
            verified_internal_context={"campaign_deadline_ns": deadline_ns},
        )
    assert dispatches == []


def test_exact_twenty_seven_static_roots_match_authorization_contract() -> None:
    completed = subprocess.run(
        [
            PYTHON,
            "-c",
            (
                "import json;"
                "from acfqp import construction_k7_campaign_measurement_"
                "execution_authorization_v180r12r4 as a;"
                "print(json.dumps(a.SOURCE_CLOSURE_REQUIRED_ROOTS))"
            ),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=True,
        capture_output=True,
        text=True,
    )
    assert tuple(json.loads(completed.stdout)) == SOURCE_CLOSURE_REQUIRED_ROOTS
    assert len(SOURCE_CLOSURE_REQUIRED_ROOTS) == 27
    assert (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r5.py"
        in SOURCE_CLOSURE_REQUIRED_ROOTS
    )
    assert (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r6.py"
        in SOURCE_CLOSURE_REQUIRED_ROOTS
    )
    assert (
        "src/acfqp/construction_k7_campaign_measurement_"
        "failure_freeze_v180r12r4r7.py"
        in SOURCE_CLOSURE_REQUIRED_ROOTS
    )


def test_exact_four_manifest_targets_and_two_internal_entrypoints_are_bound() -> None:
    assert RUNNER_PATHS == {
        "measurement": "scripts/run_v180r12r4_campaign_measurement.py",
        "verification": "scripts/verify_v180r12r4_campaign_measurement.py",
        "supervisor": "scripts/supervise_v180r12r4_campaign_measurement.py",
        "worker": "scripts/work_v180r12r4_campaign_measurement.py",
    }
    contract = _bootstrap_module()._INTERNAL_TARGET_CONTRACT
    assert contract["target_order"] == ["supervisor", "worker"]
    assert contract["precompiled_bundle_schema"] == (
        "acfqp.v180r12r4_precompiled_source_bundle.v1"
    )
    assert contract["dynamic_identity_in_argv_or_environment"] is False
    assert contract["initial_environment_keys"] == [MANIFEST_SHA_ENV, "LC_CTYPE"]
    assert [row["fd"] for row in contract["target_rows"][0]["inherited_fd_roles"]] == [
        240, 241, 242, 243, 244, 245
    ]
    assert [row["fd"] for row in contract["target_rows"][1]["inherited_fd_roles"]] == [
        240, 241, 242, 243, 246, 247, 248
    ]
    assert contract["bootstrap_entry_open_fd_inventory_is_exact"] is True
    assert contract["sock_seqpacket_buffer_request_bytes"] == 1_048_576
    assert contract["sock_seqpacket_effective_min_bytes"] == 2_097_152
    assert contract["sock_seqpacket_buffer_pair_roles"] == [
        "OBSERVER_SUPERVISOR_SOCK_SEQPACKET",
        "SUPERVISOR_WORKER_SOCK_SEQPACKET",
    ]
    assert contract[
        "sock_seqpacket_so_sndbuf_and_so_rcvbuf_required_on_both_endpoints"
    ] is True
    module_contract = contract["precompiled_runner_module_contract"]
    assert module_contract == {
        "module_type": "types.ModuleType",
        "target_order": list(RUNNER_PATHS),
        "target_rows": [
            {"target": target, "module_name": RUNNER_MODULE_NAMES[target]}
            for target in RUNNER_PATHS
        ],
        "exact_metadata_fields": [
            "__name__",
            "__file__",
            "__package__",
            "__cached__",
            "__loader__",
            "__spec__",
        ],
        "registered_before_runner_exec": True,
        "registration_spans_exec_entrypoint_and_postchecks": True,
        "preexisting_registration_fails_before_mutation": True,
        "preexisting_registration_is_preserved": True,
        "replaced_deleted_or_metadata_drifted_registration_fails": True,
        "registration_removed_after_postchecks_on_success_or_failure": True,
        "runner_module_registration_leak_forbidden": True,
        "runner_primary_error_precedes_registration_secondary": True,
    }
    assert len(set(RUNNER_MODULE_NAMES.values())) == 4


@pytest.mark.parametrize("target", tuple(RUNNER_PATHS))
def test_target_specific_module_registration_supports_real_top_level_dataclass(
    target: str,
) -> None:
    dataclass_name, dataclass_source = _first_real_top_level_dataclass_source(
        target
    )
    result = _runner_module_lifecycle_probe(
        target=target,
        mode="success",
        real_dataclass_source=dataclass_source,
        real_dataclass_name=dataclass_name,
    )
    assert result == {
        "error_type": None,
        "error_message": None,
        "cause_type": None,
        "cause_message": None,
        "module_name": RUNNER_MODULE_NAMES[target],
        "registry_is_original": True,
        "slot_present": False,
        "slot_is_preexisting": False,
    }


@pytest.mark.parametrize("target", tuple(RUNNER_PATHS))
def test_target_specific_runner_module_preexisting_collision_is_not_replaced(
    target: str,
) -> None:
    result = _runner_module_lifecycle_probe(target=target, mode="collision")
    assert result["error_type"] == "RuntimeError"
    assert "registered before dispatch" in result["error_message"]
    assert result["cause_type"] is None
    assert result["module_name"] == RUNNER_MODULE_NAMES[target]
    assert result["slot_present"] is True
    assert result["slot_is_preexisting"] is True


@pytest.mark.parametrize(
    ("mode", "expected"),
    (
        ("deleted", "module registration was deleted"),
        ("replaced", "module registration was replaced"),
        ("metadata_drift", "module metadata changed: __file__"),
        ("metadata_equality_spoof", "module metadata changed: __loader__"),
    ),
)
def test_runner_module_deletion_replacement_or_metadata_drift_fails_and_leaks_none(
    mode: str,
    expected: str,
) -> None:
    result = _runner_module_lifecycle_probe(target="measurement", mode=mode)
    assert result["error_type"] == "_RunnerSecondaryObservation"
    assert expected in result["error_message"]
    assert result["cause_type"] is None
    assert result["slot_present"] is False
    assert result["slot_is_preexisting"] is False


def test_runner_primary_is_preserved_and_module_registration_leaks_none() -> None:
    result = _runner_module_lifecycle_probe(target="verification", mode="primary")
    assert result["error_type"] == "PrimaryRunnerError"
    assert result["error_message"] == "PRIMARY_RUNNER_FAILURE"
    assert result["cause_type"] is None
    assert result["slot_present"] is False
    assert result["slot_is_preexisting"] is False


def test_runner_primary_precedes_replaced_registration_secondary_and_leaks_none() -> None:
    result = _runner_module_lifecycle_probe(
        target="supervisor", mode="primary_secondary"
    )
    assert result["error_type"] == "PrimaryRunnerError"
    assert result["error_message"] == "PRIMARY_RUNNER_FAILURE"
    assert result["cause_type"] == "_RunnerSecondaryObservation"
    assert "module registration was replaced" in result["cause_message"]
    assert result["slot_present"] is False
    assert result["slot_is_preexisting"] is False


@pytest.mark.parametrize(
    "mode", ("interrupt_after_registration", "interrupt_secondary")
)
def test_async_baseexception_restores_registry_identity_and_leaks_no_runner_module(
    mode: str,
) -> None:
    result = _runner_module_lifecycle_probe(target="worker", mode=mode)
    assert result["error_type"] == "KeyboardInterrupt"
    assert result["error_message"] == "INJECTED_RUNNER_LIFECYCLE_INTERRUPT"
    assert result["cause_type"] is None
    assert result["trace_injected"] is True
    assert result["registry_is_original"] is True
    assert result["slot_present"] is False
    assert result["slot_is_preexisting"] is False


def test_internal_seqpacket_effective_buffer_is_rechecked_before_dispatch() -> None:
    bootstrap = _bootstrap_module()
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        os.set_inheritable(left.fileno(), True)
        left.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4_096)
        left.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4_096)
        with pytest.raises(RuntimeError, match="effective buffer changed"):
            bootstrap._validate_operational_descriptor(
                left.fileno(),
                "OBSERVER_SUPERVISOR_SOCK_SEQPACKET",
                context={},
            )
        left.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            bootstrap._SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
        )
        left.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            bootstrap._SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
        )
        bootstrap._validate_operational_descriptor(
            left.fileno(),
            "OBSERVER_SUPERVISOR_SOCK_SEQPACKET",
            context={},
        )
    finally:
        left.close()
        right.close()


def test_internal_targets_use_sealed_precompiled_code_and_verified_context(
    tmp_path: Path,
) -> None:
    expected_payload_keys = {
        "supervisor": ["repository_root_fd", "worker_cgroup_fd"],
        "worker": [
            "subject_result_initial_byte_count",
            "terminal_stage_byte_count",
            "verification_stage_byte_count",
        ],
    }
    expected_roles = {"supervisor": "SUPERVISOR", "worker": "WORKER"}
    key_digest = hashlib.sha256(
        b"v180r12r4-parent-to-child-key!"[:32].ljust(32, b"!")
    ).hexdigest()
    for target in ("supervisor", "worker"):
        completed = _invoke_internal(tmp_path, target=target)
        assert completed.returncode == 0, completed.stderr
        assert json.loads(completed.stdout) == {
            "actor_role": expected_roles[target],
            "closed_context_fds": [242, 243],
            "context_consumed_once": True,
            "key_sha256": key_digest,
            "operational_fds_are_cloexec": True,
            "target": target,
            "target_payload_keys": expected_payload_keys[target],
        }
        assert "WORKING_TREE_EXECUTED" not in completed.stderr


def test_internal_target_rejects_role_crossing_under_a_valid_mac(
    tmp_path: Path,
) -> None:
    completed = _invoke_internal(
        tmp_path,
        target="supervisor",
        context_updates={"actor_role": "WORKER"},
    )
    assert completed.returncode != 0
    assert "internal launch context binding changed" in completed.stderr


@pytest.mark.parametrize(
    "field",
    (
        "authorization_evidence_id",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_rule_id",
    ),
)
def test_internal_target_mac_covers_all_authority_provenance_fields(
    tmp_path: Path, field: str
) -> None:
    completed = _invoke_internal(
        tmp_path,
        target="supervisor",
        context_updates={field: "not-a-content-id"},
    )
    assert completed.returncode != 0
    assert "internal launch context binding changed" in completed.stderr


def test_internal_target_rejects_an_unregistered_inherited_descriptor(
    tmp_path: Path,
) -> None:
    completed = _invoke_internal(
        tmp_path,
        target="supervisor",
        extra_inherited_file=True,
    )
    assert completed.returncode != 0
    assert "internal open-FD inventory changed" in completed.stderr


def test_internal_bundle_rejects_missing_reordered_or_foreign_targets(
    tmp_path: Path,
) -> None:
    bootstrap = _bootstrap_module()
    repository = (tmp_path / "repository-bundle-attack").absolute()
    c_pre = (tmp_path / "c-pre-bundle-attack").absolute()
    repository.mkdir()
    c_pre.mkdir()
    manifest = c_pre / "launch_manifest.json"
    digest = "a" * 64
    original = json.loads(
        _internal_bundle(repository, c_pre, manifest, digest).decode("utf-8")
    )
    attacks = []
    missing = json.loads(json.dumps(original))
    missing["target_records"].pop()
    attacks.append(missing)
    reordered = json.loads(json.dumps(original))
    reordered["target_records"].reverse()
    attacks.append(reordered)
    foreign = json.loads(json.dumps(original))
    foreign["target_records"][1]["target"] = "measurement"
    attacks.append(foreign)
    for document in attacks:
        with pytest.raises(RuntimeError, match="measured target"):
            bootstrap._load_precompiled_bundle(
                _canonical_bytes(document),
                target="supervisor",
                manifest_digest=digest,
                repository_root=str(repository),
                c_pre_root=str(c_pre),
                manifest_path=str(manifest),
            )


def test_sourceless_legacy_pyc_is_rejected_even_if_runner_adds_repo_src(
    tmp_path: Path,
) -> None:
    side_effect = tmp_path / "legacy-pyc-side-effect.txt"
    runner_source = (
        "import sys\n"
        "sys.path.insert(0, __file__.rsplit('/scripts/', 1)[0] + '/src')\n"
        "import acfqp.legacy\n"
    )
    repository, c_pre, manifest_path, _, digest = _build_launch(
        tmp_path, measurement_body=runner_source
    )
    legacy_source = repository / "src/acfqp/legacy.py"
    legacy_source.write_text(
        "from pathlib import Path\n"
        f"Path({str(side_effect)!r}).write_text('executed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    legacy_pyc = repository / "src/acfqp/legacy.pyc"
    py_compile.compile(str(legacy_source), cfile=str(legacy_pyc), doraise=True)
    legacy_source.unlink()

    ordinary = subprocess.run(
        [PYTHON, "-S", "-B", "-c", "import acfqp.legacy"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(repository / "src")},
        check=False,
        capture_output=True,
        text=True,
    )
    assert ordinary.returncode == 0, ordinary.stderr
    assert side_effect.read_text(encoding="utf-8") == "executed"
    side_effect.unlink()

    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "unlisted bound module origin rejected: acfqp.legacy" in completed.stderr
    assert not side_effect.exists()


def test_wrong_manifest_schema_is_rejected(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, manifest, _ = _build_launch(tmp_path)
    manifest["schema"] = "acfqp.invalid"
    digest = _rewrite_manifest(manifest_path, manifest)
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "launch manifest schema changed" in completed.stderr


def test_wrong_manifest_environment_digest_is_rejected(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, _, _ = _build_launch(tmp_path)
    completed = _invoke(repository, c_pre, manifest_path, "0" * 64)
    assert completed.returncode != 0
    assert "launch manifest stream digest mismatch" in completed.stderr


def test_unsanitized_environment_is_rejected(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, _, digest = _build_launch(tmp_path)
    completed = _invoke(
        repository,
        c_pre,
        manifest_path,
        digest,
        extra_env={"PYTHONPATH": str(tmp_path)},
    )
    assert completed.returncode != 0
    assert "bootstrap environment is not sanitized" in completed.stderr


def test_wrong_exact_argv_is_rejected(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, _, digest = _build_launch(tmp_path)
    completed = _invoke(
        repository, c_pre, manifest_path, digest, extra_argv=("unexpected",)
    )
    assert completed.returncode != 0
    assert "bootstrap API is target, repository root, C_pre root, manifest" in completed.stderr


def test_executing_bootstrap_bytes_must_match_c_pre_raw_fact(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, _, digest = _build_launch(tmp_path)
    copied_bootstrap = c_pre / "scripts/bootstrap_v180r12r4_campaign_measurement.py"
    copied_bootstrap.write_bytes(copied_bootstrap.read_bytes() + b"\n# mutated\n")
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "executing bootstrap size disagrees with its registered bound" in completed.stderr


def test_symlinked_manifest_source_is_rejected(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, _, digest = _build_launch(tmp_path)
    source = repository / "src/acfqp/bound.py"
    external = tmp_path / "same-bound.py"
    external.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(external)
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "source module acfqp.bound is unavailable or symlinked" in completed.stderr


def test_unlisted_source_module_is_rejected_by_meta_path_loader(
    tmp_path: Path,
) -> None:
    runner_source = "import acfqp.unlisted\n"
    repository, c_pre, manifest_path, _, digest = _build_launch(
        tmp_path, measurement_body=runner_source
    )
    (repository / "src/acfqp/unlisted.py").write_text(
        "VALUE = 'FILESYSTEM_MODULE'\n", encoding="utf-8"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "unlisted bound module origin rejected: acfqp.unlisted" in completed.stderr


def test_site_pth_and_unlisted_top_level_imports_are_rejected(
    tmp_path: Path,
) -> None:
    side_effect = tmp_path / "pth-side-effect.txt"
    runner_source = (
        "import sys\n"
        "sys.path.insert(0, __file__.rsplit('/scripts/', 1)[0] + '/injection')\n"
        "import injected\n"
    )
    repository, c_pre, manifest_path, _, digest = _build_launch(
        tmp_path, measurement_body=runner_source
    )
    injection = repository / "injection"
    injection.mkdir()
    (injection / "injected.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(side_effect)!r}).write_text('executed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    (injection / "activate.pth").write_text(
        "import injected\n", encoding="utf-8"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "unlisted external import origin rejected: injected" in completed.stderr
    assert not side_effect.exists()

    site_root = tmp_path / "site"
    site_root.mkdir()
    repository, c_pre, manifest_path, _, digest = _build_launch(
        site_root, measurement_body="import site\n"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "site import machinery is forbidden" in completed.stderr


def test_authorization_source_closure_aggregate_is_exact(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, manifest, _ = _build_launch(tmp_path)
    closure = manifest["authorization_source_closure"]
    closure["file_count"] += 1
    digest = _rewrite_manifest(manifest_path, manifest)
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "authorization source closure aggregate registration changed" in completed.stderr


def test_registered_source_size_cap_is_rejected_before_file_read(
    tmp_path: Path,
) -> None:
    repository, c_pre, manifest_path, manifest, _ = _build_launch(tmp_path)
    bound_fact = next(
        fact for fact in manifest["source_modules"] if fact["module"] == "acfqp.bound"
    )
    bound_fact["byte_count"] = 8 * 1024 * 1024 + 1
    digest = _rewrite_manifest(manifest_path, manifest)
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "source module" in completed.stderr
    assert "exceeds its bound" in completed.stderr


def test_git_executable_raw_fact_is_bound(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, manifest, _ = _build_launch(tmp_path)
    manifest["git"]["executable_sha256"] = "0" * 64
    digest = _rewrite_manifest(manifest_path, manifest)
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "resolved Git executable stream digest mismatch" in completed.stderr


def test_runner_git_argv_is_enforced_by_process_audit(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, manifest, _ = _build_launch(tmp_path)
    manifest["git"]["runner_argv"][0][-1] = "--show-prefix"
    digest = _rewrite_manifest(manifest_path, manifest)
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "Git process 0 contract changed" in completed.stderr


def test_partial_git_primary_failure_is_preserved_with_incomplete_secondary(
    tmp_path: Path,
) -> None:
    repository, c_pre, manifest_path, _, digest = _build_launch(
        tmp_path, measurement_failure_mode="partial_git"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "six-process Git contract was incomplete" in completed.stderr
    assert completed.stderr.rstrip().endswith(
        "RuntimeError: PRIMARY_PARTIAL_GIT_FAILURE"
    )


def test_pre_main_import_primary_failure_is_not_masked_by_git_secondary(
    tmp_path: Path,
) -> None:
    repository, c_pre, manifest_path, _, digest = _build_launch(
        tmp_path, measurement_failure_mode="pre_main_import"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "six-process Git contract was incomplete" in completed.stderr
    assert completed.stderr.rstrip().endswith(
        "ImportError: V180r12r4 unlisted bound module origin rejected: "
        "acfqp.pre_main_missing"
    )


def test_no_primary_incomplete_git_schedule_raises_secondary(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, _, digest = _build_launch(
        tmp_path, measurement_failure_mode="no_primary_incomplete"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert completed.stderr.rstrip().endswith(
        "_RunnerSecondaryObservation: V180r12r4 runner secondary observations: "
        "RuntimeError: V180r12r4 six-process Git contract was incomplete"
    )


def test_wrapper_fact_matches_authorization_twelve_literal_normalization() -> None:
    raw = (ROOT / AUTHORIZATION_EVIDENCE_RELATIVE).read_bytes()
    local = _normalize_wrapper(raw)
    completed = subprocess.run(
        [
            PYTHON,
            "-c",
            (
                "import hashlib,json,pathlib;"
                "from acfqp import construction_k7_campaign_measurement_"
                "authorization_evidence_freeze_v180r12r4 as a;"
                f"r=pathlib.Path({str(ROOT / AUTHORIZATION_EVIDENCE_RELATIVE)!r}).read_bytes();"
                "n=a.normalize_own_source_v180r12r4(r);"
                "print(json.dumps([len(n),hashlib.sha256(n).hexdigest()]))"
            ),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == [
        len(local),
        hashlib.sha256(local).hexdigest(),
    ]


def test_wrapper_rejects_a_thirteenth_allowlisted_literal_assignment(
    tmp_path: Path,
) -> None:
    repository, c_pre, manifest_path, manifest, _ = _build_launch(tmp_path)
    wrapper = repository / AUTHORIZATION_EVIDENCE_RELATIVE
    wrapper.write_bytes(
        wrapper.read_bytes()
        + b'EXPECTED_AUTHORIZATION_EVIDENCE_ID = "duplicate"\n'
    )
    replacement = _file_fact(repository, AUTHORIZATION_EVIDENCE_RELATIVE)
    source_fact = next(
        fact
        for fact in manifest["source_modules"]
        if fact["module"] == AUTHORIZATION_EVIDENCE_MODULE
    )
    source_fact.update(replacement)
    digest = _rewrite_manifest(manifest_path, manifest)
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "wrapper literal assignment changed" in completed.stderr
