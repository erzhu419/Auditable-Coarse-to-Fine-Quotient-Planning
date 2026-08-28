from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts/bootstrap_v42_formal_transport_recovery_v42r3r4.py"
STAGE_ONE = ROOT / "scripts/launch_v42_formal_transport_recovery_v42r3r4.py"
ENVIRONMENT = {
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PATH": "/usr/bin:/bin",
}


def _constants() -> dict[str, object]:
    tree = ast.parse(BOOTSTRAP.read_text(encoding="utf-8"))
    result: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in {
            "STAGE_ONE_SHA256", "STAGE_ONE_BYTE_COUNT",
        }:
            result[target.id] = ast.literal_eval(node.value)
    return result


def _run(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/usr/bin/python3", "-I", "-S", "-B", str(path), *arguments],
        cwd=ROOT,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def test_recovery_bootstrap_is_stdlib_only_and_effect_free() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert all(
        name not in {"acfqp", "scripts"}
        and not name.startswith(("acfqp.", "scripts."))
        for name in imports
    )
    assert "subprocess" not in imports
    assert "socket" not in imports
    assert "systemctl" not in source
    assert "ssh" not in source.lower()


def test_recovery_bootstrap_pins_exact_stage_one_bytes() -> None:
    raw = STAGE_ONE.read_bytes()
    assert _constants() == {
        "STAGE_ONE_SHA256": hashlib.sha256(raw).hexdigest(),
        "STAGE_ONE_BYTE_COUNT": len(raw),
    }


def test_recovery_bootstrap_rejects_direct_unsealed_entry() -> None:
    result = _run(BOOTSTRAP, "--help")
    assert result.returncode != 0
    assert "external sealed invoker" in result.stderr


def test_recovery_launcher_rejects_direct_unsealed_entry() -> None:
    result = _run(STAGE_ONE, "--help")
    assert result.returncode != 0
    assert "did not enter through pinned bootstrap" in result.stderr
