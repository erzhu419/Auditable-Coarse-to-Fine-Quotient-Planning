from __future__ import annotations

import ast
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py"
PYTHON = "/usr/bin/python3"
PYCACHE_PREFIX = "/dev/null/v180r12r2"
MANIFEST_SHA_ENV = "ACFQP_V180R12R2_LAUNCH_MANIFEST_SHA256"
SCHEMA = "acfqp.v180r12r2_source_bound_launch_manifest.v1"
AUTHORIZATION_SELF_MODULE = (
    "acfqp."
    "construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2"
)
AUTHORIZATION_EVIDENCE_MODULE = (
    "acfqp.construction_k7_ten_terminal_aggregation_execution_"
    "authorization_evidence_freeze_v180r12r2"
)
AUTHORIZATION_EVIDENCE_RELATIVE = (
    "src/acfqp/construction_k7_ten_terminal_aggregation_execution_"
    "authorization_evidence_freeze_v180r12r2.py"
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
)
WRAPPER_STRING_CONSTANTS = {
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
    "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
}
ISOLATED_FLAGS = (
    "-I",
    "-S",
    "-B",
    "-X",
    f"pycache_prefix={PYCACHE_PREFIX}",
)
RUNNER_PATHS = {
    "production": "scripts/run_v180r12r2_ten_terminal_aggregation.py",
    "verification": "scripts/verify_v180r12r2_ten_terminal_aggregation.py",
}
GIT = "/usr/bin/git"
COMMIT_ENV = "ACFQP_V180R12R2_PREREG_COMMIT"
MANIFEST_SHA_TEMPLATE = "__V180R12R2_MANIFEST_SHA256__"


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
            b'"__ACFQP_V180R12R2_POST_PREREG_REDACTED__"'
            if name in WRAPPER_STRING_CONSTANTS
            else b"0"
        )
        replacements.append((start, end, replacement))
    assert len(replacements) == 8
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
            "user.name=V180r12r2 Test",
            "-c",
            "user.email=v180r12r2@example.invalid",
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


def _build_launch(
    tmp_path: Path,
    *,
    production_body: str | None = None,
    production_failure_mode: str | None = None,
) -> tuple[Path, Path, Path, dict[str, object], str]:
    repository = (tmp_path / "repository").absolute()
    c_pre = (tmp_path / "c_pre").absolute()
    (repository / "scripts").mkdir(parents=True)
    (repository / "src/acfqp").mkdir(parents=True)
    (c_pre / "scripts").mkdir(parents=True)
    shutil.copyfile(
        BOOTSTRAP,
        c_pre / "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py",
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
        "construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2.py"
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
    if production_failure_mode == "partial_git":
        runner_source = (
            _runner_prefix(commit_id, git_argv[:1])
            + "raise RuntimeError('PRIMARY_PARTIAL_GIT_FAILURE')\n"
        )
    elif production_failure_mode == "pre_main_import":
        runner_source = "import acfqp.pre_main_missing\n"
    elif production_failure_mode == "no_primary_incomplete":
        runner_source = "PASSIVE_RETURN = True\n"
    elif production_failure_mode is None:
        runner_source = runner_prefix + (production_body or _default_runner_body())
    else:
        raise AssertionError("unknown production failure mode")
    for target, relative in RUNNER_PATHS.items():
        source = (
            runner_source
            if target == "production"
            else runner_prefix + _default_runner_body()
        )
        (repository / relative).write_text(source, encoding="utf-8")

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
    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "repository_root": str(repository),
        "c_pre_root": str(c_pre),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": commit_id,
        "bootstrap": _file_fact(
            c_pre, "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py"
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
        "authorization_source_closure": _closure(authorization_raw_facts),
        "source_modules": source_modules,
        "third_party_source_closure": _third_party_closure(third_party_facts),
        "targets": target_facts,
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
    target: str = "production",
    extra_argv: tuple[str, ...] = (),
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = {MANIFEST_SHA_ENV: manifest_digest}
    if extra_env:
        environment.update(extra_env)
    bootstrap = c_pre / "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py"
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
        check=False,
        capture_output=True,
        text=True,
    )


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
                "from acfqp import construction_k7_ten_terminal_aggregation_"
                "execution_authorization_v180r12r2 as a;"
                "print(json.dumps(a._static_source_closure_relative_paths()))"
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
    c_pre_bootstrap = c_pre / "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py"
    c_pre_bootstrap.parent.mkdir(parents=True)
    shutil.copyfile(BOOTSTRAP, c_pre_bootstrap)
    paths = _real_authorization_closure_paths()
    assert len(paths) == 236
    for relative in paths:
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    authorization_relative = (
        "src/acfqp/"
        "construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2.py"
    )
    assert authorization_relative not in paths
    (repository / authorization_relative).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / authorization_relative, repository / authorization_relative)

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
    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "repository_root": str(repository),
        "c_pre_root": str(c_pre),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": commit_id,
        "bootstrap": _file_fact(
            c_pre, "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py"
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
        "authorization_source_closure": _closure(authorization_raw_facts),
        "source_modules": source_modules,
        "third_party_source_closure": _third_party_closure(third_party_facts),
        "targets": target_facts,
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
        "hashlib",
        "importlib",
        "io",
        "json",
        "os",
        "pathlib",
        "re",
        "stat",
        "subprocess",
        "sys",
        "sysconfig",
        "tokenize",
    }
    assert "from acfqp" not in source
    assert "runpy" not in source
    assert "exec(code, globals_dict)" in source
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
    for target in ("production", "verification"):
        completed = _invoke(
            repository, c_pre, manifest_path, digest, target=target
        )
        assert completed.returncode == 0, completed.stderr
        assert json.loads(completed.stdout) == expected
    assert list(repository.rglob("__pycache__")) == []
    assert list(c_pre.rglob("__pycache__")) == []


def test_real_233_manifest_closure_from_236_bound_paths_imports_third_party(
    tmp_path: Path,
) -> None:
    repository, c_pre, manifest_path, manifest, digest = _build_real_closure_launch(
        tmp_path
    )
    # Three prelaunch scripts are separately bound C_pre raw facts, not importable
    # modules in the manifest authorization closure: 236 total bound paths - 3.
    assert manifest["authorization_source_closure"]["file_count"] == 233
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload == {
        "imported_count": len(manifest["source_modules"]),
        "packaging_loader": "_BoundSourceLoader",
        "tomli_loader": "_BoundSourceLoader",
    }


def test_real_runner_import_preamble_receives_commit_before_stubbed_main(
    tmp_path: Path,
) -> None:
    repository, c_pre, manifest_path, manifest, digest = _build_real_closure_launch(
        tmp_path,
        real_runner_pre_main_stub=True,
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "commit": manifest["c_pre_commit_id"],
        "runner": "run_v180r12r2_ten_terminal_aggregation.py",
    }


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
        tmp_path, production_body=runner_source
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
    copied_bootstrap = c_pre / "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py"
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
        tmp_path, production_body=runner_source
    )
    (repository / "src/acfqp/unlisted.py").write_text(
        "VALUE = 'FILESYSTEM_MODULE'\n", encoding="utf-8"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "unlisted bound module origin rejected: acfqp.unlisted" in completed.stderr


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
        tmp_path, production_failure_mode="partial_git"
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
        tmp_path, production_failure_mode="pre_main_import"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert "six-process Git contract was incomplete" in completed.stderr
    assert completed.stderr.rstrip().endswith(
        "ImportError: V180r12r2 unlisted bound module origin rejected: "
        "acfqp.pre_main_missing"
    )


def test_no_primary_incomplete_git_schedule_raises_secondary(tmp_path: Path) -> None:
    repository, c_pre, manifest_path, _, digest = _build_launch(
        tmp_path, production_failure_mode="no_primary_incomplete"
    )
    completed = _invoke(repository, c_pre, manifest_path, digest)
    assert completed.returncode != 0
    assert completed.stderr.rstrip().endswith(
        "_RunnerSecondaryObservation: V180r12r2 runner secondary observations: "
        "RuntimeError: V180r12r2 six-process Git contract was incomplete"
    )


def test_wrapper_fact_matches_authorization_eight_literal_normalization() -> None:
    raw = (ROOT / AUTHORIZATION_EVIDENCE_RELATIVE).read_bytes()
    local = _normalize_wrapper(raw)
    completed = subprocess.run(
        [
            PYTHON,
            "-c",
            (
                "import hashlib,json,pathlib;"
                "from acfqp import construction_k7_ten_terminal_aggregation_"
                "execution_authorization_v180r12r2 as a;"
                f"r=pathlib.Path({str(ROOT / AUTHORIZATION_EVIDENCE_RELATIVE)!r}).read_bytes();"
                "n=a.normalize_authorization_evidence_wrapper_source_v180r12r2(r);"
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


def test_wrapper_rejects_a_ninth_allowlisted_literal_assignment(tmp_path: Path) -> None:
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
