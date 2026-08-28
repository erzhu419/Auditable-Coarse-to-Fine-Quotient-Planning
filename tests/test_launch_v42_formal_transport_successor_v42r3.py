from __future__ import annotations

import ast
import importlib
from pathlib import Path
import hashlib
import json
import shlex
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import launch_v42_activation_successor_or_formal as predecessor
from scripts import launch_v42_formal_transport_successor_v42r3 as launcher


@pytest.fixture(autouse=True)
def _explicit_imported_test_harness_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pure/unit tests explicitly stand in for verified sealed materials."""

    monkeypatch.setattr(launcher, "_EARLY_SEALED_MATERIALS_VERIFIED", True)
    monkeypatch.setattr(launcher, "_AUTHENTICATED_STAGE_SELF_RAW", b"test-stage1")
    monkeypatch.setattr(launcher, "_AUTHENTICATED_BOOTSTRAP_RAW", b"test-stage0")


def test_effect_capable_launcher_rejects_missing_sealed_materials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(launcher, "_EARLY_SEALED_MATERIALS_VERIFIED", False)
    with pytest.raises(
        launcher.V42FormalTransportSuccessorLauncherError,
        match="lacks verified sealed materials",
    ):
        launcher._require_sealed_stage_materials()  # noqa: SLF001


def test_coherent_git_anchor_query_accepts_exact_commit_and_tree() -> None:
    expected_commit = subprocess.run(
        [launcher.GIT, "-C", str(launcher.ROOT), "rev-parse", "HEAD^{commit}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.decode("ascii").strip()
    expected_tree = subprocess.run(
        [launcher.GIT, "-C", str(launcher.ROOT), "rev-parse", "HEAD^{tree}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.decode("ascii").strip()
    assert launcher._coherent_git_anchors(expected_commit) == (  # noqa: SLF001
        expected_commit,
        expected_tree,
    )


def test_controller_tcb_is_exact_predecessor_plus_six_native_paths() -> None:
    assert launcher.CONTROLLER_TCB_PATHS == (
        "scripts/__init__.py",
        "scripts/bootstrap_v42_formal_transport_successor_v42r3.py",
        "scripts/launch_v42_activation_successor_or_formal.py",
        "scripts/launch_v42_formal_transport_successor_v42r3.py",
        "scripts/launch_v42_preformal_upload_sender.py",
        "scripts/publish_v42_preformal_upload_journal.py",
        "scripts/run_v42_activation_successor_finalizer.py",
        "scripts/run_v42_materialization_activation.py",
        "scripts/run_v42_preformal_upload_sender.py",
        "scripts/run_v42_standard_2048_formal_transport_driver.py",
        "scripts/run_v42_standard_2048_formal_transport_native_successor_driver.py",
        "scripts/run_v42_standard_2048_formal_transport_successor_driver.py",
        "scripts/run_v42_standard_2048_remote_ordinal2.py",
        "scripts/v42_activation_successor_loader.py",
        "scripts/v42_activation_successor_receiver.py",
        "scripts/v42_standard_2048_formal_transport_loader_v42r3.py",
        "scripts/v42_standard_2048_formal_transport_receiver_v42r3.py",
        "src/acfqp/__init__.py",
        "src/acfqp/artifacts.py",
        "src/acfqp/build_coverage.py",
        "src/acfqp/construction_k7_domain_registry_extension_v42.py",
        "src/acfqp/construction_k7_standard_2048_activation_successor_v42r2.py",
        "src/acfqp/construction_k7_standard_2048_formal_transport_successor_v42r3.py",
        "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
        "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
        "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
        "src/acfqp/core.py",
        "src/acfqp/enumeration.py",
        "src/acfqp/phase3e_ids.py",
    )
    assert len(launcher.CONTROLLER_TCB_PATHS) == 33
    assert len(set(launcher.CONTROLLER_TCB_PATHS)) == 33
    assert launcher.PREDECESSOR_TCB_PATHS == predecessor.TCB_PATHS


def test_native_launcher_never_routes_through_v42r1_formal_core() -> None:
    source = Path(launcher.__file__).read_text(encoding="utf-8")
    assert source.startswith("from __future__ import annotations\n")
    assert "/bin/sh" not in source
    assert "from scripts import run_v42_standard_2048_formal_transport_driver" not in source
    assert "build_production_activation_core_v42r1(" not in source
    assert "verify_production_activation_core_v42r1(" not in source
    assert "execute_prepare_once_v42r1" not in source
    assert "execute_launch_admission_once_v42r1" not in source


def test_launcher_imports_no_project_module_before_source_authentication() -> None:
    tree = ast.parse(Path(launcher.__file__).read_text(encoding="utf-8"))
    project_imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            project_imports.extend(
                alias.name for alias in node.names
                if alias.name in {"scripts", "acfqp"}
                or alias.name.startswith(("scripts.", "acfqp."))
            )
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module in {"scripts", "acfqp"} or node.module.startswith(
                ("scripts.", "acfqp.")
            ):
                project_imports.append(node.module)
    assert project_imports == []


def test_verified_importer_executes_cached_bytes_without_reading_named_source() -> None:
    name = "scripts.acfqp_v42r3_cached_source_test"
    relative = "scripts/acfqp_v42r3_cached_source_test.py"
    finder = launcher._VerifiedSourceFinder(  # noqa: SLF001
        {relative: b"VALUE = 'authenticated-cache'\n"}
    )
    sys.meta_path.insert(0, finder)
    try:
        module = importlib.import_module(name)
        assert module.VALUE == "authenticated-cache"
        assert not (launcher.ROOT / relative).exists()
        finder.verify_loaded()
    finally:
        sys.meta_path.remove(finder)
        sys.modules.pop(name, None)


def test_successor_journal_roots_are_new_and_versioned() -> None:
    assert str(launcher.LOCAL_JOURNAL_ROOT).endswith(
        ".acfqp-v42-local-formal-transport-ordinal2-v42r3"
    )
    assert launcher.REMOTE_JOURNAL_ROOT.endswith(
        ".acfqp-v42-remote-ordinal2-formal-transport-v42r3"
    )
    assert "-v42r3" in launcher.LOCAL_JOURNAL_ROOT.name
    assert "-v42r3" in launcher.REMOTE_JOURNAL_ROOT


def test_input_summary_explicitly_denies_effects() -> None:
    class _Successor:
        ids = {launcher.SUCCESSOR_FINAL_FILE: "c" * 64}

    class _Verified:
        successor = _Successor()
        predecessor_formal_prefix = {
            "predecessor_formal_effect_may_have_started": False
        }

    summary = launcher._summary(  # noqa: SLF001
        {"controller_source_manifest_id": "a" * 64},
        _Verified(),  # type: ignore[arg-type]
        {"native_activation_binding_id": "b" * 64},
    )
    assert summary["network_operation_performed"] is False
    assert summary["local_journal_mutated"] is False
    assert summary["formal_admission_claim_scope"] == (
        "CONDITIONAL_ON_UNATTESTED_EXTERNAL_LOCAL_SSH_AND_REMOTE_PATH_TCB"
    )
    assert summary["external_ingress_assumptions_observed_or_attested"] is False
    assert summary["remote_path_noninterference_observed_or_attested"] is False
    assert summary["predecessor_formal_effect_may_have_started"] is False


def test_local_journal_is_one_shot_anchored_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    launcher._ensure_journal_root()  # noqa: SLF001
    anchor = tmp_path / ("." + root.name + ".ROOT_IDENTITY.json")
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(anchor.stat().st_mode) == 0o400

    launcher._publish_or_verify("ONE.json", b"{}")  # noqa: SLF001
    assert (root / "ONE.json").read_bytes() == b"{}"
    assert stat.S_IMODE((root / "ONE.json").stat().st_mode) == 0o400
    launcher._publish_or_verify("ONE.json", b"{}")  # noqa: SLF001
    with pytest.raises(launcher.V42FormalTransportSuccessorLauncherError):
        launcher._publish_or_verify("ONE.json", b'{"changed":true}')  # noqa: SLF001


def test_parent_effect_cut_precedes_and_is_distinct_from_inner_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    launcher._ensure_journal_root()  # noqa: SLF001
    raw = b'{"effect_may_have_started":true}'
    pin = launcher._JournalPin.open()  # noqa: SLF001
    try:
        cut_name = launcher._anchor_name(  # noqa: SLF001
            "NETWORK_START.PREPARE." + "a" * 64 + ".json"
        )
        cut_state = pin.publish_parent_anchor(cut_name, raw)
        marker_state = pin.publish("FORMAL_PREPARE_NETWORK_START.json", raw)
        pin.verify_parent_anchor(cut_name, cut_state)
        pin.verify_artifact("FORMAL_PREPARE_NETWORK_START.json", marker_state)
    finally:
        pin.close()
    assert (tmp_path / cut_name).read_bytes() == raw
    assert (root / "FORMAL_PREPARE_NETWORK_START.json").read_bytes() == raw


def test_python312_remote_command_has_exact_loader_argv_layout() -> None:
    raws = tuple(
        value.encode("ascii")
        for value in ("loader", "controller", "authority", "receiver", "ingress")
    )
    command = launcher._loader_remote_command_v42r3(  # noqa: SLF001
        mode=launcher.PROBE_MODE,
        loader_raw=raws[0],
        controller_raw=raws[1],
        authority_raw=raws[2],
        receiver_raw=raws[3],
        ingress_raw=raws[4],
        expected_plan_id="a" * 64,
        legacy_execution_source_manifest_id="b" * 64,
    )
    arguments = shlex.split(command.removeprefix("builtin exec -c "))
    assert arguments[:7] == [
        "/usr/bin/python3", "-I", "-S", "-B", "-c", "loader",
        launcher.PROBE_MODE,
    ]
    cursor = 7
    for raw in raws:
        assert arguments[cursor : cursor + 2] == [
            hashlib.sha256(raw).hexdigest(), str(len(raw))
        ]
        cursor += 2
    assert arguments[cursor:] == ["a" * 64, "b" * 64]
    assert len(arguments) == 19


def test_ssh_argv_is_pinned_and_forbids_interactive_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    command = "builtin exec -c /usr/bin/python3 -I -S -B -c pass"
    argv = launcher._ssh_argv_v42r3(  # noqa: SLF001
        known_hosts_path=str(root / launcher.KNOWN_HOSTS_NAME),
        remote_command=command,
    )
    assert argv[0] == "/usr/bin/ssh"
    assert "-oBatchMode=yes" in argv
    assert "-oStrictHostKeyChecking=yes" in argv
    assert "-oPasswordAuthentication=no" in argv
    assert "-oKbdInteractiveAuthentication=no" in argv
    assert "-oProxyCommand=none" in argv
    assert argv[-1] == command


def test_read_only_dispatch_rejects_effect_mode_before_loading_runtime() -> None:
    raws = tuple(value.encode("ascii") for value in ("l", "c", "a", "r", "i"))
    mode = "--prepare-once-v42r3"
    command = launcher._loader_remote_command_v42r3(  # noqa: SLF001
        mode=mode,
        loader_raw=raws[0],
        controller_raw=raws[1],
        authority_raw=raws[2],
        receiver_raw=raws[3],
        ingress_raw=raws[4],
        expected_plan_id="a" * 64,
        legacy_execution_source_manifest_id="b" * 64,
    )
    transport = launcher._TransportMaterialization(  # noqa: SLF001
        mode=mode,
        argv=("ssh", command),
        frame=b"effect-frame",
        remote_command_sha256=hashlib.sha256(command.encode()).hexdigest(),
        expected_plan_id="a" * 64,
        legacy_execution_source_manifest_id="b" * 64,
    )
    with pytest.raises(
        launcher.V42FormalTransportSuccessorLauncherError,
        match="read-only dispatch authorization",
    ):
        launcher._dispatch_read_only_v42r3(  # noqa: SLF001
            transport=transport, stdout_cap=1024
        )


def test_probe_journal_prefix_publishes_pinned_known_hosts_before_dispatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    monkeypatch.setattr(
        launcher,
        "_verified_module",
        lambda name: SimpleNamespace(PINNED_KNOWN_HOSTS_BYTES=b"host key\n")
        if name == launcher.PREFORMAL_MODULE
        else (_ for _ in ()).throw(AssertionError(name)),
    )
    controller = {"controller_source_manifest_id": "a" * 64}
    binding = {"native_activation_binding_id": "b" * 64}
    probe = {"formal_host_epoch_probe_plan_id": "c" * 64}
    launcher._initialize_probe_journal_v42r3(  # noqa: SLF001
        controller_manifest=controller,
        native_activation_binding=binding,
        probe_plan=probe,
    )
    assert (root / launcher.KNOWN_HOSTS_NAME).read_bytes() == b"host key\n"
    assert stat.S_IMODE((root / launcher.KNOWN_HOSTS_NAME).stat().st_mode) == 0o400
    assert sorted(path.name for path in root.iterdir()) == sorted(
        {
            launcher.KNOWN_HOSTS_NAME,
            launcher.CONTROLLER_MANIFEST_NAME,
            launcher.NATIVE_BINDING_NAME,
            launcher.HOST_PROBE_PLAN_NAME,
        }
    )


def test_effect_dispatch_publishes_parent_cut_then_marker_before_spawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    launcher._ensure_journal_root()  # noqa: SLF001
    prefix = {"predecessor_formal_effect_may_have_started": False}
    attempt_id = "d" * 64
    plan_id = "f" * 64
    plan = {"formal_transport_plan_id": plan_id}
    controller = {"controller_source_manifest_id": "c" * 64}
    ingress = {
        "formal_prepare_attempt": {
            "formal_prepare_attempt_id": attempt_id,
        }
    }
    marker = {
        "attempt_id": attempt_id,
        "formal_transport_plan_id": plan_id,
        "operation": "PREPARE",
    }
    marker_raw = launcher._canonical_json_bytes(marker)  # noqa: SLF001
    expected_cut = tmp_path / launcher._anchor_name(  # noqa: SLF001
        "NETWORK_START.PREPARE." + attempt_id + ".json"
    )
    launcher._publish_once(  # noqa: SLF001
        launcher.KNOWN_HOSTS_NAME, b"host key\n"
    )

    class _Pins:
        ssh = SimpleNamespace(descriptor=9)

        def verify(self) -> None:
            pass

        def close(self) -> None:
            pass

    pins = _Pins()

    class _Guard:
        def verify(self) -> None:
            pass

        def close(self) -> None:
            pass

    observation = object()
    spawn_count = 0

    class _Prepared:
        def verify_prepared(self) -> None:
            pass

        def spawn_and_pump(self):
            nonlocal spawn_count
            spawn_count += 1
            assert expected_cut.read_bytes() == marker_raw
            assert (
                root / launcher.LOCAL_PREPARE_NETWORK_START_NAME
            ).read_bytes() == marker_raw
            return observation

        def close(self) -> None:
            pass

    native = SimpleNamespace(
        verify_failed_v42r1_formal_prefix_read_only=lambda: dict(prefix)
    )
    formal = SimpleNamespace(
        verify_formal_transport_plan_v42r3=lambda value: dict(value),
        verify_network_start_v42r3=(
            lambda raw, **_kwargs: json.loads(raw.decode("utf-8"))
        ),
    )
    preformal = SimpleNamespace(PINNED_KNOWN_HOSTS_BYTES=b"host key\n")
    sender = SimpleNamespace(
        _open_local_dispatch_pins_v42r1=lambda _plan: pins,
        _derive_identity_fingerprint_v42r1=lambda **_kwargs: "fingerprint",
        _SigpipeIgnoreGuard=SimpleNamespace(acquire=lambda: _Guard()),
    )
    monkeypatch.setattr(
        launcher,
        "_verified_module",
        lambda name: {
            launcher.NATIVE_DRIVER_MODULE: native,
            launcher.PREFORMAL_MODULE: preformal,
            launcher.SENDER_MODULE: sender,
        }[name],
    )
    monkeypatch.setattr(launcher, "_authority", lambda: formal)
    monkeypatch.setattr(
        launcher,
        "_ssh_pin_plan",
        lambda: {"ssh_client_contract": {"identity_public_fingerprint": "fingerprint"}},
    )
    monkeypatch.setattr(launcher, "_prepare_pinned_child", lambda **_kwargs: _Prepared())
    monkeypatch.setattr(
        launcher,
        "_ssh_execution_argv_v42r3",
        lambda *, transport, known_hosts: transport.argv,
    )
    verified_contexts: list[tuple[object, object, object]] = []

    def _verify_transport(
        value: object, *, controller_manifest: object, ingress: object,
    ) -> None:
        verified_contexts.append((value, controller_manifest, ingress))

    monkeypatch.setattr(launcher, "_verify_transport_materialization", _verify_transport)
    transport = launcher._TransportMaterialization(  # noqa: SLF001
        mode="--prepare-once-v42r3",
        argv=("ssh", "command"),
        frame=b"frame",
        remote_command_sha256="e" * 64,
        expected_plan_id=plan_id,
        legacy_execution_source_manifest_id="a" * 64,
    )
    observed, marker, failure = launcher._dispatch_effect_once_v42r3(  # noqa: SLF001
        operation="PREPARE",
        attempt_id=attempt_id,
        transport=transport,
        controller_manifest=controller,
        ingress=ingress,
        formal_transport_plan=plan,
        marker_name=launcher.LOCAL_PREPARE_NETWORK_START_NAME,
        marker_raw=marker_raw,
        expected_predecessor_formal_prefix=prefix,
        stdout_cap=1024,
        timeout_seconds=120.0,
    )
    assert observed is observation
    assert marker is True
    assert failure is None
    assert spawn_count == 1
    assert verified_contexts == [
        (transport, controller, ingress),
        (transport, controller, ingress),
    ]
    with pytest.raises(
        launcher.V42FormalTransportSuccessorLauncherError,
        match="same identity replay",
    ):
        launcher._dispatch_effect_once_v42r3(  # noqa: SLF001
            operation="PREPARE",
            attempt_id=attempt_id,
            transport=transport,
            controller_manifest=controller,
            ingress=ingress,
            formal_transport_plan=plan,
            marker_name=launcher.LOCAL_PREPARE_NETWORK_START_NAME,
            marker_raw=marker_raw,
            expected_predecessor_formal_prefix=prefix,
            stdout_cap=1024,
            timeout_seconds=120.0,
        )
    assert spawn_count == 1


def test_read_only_dispatch_reaches_exactly_one_spawn_after_pinned_setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    launcher._ensure_journal_root()  # noqa: SLF001
    launcher._publish_once(  # noqa: SLF001
        launcher.KNOWN_HOSTS_NAME, b"host key\n"
    )
    controller = {"controller_source_manifest_id": "a" * 64}
    ingress = {"formal_host_epoch_probe_plan_id": "b" * 64}
    transport = launcher._TransportMaterialization(  # noqa: SLF001
        mode=launcher.PROBE_MODE,
        argv=("ssh", "command"),
        frame=b"read-only-frame",
        remote_command_sha256="c" * 64,
        expected_plan_id="b" * 64,
        legacy_execution_source_manifest_id="d" * 64,
    )
    events: list[str] = []

    class _Pins:
        ssh = SimpleNamespace(descriptor=7)

        def verify(self) -> None:
            events.append("pins.verify")

        def close(self) -> None:
            events.append("pins.close")

    class _Prepared:
        def spawn_and_pump(self) -> object:
            events.append("spawn")
            return SimpleNamespace(stdout_raw=b"receipt\n")

        def close(self) -> None:
            events.append("prepared.close")

    pins = _Pins()
    sender = SimpleNamespace(
        _open_local_dispatch_pins_v42r1=lambda _plan: pins,
        _derive_identity_fingerprint_v42r1=lambda **_kwargs: "fingerprint",
    )
    preformal = SimpleNamespace(PINNED_KNOWN_HOSTS_BYTES=b"host key\n")

    def _module(name: str) -> object:
        return {
            launcher.SENDER_MODULE: sender,
            launcher.PREFORMAL_MODULE: preformal,
        }[name]

    monkeypatch.setattr(launcher, "_verified_module", _module)
    monkeypatch.setattr(
        launcher,
        "_ssh_pin_plan",
        lambda: {
            "ssh_client_contract": {
                "identity_public_fingerprint": "fingerprint",
            }
        },
    )
    monkeypatch.setattr(
        launcher,
        "_verify_transport_materialization",
        lambda value, *, controller_manifest, ingress: events.append(
            "transport.verify"
        ),
    )
    monkeypatch.setattr(
        launcher,
        "_ssh_execution_argv_v42r3",
        lambda *, transport, known_hosts: transport.argv,
    )
    monkeypatch.setattr(
        launcher, "_prepare_pinned_child", lambda **_kwargs: _Prepared()
    )

    observation = launcher._dispatch_read_only_v42r3(  # noqa: SLF001
        transport=transport,
        controller_manifest=controller,
        ingress=ingress,
        stdout_cap=1024,
    )
    assert observation.stdout_raw == b"receipt\n"
    assert events.count("spawn") == 1
    assert events[0] == "transport.verify"
    assert events.index("spawn") < events.index("prepared.close")


@pytest.mark.parametrize("known_hosts_state", ["missing", "corrupt"])
def test_effect_known_hosts_failure_leaves_no_cut_or_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, known_hosts_state: str,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    launcher._ensure_journal_root()  # noqa: SLF001
    if known_hosts_state == "corrupt":
        launcher._publish_once(  # noqa: SLF001
            launcher.KNOWN_HOSTS_NAME, b"wrong host key\n"
        )
    prefix = {"predecessor_formal_effect_may_have_started": False}
    attempt_id = "d" * 64
    plan_id = "e" * 64
    controller = {"controller_source_manifest_id": "c" * 64}
    ingress = {
        "formal_prepare_attempt": {
            "formal_prepare_attempt_id": attempt_id,
        }
    }
    plan = {"formal_transport_plan_id": plan_id}
    marker_raw = launcher._canonical_json_bytes(  # noqa: SLF001
        {
            "attempt_id": attempt_id,
            "formal_transport_plan_id": plan_id,
            "operation": "PREPARE",
        }
    )
    formal = SimpleNamespace(
        verify_formal_transport_plan_v42r3=lambda value: dict(value),
        verify_network_start_v42r3=(
            lambda raw, **_kwargs: json.loads(raw.decode("utf-8"))
        ),
    )
    native = SimpleNamespace(
        verify_failed_v42r1_formal_prefix_read_only=lambda: dict(prefix)
    )
    preformal = SimpleNamespace(PINNED_KNOWN_HOSTS_BYTES=b"host key\n")
    monkeypatch.setattr(launcher, "_authority", lambda: formal)
    monkeypatch.setattr(
        launcher,
        "_verified_module",
        lambda name: {
            launcher.NATIVE_DRIVER_MODULE: native,
            launcher.PREFORMAL_MODULE: preformal,
        }[name],
    )
    monkeypatch.setattr(
        launcher,
        "_verify_transport_materialization",
        lambda value, *, controller_manifest, ingress: None,
    )
    transport = launcher._TransportMaterialization(  # noqa: SLF001
        mode="--prepare-once-v42r3",
        argv=("ssh", "command"),
        frame=b"frame",
        remote_command_sha256="f" * 64,
        expected_plan_id=plan_id,
        legacy_execution_source_manifest_id="a" * 64,
    )

    observation, marker_present, failure = (
        launcher._dispatch_effect_once_v42r3(  # noqa: SLF001
            operation="PREPARE",
            attempt_id=attempt_id,
            transport=transport,
            controller_manifest=controller,
            ingress=ingress,
            formal_transport_plan=plan,
            marker_name=launcher.LOCAL_PREPARE_NETWORK_START_NAME,
            marker_raw=marker_raw,
            expected_predecessor_formal_prefix=prefix,
            stdout_cap=1024,
            timeout_seconds=120.0,
        )
    )
    cut = tmp_path / launcher._anchor_name(  # noqa: SLF001
        "NETWORK_START.PREPARE." + attempt_id + ".json"
    )
    assert observation is None
    assert marker_present is False
    assert failure is not None
    assert not cut.exists()
    assert not (root / launcher.LOCAL_PREPARE_NETWORK_START_NAME).exists()


@pytest.mark.parametrize("mismatch", ["marker", "ingress"])
def test_effect_attempt_mismatch_is_rejected_before_any_cut(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mismatch: str,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    launcher._ensure_journal_root()  # noqa: SLF001
    attempt_id = "a" * 64
    plan_id = "b" * 64
    marker_attempt = "c" * 64 if mismatch == "marker" else attempt_id
    ingress_attempt = "d" * 64 if mismatch == "ingress" else attempt_id
    controller = {"controller_source_manifest_id": "e" * 64}
    ingress = {
        "formal_prepare_attempt": {
            "formal_prepare_attempt_id": ingress_attempt,
        }
    }
    plan = {"formal_transport_plan_id": plan_id}
    marker_raw = launcher._canonical_json_bytes(  # noqa: SLF001
        {
            "attempt_id": marker_attempt,
            "formal_transport_plan_id": plan_id,
            "operation": "PREPARE",
        }
    )
    formal = SimpleNamespace(
        verify_formal_transport_plan_v42r3=lambda value: dict(value),
        verify_network_start_v42r3=(
            lambda raw, **_kwargs: json.loads(raw.decode("utf-8"))
        ),
    )
    monkeypatch.setattr(launcher, "_authority", lambda: formal)
    monkeypatch.setattr(
        launcher,
        "_verify_transport_materialization",
        lambda value, *, controller_manifest, ingress: None,
    )
    monkeypatch.setattr(
        launcher,
        "_verified_module",
        lambda name: (_ for _ in ()).throw(AssertionError(name)),
    )
    transport = launcher._TransportMaterialization(  # noqa: SLF001
        mode="--prepare-once-v42r3",
        argv=("ssh", "command"),
        frame=b"frame",
        remote_command_sha256="f" * 64,
        expected_plan_id=plan_id,
        legacy_execution_source_manifest_id="9" * 64,
    )

    with pytest.raises(
        launcher.V42FormalTransportSuccessorLauncherError,
        match="network-start marker/transport join|ingress/marker attempt join",
    ):
        launcher._dispatch_effect_once_v42r3(  # noqa: SLF001
            operation="PREPARE",
            attempt_id=attempt_id,
            transport=transport,
            controller_manifest=controller,
            ingress=ingress,
            formal_transport_plan=plan,
            marker_name=launcher.LOCAL_PREPARE_NETWORK_START_NAME,
            marker_raw=marker_raw,
            expected_predecessor_formal_prefix={
                "predecessor_formal_effect_may_have_started": False,
            },
            stdout_cap=1024,
            timeout_seconds=120.0,
        )
    cut = tmp_path / launcher._anchor_name(  # noqa: SLF001
        "NETWORK_START.PREPARE." + attempt_id + ".json"
    )
    assert not cut.exists()
    assert not (root / launcher.LOCAL_PREPARE_NETWORK_START_NAME).exists()


@pytest.mark.parametrize("forgery", ["self_consistent_tuple", "frame_bit_flip"])
def test_exact_transport_reconstruction_rejects_self_consistent_forgery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, forgery: str,
) -> None:
    root = tmp_path / ".v42r3-journal"
    monkeypatch.setattr(launcher, "LOCAL_JOURNAL_ROOT", root)
    plan_id = "a" * 64
    legacy_id = "b" * 64
    loader_raw = b"pass"
    original_sections = (
        b"controller", b"authority", b"receiver", b"ingress",
    )
    forged_sections = (
        b"controller!", b"authority", b"receiver", b"ingress",
    )
    original_frame = b"frame-original"
    forged_frame = (
        b"frame-forged" if forgery == "self_consistent_tuple"
        else original_frame[:-1] + bytes([original_frame[-1] ^ 1])
    )
    decoded = {
        original_frame: original_sections,
        forged_frame: (
            forged_sections
            if forgery == "self_consistent_tuple" else original_sections
        ),
    }
    loader = SimpleNamespace(
        _decode_probe_frame_bytes=lambda frame: decoded[frame]
    )
    monkeypatch.setattr(
        launcher,
        "_verify_transport_ingress_v42r3",
        lambda **_kwargs: (plan_id, legacy_id),
    )
    monkeypatch.setattr(
        launcher,
        "_verified_module",
        lambda name: loader
        if name == launcher.LOADER_MODULE
        else (_ for _ in ()).throw(AssertionError(name)),
    )

    def _materialization(
        frame: bytes, sections: tuple[bytes, bytes, bytes, bytes],
    ) -> launcher._TransportMaterialization:  # noqa: SLF001
        command = launcher._loader_remote_command_v42r3(  # noqa: SLF001
            mode=launcher.PROBE_MODE,
            loader_raw=loader_raw,
            controller_raw=sections[0],
            authority_raw=sections[1],
            receiver_raw=sections[2],
            ingress_raw=sections[3],
            expected_plan_id=plan_id,
            legacy_execution_source_manifest_id=legacy_id,
        )
        argv = launcher._ssh_argv_v42r3(  # noqa: SLF001
            known_hosts_path=str(root / launcher.KNOWN_HOSTS_NAME),
            remote_command=command,
        )
        return launcher._TransportMaterialization(  # noqa: SLF001
            mode=launcher.PROBE_MODE,
            argv=argv,
            frame=frame,
            remote_command_sha256=hashlib.sha256(
                command.encode("utf-8")
            ).hexdigest(),
            expected_plan_id=plan_id,
            legacy_execution_source_manifest_id=legacy_id,
        )

    original = _materialization(original_frame, original_sections)
    monkeypatch.setattr(
        launcher, "_transport_materialization_v42r3", lambda **_kwargs: original
    )
    launcher._verify_transport_materialization(  # noqa: SLF001
        original, controller_manifest={}, ingress={}
    )
    forged = _materialization(
        forged_frame,
        forged_sections if forgery == "self_consistent_tuple" else original_sections,
    )
    with pytest.raises(
        launcher.V42FormalTransportSuccessorLauncherError,
        match="exact authenticated reconstruction",
    ):
        launcher._verify_transport_materialization(  # noqa: SLF001
            forged, controller_manifest={}, ingress={}
        )


@pytest.mark.parametrize(
    ("mode", "ordinal"),
    [
        ("--prepare-once-v42r3", "2"),
        ("--inspect-prepare-v42r3", "0"),
        ("--inspect-launch-v42r3", "4097"),
    ],
)
def test_inspection_ordinal_is_rejected_before_controller_verification(
    monkeypatch: pytest.MonkeyPatch, mode: str, ordinal: str,
) -> None:
    reached: list[str] = []
    monkeypatch.setattr(
        launcher,
        "verify_controller_and_native_inputs_v42r3",
        lambda **_kwargs: reached.append("controller"),
    )
    arguments = [
        "--predecessor-activation-evidence-root", "/tmp/predecessor",
        "--successor-evidence-root", "/tmp/successor",
        "--expected-successor-final-evidence-index-id", "a" * 64,
        "--expected-controller-commit", "b" * 40,
        "--expected-controller-tree", "c" * 40,
        mode,
        "--inspection-ordinal", ordinal,
    ]
    with pytest.raises(
        launcher.V42FormalTransportSuccessorLauncherError,
        match="inspection ordinal",
    ):
        launcher.main(arguments)
    assert reached == []


def test_verified_importer_detects_module_metadata_tamper() -> None:
    name = "scripts.acfqp_v42r3_metadata_tamper_test"
    relative = "scripts/acfqp_v42r3_metadata_tamper_test.py"
    finder = launcher._VerifiedSourceFinder(  # noqa: SLF001
        {relative: b"VALUE = 42\n"}
    )
    sys.meta_path.insert(0, finder)
    try:
        module = importlib.import_module(name)
        finder.verify_loaded()
        assert module.__spec__ is not None
        module.__spec__.origin = "/tmp/forged.py"
        with pytest.raises(
            launcher.V42FormalTransportSuccessorLauncherError,
            match="escaped source bytes",
        ):
            finder.verify_loaded()
    finally:
        sys.meta_path.remove(finder)
        sys.modules.pop(name, None)


def test_verified_importer_detects_sys_path_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden = {str(launcher.ROOT), str(launcher.SOURCE_ROOT)}
    baseline = tuple(entry for entry in sys.path if entry not in forbidden)
    monkeypatch.setattr(sys, "path", [*baseline, "/tmp/forged-import-root"])
    finder = launcher._VerifiedSourceFinder(  # noqa: SLF001
        {}, enforce_runtime_boundary=True, allowed_sys_path=baseline
    )
    with pytest.raises(
        launcher.V42FormalTransportSuccessorLauncherError,
        match="sys.path authority changed",
    ):
        finder.find_spec("json")


def test_prepare_ambiguous_outcome_is_retained_and_never_replayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_id = "a" * 64
    attempt_id = "b" * 64
    plan = {
        "formal_transport_plan_id": plan_id,
        "legacy_execution_source_manifest_id": "c" * 64,
    }
    attempt = {"formal_prepare_attempt_id": attempt_id}
    ambiguous = "POST_MARKER_AMBIGUOUS"
    retained: dict[str, object] = {}
    dispatch_count = 0
    formal = SimpleNamespace(
        OUTCOME_POST_MARKER_AMBIGUOUS=ambiguous,
        OUTCOME_COMPLETE_EXACT_RECEIPT="COMPLETE_EXACT_RECEIPT",
        OUTCOME_PRE_NETWORK_FAILURE="PRE_NETWORK_FAILURE",
        verify_formal_transport_plan_v42r3=lambda value: dict(value),
        build_formal_prepare_attempt_v42r3=lambda **_kwargs: dict(attempt),
        verify_formal_prepare_attempt_v42r3=lambda value, **_kwargs: dict(value),
        build_network_start_v42r3=lambda **_kwargs: {
            "attempt_id": attempt_id,
            "formal_transport_plan_id": plan_id,
            "operation": "PREPARE",
        },
    )
    transport = launcher._TransportMaterialization(  # noqa: SLF001
        mode="--prepare-once-v42r3",
        argv=("ssh", "command"),
        frame=b"frame",
        remote_command_sha256="d" * 64,
        expected_plan_id=plan_id,
        legacy_execution_source_manifest_id="c" * 64,
    )

    def _dispatch(**_kwargs: object) -> tuple[None, bool, BaseException]:
        nonlocal dispatch_count
        dispatch_count += 1
        return None, True, TimeoutError("ambiguous after marker")

    def _publish_outcome(**kwargs: object) -> dict[str, object]:
        outcome = {
            "attempt_id": kwargs["attempt_id"],
            "outcome_class": kwargs["outcome_class"],
            "controller_same_effect_dispatch_replay_allowed": False,
        }
        retained["outcome"] = outcome
        return outcome

    monkeypatch.setattr(launcher, "_authority", lambda: formal)
    monkeypatch.setattr(launcher, "_publish_or_verify", lambda *_args: None)
    monkeypatch.setattr(
        launcher,
        "_retained_terminal_outcome_v42r3",
        lambda **_kwargs: retained.get("outcome"),
    )
    monkeypatch.setattr(
        launcher, "_effect_cut_present_v42r3", lambda **_kwargs: False
    )
    monkeypatch.setattr(
        launcher,
        "_prepare_ingress_v42r3",
        lambda _plan, _attempt: {"formal_prepare_attempt": dict(attempt)},
    )
    monkeypatch.setattr(
        launcher,
        "_transport_materialization_v42r3",
        lambda **_kwargs: transport,
    )
    monkeypatch.setattr(launcher, "_dispatch_effect_once_v42r3", _dispatch)
    monkeypatch.setattr(launcher, "_publish_outcome_v42r3", _publish_outcome)

    first = launcher._execute_prepare_once_v42r3(  # noqa: SLF001
        controller_manifest={"controller_source_manifest_id": "e" * 64},
        formal_transport_plan=plan,
        expected_predecessor_formal_prefix={
            "predecessor_formal_effect_may_have_started": False,
        },
    )
    second = launcher._execute_prepare_once_v42r3(  # noqa: SLF001
        controller_manifest={"controller_source_manifest_id": "e" * 64},
        formal_transport_plan=plan,
        expected_predecessor_formal_prefix={
            "predecessor_formal_effect_may_have_started": False,
        },
    )
    assert first == second
    assert first["outcome_class"] == ambiguous
    assert first["controller_same_effect_dispatch_replay_allowed"] is False
    assert dispatch_count == 1
