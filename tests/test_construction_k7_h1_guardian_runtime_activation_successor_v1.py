from __future__ import annotations

import ast
import dis
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

from acfqp import construction_k7_h1_guardian_runtime_activation_successor_v1 as successor


def test_surface_is_compile_time_blocked_scaffold_only() -> None:
    surface = successor.verify_h1_guardian_runtime_activation_successor_surface_v1()
    assert surface["readiness"] == (
        "COMPILE_TIME_BLOCKED_SCAFFOLD_NO_SUCCESSOR_ISSUANCE"
    )
    assert len(surface["source_closure"]) == 2
    assert surface["scaffold_only"] is True
    assert surface["schema_names_reserved_only"] is True
    assert surface["consumer_evidence_schema_scaffold_present"] is True
    assert surface["activation_successor_schema_scaffold_present"] is True
    assert surface["issuance_code_present"] is False
    assert surface["durable_successor_journal_code_present"] is False
    assert surface["fresh_v20_consumer_evidence_present"] is False
    assert surface["fresh_v20_activation_successor_present"] is False
    assert surface["durable_successor_artifact_present"] is False
    assert surface["v19_public_capsule_binding_seam_available"] is False
    assert surface["public_successor_issuance_reachable"] is False
    assert surface["blocked_before_argument_validation"] is True
    assert surface["blocked_before_predecessor_call"] is True
    assert surface["blocked_before_path_resolution"] is True
    assert surface["blocked_before_authority_object_creation"] is True
    assert surface["blocked_before_successor_object_creation"] is True
    assert surface["blocked_before_journal_open"] is True
    assert surface["blocked_before_native_edge"] is True
    assert surface["permit_consumption_path_present"] is False
    assert surface["clone_syscall_performed"] is False
    assert surface["actual_process_birth_present"] is False
    assert surface["formal_v7_authority_present"] is False
    assert surface["official_execution_allowed"] is False
    observation = surface["v19_public_capsule_binding_seam_observation"]
    assert observation["authoritative"] is False
    assert tuple(observation["required_names"]) == (
        "prepare_lease_bound_three_birth_prebound_clone_v1",
        "verify_lease_bound_three_birth_prebound_clone_binding_v1",
        "cancel_lease_bound_three_birth_prebound_clone_v1",
    )
    assert all(row["observation_is_diagnostic_only"] for row in observation["rows"])


def test_prepare_unconditionally_fails_before_path_or_objects(tmp_path: Path) -> None:
    absent_journal = tmp_path / "must-not-be-created"
    with pytest.raises(
        successor.ConstructionK7H1GuardianRuntimeActivationSuccessorV1Error,
        match="compile-time blocked",
    ):
        successor.prepare_h1_guardian_runtime_activation_successor_v1(
            guardian_takeover=object(),
            launch_preparation=object(),
            prebound_capsule=object(),
            journal_path=absent_journal,
        )
    assert not absent_journal.exists()
    assert list(tmp_path.iterdir()) == []
    assert not any(name.startswith("_LIVE") for name in vars(successor))


def test_blocked_prepare_bytecode_has_no_dynamic_or_external_lookup() -> None:
    instructions = tuple(
        dis.get_instructions(
            successor.prepare_h1_guardian_runtime_activation_successor_v1
        )
    )
    assert "LOAD_GLOBAL" not in {instruction.opname for instruction in instructions}
    assert "LOAD_ATTR" not in {instruction.opname for instruction in instructions}
    assert "LOAD_METHOD" not in {instruction.opname for instruction in instructions}
    assert "IMPORT_NAME" not in {instruction.opname for instruction in instructions}
    assert instructions[-1].opname == "RAISE_VARARGS"


def test_module_exports_no_positive_handle_journal_or_terminal_surface() -> None:
    exports = set(successor.__all__)
    assert "prepare_h1_guardian_runtime_activation_successor_v1" in exports
    assert "verify_h1_guardian_runtime_activation_successor_surface_v1" in exports
    assert not any("cancel" in name.lower() for name in exports)
    assert not any("closure" in name.lower() for name in exports)
    assert not any("evidence_v2" in name.lower() for name in exports)
    assert not any(name.startswith("H1GuardianRuntime") for name in exports)
    assert not hasattr(successor, "H1GuardianRuntimeConsumerEvidenceV2")
    assert not hasattr(successor, "H1GuardianRuntimeActivationSuccessorV1")
    assert not hasattr(successor, "H1GuardianRuntimeActivationSuccessorClosureV1")


def test_module_imports_no_guardian_prebound_native_or_private_runtime() -> None:
    source = Path(successor.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("guardian_runtime_genesis" in name for name in imports)
    assert not any("supervisor_v2_prebound_clone" in name for name in imports)
    assert not any("actual_observed_supervisor_birth" in name for name in imports)
    assert "_LIVE" not in source
    assert "_append_exclusive" not in source
    assert "register_at_fork" not in source


def test_post_import_fake_seam_and_rebaseline_inputs_cannot_unlock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    launch = successor.launch_v19
    error_type = successor.ConstructionK7H1GuardianRuntimeActivationSuccessorV1Error

    def fake_seam(*_args, **_kwargs):
        raise AssertionError("fake V19 seam was invoked")

    for name in successor.REQUIRED_V19_CAPSULE_BINDING_SEAM:
        module_owned = types.FunctionType(fake_seam.__code__, launch.__dict__, name)
        monkeypatch.setattr(launch, name, module_owned, raising=False)
    monkeypatch.setattr(
        launch,
        "__all__",
        tuple(
            dict.fromkeys(
                (*getattr(launch, "__all__", ()), *successor.REQUIRED_V19_CAPSULE_BINDING_SEAM)
            )
        ),
    )
    monkeypatch.setattr(successor, "launch_v19", object())
    monkeypatch.setattr(successor, "REQUIRED_V19_CAPSULE_BINDING_SEAM", ())
    monkeypatch.setattr(
        successor,
        "ConstructionK7H1GuardianRuntimeActivationSuccessorV1Error",
        AssertionError,
    )
    assert not hasattr(successor, "_freeze_local_callable_closure")
    assert not hasattr(successor, "_UPSTREAM_CALLABLES")
    assert not hasattr(successor, "_EXPECTED_TYPES")

    surface = successor.verify_h1_guardian_runtime_activation_successor_surface_v1()
    observation = surface["v19_public_capsule_binding_seam_observation"]
    assert observation["observed_complete"] is True
    assert observation["authoritative"] is False
    assert len(observation["required_names"]) == 3
    assert surface["v19_public_capsule_binding_seam_available"] is False
    assert surface["public_successor_issuance_reachable"] is False

    absent_journal = tmp_path / "post-import-attack"
    with pytest.raises(error_type, match="compile-time blocked"):
        successor.prepare_h1_guardian_runtime_activation_successor_v1(
            guardian_takeover=object(),
            launch_preparation=object(),
            prebound_capsule=object(),
            journal_path=absent_journal,
        )
    assert not absent_journal.exists()


def test_pre_import_module_owned_fake_public_seam_cannot_unlock() -> None:
    code = r'''
import json
from pathlib import Path
import sys
import tempfile

from acfqp import construction_k7_h1_lease_bound_three_birth_runtime_v1 as launch

module_name = "acfqp.construction_k7_h1_guardian_runtime_activation_successor_v1"
assert module_name not in sys.modules
exec("""
def prepare_lease_bound_three_birth_prebound_clone_v1(*args, **kwargs):
    raise AssertionError('pre-import fake prepare was invoked')
def verify_lease_bound_three_birth_prebound_clone_binding_v1(*args, **kwargs):
    raise AssertionError('pre-import fake verify was invoked')
def cancel_lease_bound_three_birth_prebound_clone_v1(*args, **kwargs):
    raise AssertionError('pre-import fake cancel was invoked')
""", launch.__dict__)
required = (
    "prepare_lease_bound_three_birth_prebound_clone_v1",
    "verify_lease_bound_three_birth_prebound_clone_binding_v1",
    "cancel_lease_bound_three_birth_prebound_clone_v1",
)
launch.__all__ = tuple(dict.fromkeys((*getattr(launch, "__all__", ()), *required)))

from acfqp import construction_k7_h1_guardian_runtime_activation_successor_v1 as blocked

with tempfile.TemporaryDirectory(prefix="acfqp-v20-blocked-") as root:
    journal = Path(root) / "must-not-exist"
    rejected = False
    try:
        blocked.prepare_h1_guardian_runtime_activation_successor_v1(
            guardian_takeover=object(),
            launch_preparation=object(),
            prebound_capsule=object(),
            journal_path=journal,
        )
    except blocked.ConstructionK7H1GuardianRuntimeActivationSuccessorV1Error:
        rejected = True
    surface = blocked.verify_h1_guardian_runtime_activation_successor_surface_v1()
    print(json.dumps({
        "observed_complete": surface[
            "v19_public_capsule_binding_seam_observation"
        ]["observed_complete"],
        "available": surface["v19_public_capsule_binding_seam_available"],
        "reachable": surface["public_successor_issuance_reachable"],
        "rejected": rejected,
        "journal_exists": journal.exists(),
        "clone": surface["clone_syscall_performed"],
        "birth": surface["actual_process_birth_present"],
    }, sort_keys=True))
'''
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result == {
        "available": False,
        "birth": False,
        "clone": False,
        "journal_exists": False,
        "observed_complete": True,
        "reachable": False,
        "rejected": True,
    }
