from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import py_compile
import subprocess
import sys
from types import MappingProxyType, SimpleNamespace
from typing import Any

import pytest

from scripts import launch_v42_activation_or_formal as launcher


def _hex(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _activation_cli() -> list[str]:
    return [
        str(launcher.SCRIPT_PATH),
        "activation",
        "--preformal-evidence-root", "/tmp/preformal",
        "--control-root", "/tmp/controls",
        "--resource-evidence-root", "/tmp/resource",
        "--activation-evidence-root", "/tmp/activation",
        "--expected-preformal-plan-id", _hex("preformal"),
    ]


def _formal_cli(mode: str = "--prepare-once") -> list[str]:
    return [
        str(launcher.SCRIPT_PATH),
        "formal",
        "--activation-evidence-root", "/tmp/activation",
        "--expected-activation-final-evidence-index-id", _hex("final"),
        mode,
    ]


def test_exact_activation_cli_exposes_no_request_or_program_override() -> None:
    parsed = launcher._parse_cli(_activation_cli())  # noqa: SLF001
    assert parsed.operation == "activation"
    assert parsed.driver_argv == (
        "--orchestrate-from-retained",
        "--preformal-evidence-root", "/tmp/preformal",
        "--expected-preformal-plan-id", _hex("preformal"),
        "--control-root", "/tmp/controls",
        "--resource-evidence-root", "/tmp/resource",
        "--activation-evidence-root", "/tmp/activation",
    )
    assert not any(
        token in parsed.driver_argv
        for token in (
            "--request", "--preformal-loader-path", "--preformal-receiver-path",
            "--activation-loader-path", "--activation-receiver-path",
            "--activation-service-path", "--activation-authority-path",
        )
    )


@pytest.mark.parametrize(
    "mode",
    [
        "--probe-host-epoch", "--prepare-once", "--admit-launch-once",
        "--inspect-prepare", "--inspect-launch",
    ],
)
def test_exact_formal_cli_forwards_one_mode_and_no_root_override(mode: str) -> None:
    parsed = launcher._parse_cli(_formal_cli(mode))  # noqa: SLF001
    assert parsed.operation == "formal"
    assert parsed.driver_argv == (
        "--activation-evidence-root", "/tmp/activation",
        "--expected-activation-final-evidence-index-id", _hex("final"),
        mode,
    )
    assert not any(
        token in parsed.driver_argv
        for token in (
            "--preformal-evidence-root", "--resource-evidence-root",
            "--control-evidence-root",
        )
    )


def test_inspection_ordinal_is_canonical_bounded_and_inspection_only() -> None:
    values = _formal_cli("--inspect-launch") + ["--inspection-ordinal", "7"]
    assert launcher._parse_cli(values).driver_argv[-2:] == (  # noqa: SLF001
        "--inspection-ordinal", "7"
    )
    for crossed in (
        _formal_cli("--prepare-once") + ["--inspection-ordinal", "1"],
        _formal_cli("--inspect-launch") + ["--inspection-ordinal", "01"],
        _formal_cli("--inspect-launch") + ["--inspection-ordinal", "0"],
        _formal_cli("--inspect-launch") + ["--inspection-ordinal", "4097"],
    ):
        with pytest.raises(launcher.V42ProductionLauncherError):
            launcher._parse_cli(crossed)  # noqa: SLF001


@pytest.mark.parametrize(
    "mutate",
    [
        lambda values: [values[0], *values[2:]],
        lambda values: [*values, "--request", "/tmp/request.json"],
        lambda values: [*values, "--activation-loader-path", "/tmp/x.py"],
        lambda values: [values[0], values[1], values[3], values[2], *values[4:]],
        lambda values: [*values[:-1], values[-1].upper()],
    ],
)
def test_shifted_or_expanded_activation_argv_is_rejected(mutate: Any) -> None:
    with pytest.raises(launcher.V42ProductionLauncherError):
        launcher._parse_cli(mutate(_activation_cli()))  # noqa: SLF001


def _runtime_sys(argv: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        executable=launcher.LOCAL_PYTHON,
        version_info=launcher.LOCAL_PYTHON_VERSION,
        flags=SimpleNamespace(isolated=1, no_site=1),
        dont_write_bytecode=True,
        argv=argv,
        orig_argv=[launcher.LOCAL_PYTHON, "-I", "-S", "-B", *argv],
        path=list(launcher.EXACT_PYTHON_PATH),
        gettrace=lambda: None,
        getprofile=lambda: None,
    )


def test_runtime_gate_accepts_only_exact_env_flags_hooks_argv_and_fds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    argv = _activation_cli()
    fake = _runtime_sys(argv)
    monkeypatch.setattr(launcher, "sys", fake)
    monkeypatch.setattr(launcher.os, "environ", dict(launcher.EXACT_ENVIRONMENT))
    monkeypatch.setattr(launcher, "_live_descriptors", lambda: [0, 1, 2])
    assert launcher._verify_runtime(launcher._parse_cli(argv)).operation == "activation"  # noqa: SLF001

    mutations = (
        lambda: setattr(fake.flags, "isolated", 0),
        lambda: setattr(fake.flags, "no_site", 0),
        lambda: setattr(fake, "dont_write_bytecode", False),
        lambda: setattr(fake, "gettrace", lambda: object()),
        lambda: setattr(fake, "getprofile", lambda: object()),
        lambda: fake.orig_argv.__setitem__(1, "-S"),
        lambda: fake.path.append("/tmp"),
    )
    for mutate in mutations:
        fake = _runtime_sys(argv)
        monkeypatch.setattr(launcher, "sys", fake)
        monkeypatch.setattr(launcher.os, "environ", dict(launcher.EXACT_ENVIRONMENT))
        monkeypatch.setattr(launcher, "_live_descriptors", lambda: [0, 1, 2])
        mutate()
        with pytest.raises(
            launcher.V42ProductionLauncherError,
            match="exact isolated Python runtime",
        ):
            launcher._verify_runtime(launcher._parse_cli(argv))  # noqa: SLF001

    fake = _runtime_sys(argv)
    monkeypatch.setattr(launcher, "sys", fake)
    monkeypatch.setattr(
        launcher.os, "environ", {**launcher.EXACT_ENVIRONMENT, "HOME": "/tmp"}
    )
    with pytest.raises(launcher.V42ProductionLauncherError):
        launcher._verify_runtime(launcher._parse_cli(argv))  # noqa: SLF001

    monkeypatch.setattr(launcher.os, "environ", dict(launcher.EXACT_ENVIRONMENT))
    monkeypatch.setattr(launcher, "_live_descriptors", lambda: [0, 1, 2, 9])
    with pytest.raises(
        launcher.V42ProductionLauncherError, match="extra file descriptor"
    ):
        launcher._verify_runtime(launcher._parse_cli(argv))  # noqa: SLF001


def _compile_legacy_pyc(source: Path, pyc: Path) -> None:
    py_compile.compile(str(source), cfile=str(pyc), doraise=True)
    source.unlink()


def test_unisolated_direct_entry_rejects_before_matching_header_stdlib_pyc(
    tmp_path: Path,
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    copied = scripts / launcher.SCRIPT_PATH.name
    copied.write_bytes(launcher.SCRIPT_PATH.read_bytes())
    sentinel = tmp_path / "STDLIB_PYC_EXECUTED"
    source = scripts / "json.py"
    source.write_text(
        "from pathlib import Path\nPath(" + repr(str(sentinel)) + ").write_text('x')\n",
        encoding="utf-8",
    )
    _compile_legacy_pyc(source, scripts / "json.pyc")
    observed = subprocess.run(
        ["/usr/bin/python3", str(copied), "activation"],
        cwd=tmp_path,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    assert observed.returncode == 72
    assert observed.stdout == b""
    assert observed.stderr == b"acfqp v42 production launcher rejected\n"
    assert not sentinel.exists()


@pytest.mark.parametrize("entry", ["runpy", "dash_c"])
def test_runpy_and_dash_c_shifted_entries_fail_at_early_gate(
    tmp_path: Path, entry: str,
) -> None:
    sentinel = tmp_path / "LATE_IMPORT"
    if entry == "runpy":
        code = (
            "import runpy;runpy.run_path(" + repr(str(launcher.SCRIPT_PATH))
            + ",run_name='__main__')"
        )
    else:
        code = (
            "p=" + repr(str(sentinel)) + ";exec(compile(open("
            + repr(str(launcher.SCRIPT_PATH)) + ").read(),p,'exec'))"
        )
    observed = subprocess.run(
        ["/usr/bin/python3", "-I", "-S", "-B", "-c", code],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    assert observed.returncode == 72
    assert b"acfqp v42 production launcher rejected" in observed.stderr
    assert not sentinel.exists()


def test_symlink_launcher_and_symlink_root_fail_closed(tmp_path: Path) -> None:
    link = tmp_path / launcher.SCRIPT_PATH.name
    link.symlink_to(launcher.SCRIPT_PATH)
    observed = subprocess.run(
        [
            "/usr/bin/env", "-i", "LANG=C.UTF-8", "LC_ALL=C.UTF-8",
            "PATH=/usr/bin:/bin", "/usr/bin/python3", "-I", "-S", "-B",
            str(link), *_activation_cli()[1:],
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    assert observed.returncode == 72
    assert observed.stdout == b""
    assert observed.stderr == b"acfqp v42 production launcher rejected\n"

    real = tmp_path / "real-root"
    real.mkdir(mode=0o700)
    root_link = tmp_path / "linked-root"
    root_link.symlink_to(real, target_is_directory=True)
    with pytest.raises((OSError, launcher.V42ProductionLauncherError)):
        launcher._RootGuard.capture(  # noqa: SLF001
            root_link, "linked root", require_existing=True
        )


def _git_row(path: str, oid: str) -> bytes:
    return f"100644 blob {oid}\t{path}".encode("ascii") + b"\0"


def test_selected_git_inventory_separates_revisions_and_rejects_head_swap() -> None:
    commit = "1" * 40
    tree = "2" * 40
    oid = "3" * 40
    path = "scripts/x.py"
    calls: list[tuple[str, ...]] = []

    def stable(*args: str) -> bytes:
        calls.append(args)
        if args == ("--version",):
            return b"git version pinned\n"
        if args[-2:] == ("--verify", "HEAD^{commit}"):
            return commit.encode() + b"\n"
        if args[-2:] == ("--verify", "HEAD^{tree}"):
            return tree.encode() + b"\n"
        if "ls-tree" in args:
            return _git_row(path, oid)
        raise AssertionError(args)

    selected = launcher._selected_git_inventory(  # noqa: SLF001
        stable, source_commit=commit, source_tree=tree, paths=(path,),
        version_stdout=b"git version pinned\n",
    )
    assert selected == {path: ("100644", "blob", oid)}
    assert all(
        not ("--verify" in call and "HEAD^{commit}" in call and "HEAD^{tree}" in call)
        for call in calls
    )

    tree_reads = 0

    def swapped(*args: str) -> bytes:
        nonlocal tree_reads
        if args == ("--version",):
            return b"git version pinned\n"
        if args[-2:] == ("--verify", "HEAD^{commit}"):
            return commit.encode() + b"\n"
        if args[-2:] == ("--verify", "HEAD^{tree}"):
            tree_reads += 1
            return (tree if tree_reads == 1 else "4" * 40).encode() + b"\n"
        if "ls-tree" in args:
            return _git_row(path, oid)
        raise AssertionError(args)

    with pytest.raises(
        launcher.V42ProductionLauncherError, match="changed across Git inventory"
    ):
        launcher._selected_git_inventory(  # noqa: SLF001
            swapped, source_commit=commit, source_tree=tree, paths=(path,),
            version_stdout=b"git version pinned\n",
        )


def _fact(relative: str, raw: bytes) -> dict[str, object]:
    return {
        "relative_path": relative,
        "git_mode": "100644",
        "git_object_type": "blob",
        "git_blob_oid": launcher._git_blob_oid(raw),  # noqa: SLF001
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def test_baseline_sized_transport_accepts_large_and_zero_non_tcb_rows() -> None:
    rows = []
    for ordinal in range(4656):
        byte_count = 59_473_200 if ordinal < 13 else (0 if ordinal == 13 else 1)
        rows.append({
            "relative_path": f"artifacts/{ordinal:08d}",
            "git_mode": "100644", "git_object_type": "blob",
            "git_blob_oid": f"{ordinal:040x}", "byte_count": byte_count,
            "sha256": f"{ordinal:064x}",
        })
    facts = launcher._fact_map(  # noqa: SLF001
        {"transport_facts": rows}, "transport_facts", "transport"
    )
    assert len(facts) == 4656
    assert facts["artifacts/00000000"]["byte_count"] == 59_473_200
    assert facts["artifacts/00000013"]["byte_count"] == 0


def test_frozen_pinned_git_detects_named_path_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = launcher._DirectoryPin.open(launcher.ROOT, "repository root")  # noqa: SLF001
    try:
        primitive = launcher._load_frozen_primitives(repo)  # noqa: SLF001
    finally:
        repo.close()
    executable = tmp_path / "git"
    raw = b"pinned-fake-git\n"
    executable.write_bytes(raw)
    executable.chmod(0o755)
    monkeypatch.setattr(primitive, "GIT_EXECUTABLE", str(executable))
    monkeypatch.setattr(primitive, "GIT_EXECUTABLE_REALPATH", str(executable))
    monkeypatch.setattr(primitive, "GIT_EXECUTABLE_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(primitive, "GIT_EXECUTABLE_BYTE_COUNT", len(raw))
    monkeypatch.setattr(primitive, "GIT_EXECUTABLE_UID", os.geteuid())
    monkeypatch.setattr(primitive, "GIT_EXECUTABLE_GID", os.getegid())

    def replace_after_pin(**_kwargs: object) -> object:
        replacement = tmp_path / "replacement"
        replacement.write_bytes(raw)
        replacement.chmod(0o755)
        os.replace(replacement, executable)
        return primitive._PinnedProcessObservationV42r1(
            exec_succeeded=True,
            returncode=0,
            timed_out=False,
            stdout_raw=b"git version pinned\n",
            stdout_total_byte_count=len(b"git version pinned\n"),
            stdout_overflow=False,
            stdout_eof=True,
            stderr_raw=b"",
            stderr_total_byte_count=0,
            stderr_overflow=False,
            stderr_eof=True,
        )

    monkeypatch.setattr(primitive, "_run_pinned_executable_v42r1", replace_after_pin)
    with pytest.raises(
        primitive.V42PreformalSenderLauncherError,
        match="fixed Git executable changed across read-only query",
    ):
        primitive._run_fixed_git_v42r1("--version")


def test_unrelated_ancestor_sibling_directory_churn_does_not_break_pin_or_loader(
    tmp_path: Path,
) -> None:
    pin = launcher._DirectoryPin.open(launcher.ROOT, "repository root")  # noqa: SLF001
    sibling = Path("/tmp") / (
        "acfqp-launcher-unrelated-" + _hex(str(tmp_path))[:16]
    )
    try:
        sibling.mkdir(mode=0o700)
        sibling.rmdir()
        pin.verify()
        primitive = launcher._load_frozen_primitives(pin)  # noqa: SLF001
        assert primitive.__acfqp_exec_count__ == 1
    finally:
        if sibling.exists():
            sibling.rmdir()
        pin.close()


def test_named_root_exchange_is_detected_without_ancestor_count_change(
    tmp_path: Path,
) -> None:
    root = tmp_path / "evidence"
    root.mkdir(mode=0o700)
    replacement = tmp_path / "replacement"
    replacement.mkdir(mode=0o700)
    guard = launcher._RootGuard.capture(  # noqa: SLF001
        root, "evidence root", require_existing=True
    )
    try:
        displaced = tmp_path / "displaced"
        root.rename(displaced)
        replacement.rename(root)
        with pytest.raises(launcher.V42ProductionLauncherError):
            guard.verify()
    finally:
        guard.close()


def test_live_modified_and_git_omitted_tcb_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    source_path = root / "src/acfqp/__init__.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"VALUE = 1\n")
    os.chmod(source_path, 0o644)
    raw = source_path.read_bytes()
    fact = _fact("src/acfqp/__init__.py", raw)
    source = {
        "source_commit": "1" * 40, "source_tree": "2" * 40,
        "source_facts": [fact],
    }
    transport = {"transport_facts": [fact]}
    monkeypatch.setattr(
        launcher, "TRANSPORT_ONLY_TCB_PATHS",
        frozenset({"src/acfqp/__init__.py"}),
    )
    pin = launcher._DirectoryPin.open(root, "test repo")  # noqa: SLF001
    try:
        version = b"git version pinned\n"

        def run(*args: str) -> bytes:
            if args == ("--version",):
                return version
            if args[-2:] == ("--verify", "HEAD^{commit}"):
                return b"1" * 40 + b"\n"
            if args[-2:] == ("--verify", "HEAD^{tree}"):
                return b"2" * 40 + b"\n"
            if "ls-tree" in args:
                return _git_row("src/acfqp/__init__.py", str(fact["git_blob_oid"]))
            raise AssertionError(args)

        primitives = SimpleNamespace(
            _run_fixed_git_v42r1=run, GIT_VERSION_STDOUT=version,
        )
        source_path.write_bytes(b"VALUE = 2\n")
        with pytest.raises(
            launcher.V42ProductionLauncherError,
            match="live launcher TCB bytes differ",
        ):
            launcher._verified_tcb(  # noqa: SLF001
                repo=pin, source=source, transport=transport,
                primitives=primitives,
            )

        source_path.write_bytes(raw)

        def omitted(*args: str) -> bytes:
            result = run(*args)
            return b"" if "ls-tree" in args else result

        primitives._run_fixed_git_v42r1 = omitted
        with pytest.raises(
            launcher.V42ProductionLauncherError,
            match="omitted an exact launcher TCB source",
        ):
            launcher._verified_tcb(  # noqa: SLF001
                repo=pin, source=source, transport=transport,
                primitives=primitives,
            )
    finally:
        pin.close()


def _subprocess_import_check(tmp_path: Path, operation: str, *, extra: bool) -> None:
    script = tmp_path / ("check_" + operation + ".py")
    sentinel = tmp_path / "EXTRA_MANIFESTED_EXECUTED"
    extra_code = ""
    if extra:
        extra_code = "\n    import acfqp.extra_manifested"
    code = f"""
import importlib.util
from pathlib import Path
import sys
from types import MappingProxyType
p=Path({str(launcher.SCRIPT_PATH)!r})
spec=importlib.util.spec_from_file_location('_launcher_check',p)
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
sys.modules.pop(spec.name)
repo=module._DirectoryPin.open(module.ROOT,'repository root')
primitive=module._load_frozen_primitives(repo)
raws={{}}
for base in ('scripts','src/acfqp'):
    for source in (module.ROOT/base).rglob('*.py'):
        raws[source.relative_to(module.ROOT).as_posix()]=source.read_bytes()
if {extra!r}:
    raws['src/acfqp/extra_manifested.py']=(
        "from pathlib import Path\\nPath(" + {str(sentinel)!r}.__repr__()
        + ").write_text('x')\\n"
    ).encode('utf-8')
finder=module._VerifiedFinder(MappingProxyType(raws),repo,operation={operation!r})
sys.meta_path.insert(0,finder)
before=tuple(sys.path)
try:
    driver=__import__(module._driver_name({operation!r}),fromlist=['*']){extra_code}
except ImportError as error:
    if not {extra!r} or 'unexpected repository module rejected' not in str(error):
        raise
    driver=None
sys.path[:]=list(before)
if not {extra!r}:
    finder.verify(operation={operation!r})
assert primitive.__acfqp_exec_count__ == 1
assert '_acfqp_v42_frozen_preformal_launcher_primitives' not in sys.modules
assert not Path({str(sentinel)!r}).exists()
print('OK')
"""
    script.write_text(code, encoding="utf-8")
    observed = subprocess.run(
        ["/usr/bin/python3", "-B", str(script)],
        cwd=launcher.ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert observed.returncode == 0, observed.stderr.decode(errors="replace")
    assert observed.stdout == b"OK\n"
    assert not sentinel.exists()


@pytest.mark.parametrize("operation", ["activation", "formal"])
def test_frozen_primitives_then_driver_use_exact_source_only_inventory(
    tmp_path: Path, operation: str,
) -> None:
    _subprocess_import_check(tmp_path, operation, extra=False)


def test_extra_manifested_repository_import_is_rejected(tmp_path: Path) -> None:
    _subprocess_import_check(tmp_path, "activation", extra=True)


def test_verified_source_loader_ignores_repo_pyc_and_rejects_stdlib_shadow(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    package = root / "src/acfqp"
    package.mkdir(parents=True)
    os.chmod(root, 0o700)
    sentinel = tmp_path / "REPO_PYC_EXECUTED"
    malicious = package / "victim.py"
    malicious.write_text(
        "from pathlib import Path\nPath(" + repr(str(sentinel)) + ").write_text('x')\n",
        encoding="utf-8",
    )
    _compile_legacy_pyc(malicious, package / "victim.pyc")
    stdlib_source = root / "fractions.py"
    stdlib_source.write_text(
        "from pathlib import Path\nPath(" + repr(str(sentinel)) + ").write_text('y')\n",
        encoding="utf-8",
    )
    _compile_legacy_pyc(stdlib_source, root / "fractions.pyc")
    child = tmp_path / "finder_check.py"
    child.write_text(
        f"""
import importlib.util
from pathlib import Path
from types import MappingProxyType
import sys
p=Path({str(launcher.SCRIPT_PATH)!r})
s=importlib.util.spec_from_file_location('_finder_launcher',p)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
pin=m._DirectoryPin.open(Path({str(root)!r}),'fake repo')
raws=MappingProxyType({{
 'src/acfqp/__init__.py': b'',
 'src/acfqp/victim.py': b'VALUE = 7\\n',
}})
m.EXPECTED_MODULES_BY_OPERATION=MappingProxyType({{
 'activation': MappingProxyType({{
   'acfqp': 'src/acfqp/__init__.py',
   'acfqp.victim': 'src/acfqp/victim.py',
 }}),
}})
finder=m._VerifiedFinder(raws,pin,operation='activation');sys.meta_path.insert(0,finder)
import acfqp.victim as victim
assert victim.VALUE == 7
try:
 import fractions
except ImportError as error:
 assert 'stdlib shadow rejected' in str(error)
else:
 raise RuntimeError('stdlib shadow imported')
assert not Path({str(sentinel)!r}).exists()
print('OK')
""",
        encoding="utf-8",
    )
    observed = subprocess.run(
        ["/usr/bin/python3", "-B", str(child)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    assert observed.returncode == 0, observed.stderr.decode(errors="replace")
    assert observed.stdout == b"OK\n"
    assert not sentinel.exists()


def test_driver_main_has_one_callsite_and_is_called_once_with_exact_list() -> None:
    observed: list[list[str]] = []

    def effect(argv: list[str]) -> int:
        observed.append(argv)
        return 7

    driver = SimpleNamespace(main=effect)
    args = ("--activation-evidence-root", "/tmp/a", "--prepare-once")
    assert launcher._invoke_driver_once(driver, args) == 7  # noqa: SLF001
    assert observed == [list(args)]

    tree = ast.parse(launcher.SCRIPT_PATH.read_bytes())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "main"
    ]
    assert len(calls) == 1


def test_invalid_driver_status_is_rejected_after_single_call() -> None:
    count = 0

    def effect(_argv: list[str]) -> bool:
        nonlocal count
        count += 1
        return True

    with pytest.raises(
        launcher.V42ProductionLauncherError, match="invalid process status"
    ):
        launcher._invoke_driver_once(SimpleNamespace(main=effect), ())  # noqa: SLF001
    assert count == 1
