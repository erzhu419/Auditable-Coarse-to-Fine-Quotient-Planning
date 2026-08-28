from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import types
from typing import Any

import pytest

from scripts import v42_standard_2048_formal_transport_loader_v42r3 as loader


ROOT = Path(__file__).resolve().parents[1]
LOADER_PATH = ROOT / loader.LOADER_RELATIVE
RECEIVER_PATH = ROOT / loader.RECEIVER_RELATIVE
AUTHORITY_PATH = ROOT / loader.AUTHORITY_RELATIVE


@pytest.fixture
def receiver_module(monkeypatch: pytest.MonkeyPatch):
    import acfqp

    module_name = loader.AUTHORITY_MODULE
    attribute = module_name.rsplit(".", 1)[1]
    authority_stub = types.ModuleType(module_name)
    monkeypatch.setitem(sys.modules, module_name, authority_stub)
    monkeypatch.setattr(acfqp, attribute, authority_stub, raising=False)
    spec = importlib.util.spec_from_file_location(
        "_acfqp_test_formal_transport_receiver_v42r3", RECEIVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_fact(relative: str, raw: bytes) -> dict[str, object]:
    return loader._artifact(relative, raw)  # noqa: SLF001


def _controller(
    *, loader_raw: bytes = b"loader", authority_raw: bytes = b"authority",
    receiver_raw: bytes = b"receiver",
) -> dict[str, object]:
    return {
        "schema": loader.CONTROLLER_SOURCE_MANIFEST_SCHEMA,
        "schema_version": loader.SCHEMA_VERSION,
        "formal_identity": "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2",
        "global_execution_ordinal": 2,
        "source_commit": "1" * 40,
        "source_tree": "2" * 40,
        "source_facts": [
            _source_fact(loader.LOADER_RELATIVE, loader_raw),
            _source_fact(loader.AUTHORITY_RELATIVE, authority_raw),
            _source_fact(loader.RECEIVER_RELATIVE, receiver_raw),
        ],
        "controller_source_manifest_id": "3" * 64,
    }


def _raise_nested_loader_failure(depth: int) -> None:
    if depth:
        _raise_nested_loader_failure(depth - 1)
    raise ValueError("loader diagnostic \N{SNOWMAN} " + "x" * 1000)


def test_loader_failure_diagnostic_is_canonical_bounded_and_traceable() -> None:
    try:
        _raise_nested_loader_failure(10)
    except ValueError as error:
        raw = loader._loader_failure_stderr(error)  # noqa: SLF001
        message = str(error)
        message_raw = message.encode("utf-8", errors="backslashreplace")
    else:  # pragma: no cover - the helper always raises
        raise AssertionError("loader failure fixture did not raise")

    assert raw.endswith(b"\n")
    assert len(raw) <= loader.MAX_LOADER_FAILURE_DIAGNOSTIC_BYTES
    document = json.loads(raw)
    assert raw[:-1] == loader._canonical_bytes(document)  # noqa: SLF001
    assert document["schema"] == loader.LOADER_FAILURE_DIAGNOSTIC_SCHEMA
    assert document["schema_version"] == loader.LOADER_FAILURE_DIAGNOSTIC_VERSION
    assert document["message"] == {
        "character_count": len(message),
        "prefix_byte_count": loader.LOADER_FAILURE_MESSAGE_PREFIX_BYTES,
        "prefix_hex": message_raw[
            : loader.LOADER_FAILURE_MESSAGE_PREFIX_BYTES
        ].hex(),
        "prefix_truncated": True,
        "scan_complete": True,
        "scanned_byte_count": len(message_raw),
        "scanned_character_count": len(message),
        "scanned_sha256": hashlib.sha256(message_raw).hexdigest(),
    }
    assert (
        document["traceback_scanned_frame_count"]
        > loader.LOADER_FAILURE_TRACEBACK_FRAMES
    )
    assert document["traceback_scan_truncated"] is False
    assert len(document["traceback_frames"]) == loader.LOADER_FAILURE_TRACEBACK_FRAMES
    assert document["traceback_frames_truncated"] is True
    final_function = bytes.fromhex(
        document["traceback_frames"][-1]["function"]["prefix_hex"]
    ).decode("utf-8")
    assert final_function == "_raise_nested_loader_failure"[
        : loader.LOADER_FAILURE_FUNCTION_PREFIX_BYTES
    ]


def test_loader_failure_diagnostic_has_fail_safe_generic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_diagnostic(_error: BaseException) -> bytes:
        raise MemoryError("diagnostic failure")

    monkeypatch.setattr(loader, "_loader_failure_diagnostic", fail_diagnostic)
    raw = loader._loader_failure_stderr(RuntimeError("hidden"))  # noqa: SLF001
    assert raw == loader.GENERIC_LOADER_FAILURE
    document = json.loads(raw)
    assert raw[:-1] == loader._canonical_bytes(document)  # noqa: SLF001
    assert document["diagnostic_builder_succeeded"] is False

    monkeypatch.setattr(
        loader,
        "_canonical_bytes",
        lambda _value: (_ for _ in ()).throw(MemoryError("encoder failure")),
    )
    raw = loader._loader_failure_stderr(RuntimeError("hidden"))  # noqa: SLF001
    assert raw == loader.GENERIC_LOADER_FAILURE
    assert json.loads(raw)["diagnostic_builder_succeeded"] is False


def test_loader_failure_diagnostic_bypasses_hostile_exception_accessors() -> None:
    class HostileMeta(type):
        def __getattribute__(cls, _name: str) -> object:
            raise SystemExit("metaclass accessor must not run")

    class HostileError(Exception, metaclass=HostileMeta):
        def __getattribute__(self, name: str) -> object:
            if name == "__traceback__":
                raise KeyboardInterrupt("traceback accessor must not run")
            return object.__getattribute__(self, name)

        def __str__(self) -> str:
            raise MemoryError("exception __str__ must not run")

    try:
        raise HostileError("bounded message from exact args")
    except HostileError as error:
        raw = loader._loader_failure_stderr(error)  # noqa: SLF001

    assert raw != loader.GENERIC_LOADER_FAILURE
    document = json.loads(raw)
    assert document["diagnostic_builder_succeeded"] is True
    assert bytes.fromhex(document["message"]["prefix_hex"]) == (
        b"bounded message from exact args"
    )


def test_loader_failure_diagnostic_caps_hostile_type_message_and_frame() -> None:
    error_type = type(
        "E" * 10_000,
        (Exception,),
        {"__module__": "m" * 10_000},
    )
    function_name = "f" * 10_000
    code = compile(
        f"def {function_name}(depth):\n"
        "    if depth:\n"
        f"        {function_name}(depth - 1)\n"
        "        return\n"
        "    raise error_type(message)\n"
        f"{function_name}(10)\n",
        "/" + "p" * 10_000,
        "exec",
        flags=0,
        dont_inherit=True,
        optimize=0,
    )
    try:
        exec(code, {"error_type": error_type, "message": "\N{SNOWMAN}" * 10_000})
    except Exception as error:
        raw = loader._loader_failure_stderr(error)  # noqa: SLF001
    else:  # pragma: no cover - the compiled fixture always raises
        raise AssertionError("hostile loader failure fixture did not raise")

    assert raw != loader.GENERIC_LOADER_FAILURE
    assert len(raw) <= loader.MAX_LOADER_FAILURE_DIAGNOSTIC_BYTES
    document = json.loads(raw)
    assert raw[:-1] == loader._canonical_bytes(document)  # noqa: SLF001
    assert document["exception_module"]["truncated"] is True
    assert document["exception_qualname"]["truncated"] is True
    assert document["message"]["scan_complete"] is False
    assert document["message"]["prefix_truncated"] is True
    assert len(document["traceback_frames"]) == loader.LOADER_FAILURE_TRACEBACK_FRAMES
    assert document["traceback_frames"][-1]["filename"]["truncated"] is True
    assert document["traceback_frames"][-1]["function"]["truncated"] is True


def test_loader_failure_diagnostic_bounds_traceback_scan() -> None:
    def recurse(depth: int) -> None:
        if depth:
            recurse(depth - 1)
        raise RuntimeError("deep traceback")

    try:
        recurse(loader.LOADER_FAILURE_TRACEBACK_SCAN_FRAMES + 20)
    except RuntimeError as error:
        raw = loader._loader_failure_stderr(error)  # noqa: SLF001

    document = json.loads(raw)
    assert len(raw) <= loader.MAX_LOADER_FAILURE_DIAGNOSTIC_BYTES
    assert (
        document["traceback_scanned_frame_count"]
        == loader.LOADER_FAILURE_TRACEBACK_SCAN_FRAMES
    )
    assert document["traceback_scan_truncated"] is True
    assert document["traceback_frames_truncated"] is True


def test_loader_top_level_emits_only_bounded_canonical_failure() -> None:
    source = LOADER_PATH.read_text(encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", source, "--invalid-mode"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={},
        check=False,
        timeout=10,
    )
    assert completed.returncode == 73
    assert completed.stdout == b""
    assert completed.stderr != loader.GENERIC_LOADER_FAILURE
    assert len(completed.stderr) <= loader.MAX_LOADER_FAILURE_DIAGNOSTIC_BYTES
    document = json.loads(completed.stderr)
    assert completed.stderr[:-1] == loader._canonical_bytes(document)  # noqa: SLF001
    assert document["diagnostic_scope"] == "DIAGNOSTIC_ONLY_NOT_FORMAL_RECEIPT"
    message_prefix = bytes.fromhex(document["message"]["prefix_hex"])
    assert message_prefix == b"formal transport loader mode or argv changed"


@pytest.mark.parametrize(
    "write_override",
    (
        "os.write=lambda *_args: 0",
        (
            "os.write=lambda *_args: "
            "(_ for _ in ()).throw(OSError('write failed'))"
        ),
    ),
)
def test_loader_top_level_write_failure_exits_without_traceback(
    write_override: str,
) -> None:
    source = LOADER_PATH.read_text(encoding="utf-8")
    future = "from __future__ import annotations\n"
    source = source.replace(
        future,
        future + "import os\n" + write_override + "\n",
        1,
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", source, "--invalid-mode"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={},
        check=False,
        timeout=10,
    )
    assert completed.returncode == 74
    assert completed.stdout == b""
    assert completed.stderr == b""


def test_virtual_procfs_reader_handles_zero_reported_size(
    receiver_module: Any,
) -> None:
    boot_path = Path("/proc/sys/kernel/random/boot_id")
    assert boot_path.stat().st_size == 0
    raw, observed = receiver_module._stable_virtual_regular(  # noqa: SLF001
        boot_path, 128
    )
    assert observed.st_size == 0
    assert len(raw) == 37
    assert raw.endswith(b"\n")


def test_formal_successor_journal_is_exact_owned_directory_or_absent(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-journal-state-", dir="/tmp"
    ) as raw_parent:
        journal = Path(raw_parent) / "journal"
        monkeypatch.setattr(receiver_module, "REMOTE_V42R3_JOURNAL_ROOT", journal)
        monkeypatch.setattr(receiver_module, "REMOTE_UID", os.geteuid())
        monkeypatch.setattr(receiver_module, "REMOTE_GID", os.getegid())
        assert receiver_module._formal_successor_journal_state() == "ABSENT"  # noqa: SLF001
        journal.mkdir(mode=0o700)
        assert receiver_module._formal_successor_journal_state() == "DIRECTORY"  # noqa: SLF001
        journal.chmod(0o755)
        with pytest.raises(receiver_module.V42FormalProbeReceiverError):
            receiver_module._formal_successor_journal_state()  # noqa: SLF001
        journal.chmod(0o700)
        journal.rmdir()
        journal.write_bytes(b"not a directory")
        with pytest.raises(receiver_module.V42FormalProbeReceiverError):
            receiver_module._formal_successor_journal_state()  # noqa: SLF001


def test_formal_journal_rejects_hardlink_wrong_mode_wrong_bytes_and_extra_file(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-journal-integrity-", dir="/tmp"
    ) as raw_parent:
        journal = Path(raw_parent) / "journal"
        journal.mkdir(mode=0o700)
        monkeypatch.setattr(receiver_module, "REMOTE_V42R3_JOURNAL_ROOT", journal)
        monkeypatch.setattr(receiver_module, "REMOTE_UID", os.geteuid())
        monkeypatch.setattr(receiver_module, "REMOTE_GID", os.getegid())
        for name in receiver_module.REMOTE_JOURNAL_INITIAL_INVENTORY:
            path = journal / name
            path.write_bytes(b"persisted\n")
            path.chmod(0o400)
        assert receiver_module._formal_successor_journal_inventory() == frozenset(  # noqa: SLF001
            receiver_module.REMOTE_JOURNAL_INITIAL_INVENTORY
        )

        loader_path = journal / receiver_module.REMOTE_LOADER_NAME
        fact = {
            "byte_count": len(b"expected\n"),
            "sha256": hashlib.sha256(b"expected\n").hexdigest(),
        }
        with pytest.raises(receiver_module.V42FormalProbeReceiverError):
            receiver_module._stable_verified_formal_journal_source(  # noqa: SLF001
                receiver_module.REMOTE_LOADER_NAME, fact, "loader"
            )

        loader_path.chmod(0o600)
        with pytest.raises(receiver_module.V42FormalProbeReceiverError):
            receiver_module._stable_formal_journal_artifact(  # noqa: SLF001
                receiver_module.REMOTE_LOADER_NAME
            )
        loader_path.chmod(0o400)

        hardlink = journal / receiver_module.REMOTE_ADMISSION_NAME
        os.link(loader_path, hardlink)
        with pytest.raises(receiver_module.V42FormalProbeReceiverError):
            receiver_module._stable_formal_journal_artifact(  # noqa: SLF001
                receiver_module.REMOTE_ADMISSION_NAME
            )
        hardlink.unlink()

        extra = journal / "UNREGISTERED"
        extra.write_bytes(b"extra\n")
        extra.chmod(0o400)
        with pytest.raises(receiver_module.V42FormalProbeReceiverError):
            receiver_module._formal_successor_journal_inventory()  # noqa: SLF001


def test_formal_journal_pin_rejects_exact_parent_rename_replacement(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-journal-parent-swap-", dir="/tmp"
    ) as raw_root:
        root = Path(raw_root)
        live_parent = root / "live"
        live_parent.mkdir(mode=0o700)
        journal = live_parent / "journal"
        journal.mkdir(mode=0o700)
        monkeypatch.setattr(receiver_module, "REMOTE_V42R3_JOURNAL_ROOT", journal)
        monkeypatch.setattr(receiver_module, "REMOTE_UID", os.geteuid())
        monkeypatch.setattr(receiver_module, "REMOTE_GID", os.getegid())
        for name in receiver_module.REMOTE_JOURNAL_INITIAL_INVENTORY:
            path = journal / name
            path.write_bytes((name + "\n").encode("ascii"))
            path.chmod(0o400)

        pin = receiver_module._FormalJournalPin.open()  # noqa: SLF001
        try:
            assert pin.inventory() == frozenset(
                receiver_module.REMOTE_JOURNAL_INITIAL_INVENTORY
            )
            detached_parent = root / "detached"
            live_parent.rename(detached_parent)
            live_parent.mkdir(mode=0o700)
            replacement = live_parent / "journal"
            replacement.mkdir(mode=0o700)
            for name in receiver_module.REMOTE_JOURNAL_INITIAL_INVENTORY:
                path = replacement / name
                path.write_bytes((name + "\n").encode("ascii"))
                path.chmod(0o400)

            with pytest.raises(
                receiver_module.V42FormalProbeReceiverError,
                match="ancestry changed",
            ):
                pin.inventory()
        finally:
            pin.close()


def test_formal_journal_pin_rejects_parent_swap_during_openat_read(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-journal-read-swap-", dir="/tmp"
    ) as raw_root:
        root = Path(raw_root)
        live_parent = root / "live"
        live_parent.mkdir(mode=0o700)
        journal = live_parent / "journal"
        journal.mkdir(mode=0o700)
        monkeypatch.setattr(receiver_module, "REMOTE_V42R3_JOURNAL_ROOT", journal)
        monkeypatch.setattr(receiver_module, "REMOTE_UID", os.geteuid())
        monkeypatch.setattr(receiver_module, "REMOTE_GID", os.getegid())
        artifact = journal / receiver_module.REMOTE_LOADER_NAME
        expected = b"x" * (1024 * 1024 + 1)
        artifact.write_bytes(expected)
        artifact.chmod(0o400)

        pin = receiver_module._FormalJournalPin.open()  # noqa: SLF001
        original_read = receiver_module.os.read
        swapped = False

        def swap_after_first_read(descriptor: int, count: int) -> bytes:
            nonlocal swapped
            chunk = original_read(descriptor, count)
            if not swapped:
                swapped = True
                live_parent.rename(root / "detached")
                live_parent.mkdir(mode=0o700)
                (live_parent / "journal").mkdir(mode=0o700)
            return chunk

        monkeypatch.setattr(receiver_module.os, "read", swap_after_first_read)
        try:
            with pytest.raises(
                receiver_module.V42FormalProbeReceiverError,
                match="ancestry changed",
            ):
                pin.read(receiver_module.REMOTE_LOADER_NAME)
            assert swapped is True
        finally:
            pin.close()


def test_initial_journal_publication_stays_on_one_pinned_inode_under_parent_swap(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-journal-publish-swap-", dir="/tmp"
    ) as raw_root:
        root = Path(raw_root)
        live_parent = root / "live"
        live_parent.mkdir(mode=0o700)
        journal = live_parent / "journal"
        monkeypatch.setattr(receiver_module, "REMOTE_V42R3_JOURNAL_ROOT", journal)
        monkeypatch.setattr(receiver_module, "REMOTE_UID", os.geteuid())
        monkeypatch.setattr(receiver_module, "REMOTE_GID", os.getegid())
        monkeypatch.setattr(
            receiver_module.processio,
            "create_one_shot_root",
            lambda *_args, **_kwargs: pytest.fail(
                "initial journal creation must be dir-fd-relative"
            ),
        )
        monkeypatch.setattr(
            receiver_module.processio,
            "write_once",
            lambda *_args, **_kwargs: pytest.fail(
                "initial journal publication must be journal-fd-relative"
            ),
        )
        original_write_once = receiver_module._FormalJournalPin.write_once  # noqa: SLF001
        publication_count = 0

        def swap_after_first_publication(pin: Any, name: str, raw: bytes) -> None:
            nonlocal publication_count
            original_write_once(pin, name, raw)
            publication_count += 1
            if publication_count == 1:
                live_parent.rename(root / "detached")
                live_parent.mkdir(mode=0o700)
                (live_parent / "journal").mkdir(mode=0o700)

        monkeypatch.setattr(
            receiver_module._FormalJournalPin,  # noqa: SLF001
            "write_once",
            swap_after_first_publication,
        )
        with pytest.raises(
            receiver_module.V42FormalProbeReceiverError,
            match="ancestry changed",
        ):
            receiver_module._publish_initial_journal(  # noqa: SLF001
                plan={"plan": 1},
                controller_manifest={"controller": 2},
                loader_raw=b"loader",
                authority_raw=b"authority",
                receiver_raw=b"receiver",
                transport_attempt={"attempt": 3},
            )
        assert publication_count == 1
        assert not any((live_parent / "journal").iterdir())
        assert len(list((root / "detached" / "journal").iterdir())) == 1


def test_initial_journal_pin_is_retained_for_admission_publication(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-journal-admission-swap-", dir="/tmp"
    ) as raw_root:
        root = Path(raw_root)
        live_parent = root / "live"
        live_parent.mkdir(mode=0o700)
        journal = live_parent / "journal"
        monkeypatch.setattr(receiver_module, "REMOTE_V42R3_JOURNAL_ROOT", journal)
        monkeypatch.setattr(receiver_module, "REMOTE_UID", os.geteuid())
        monkeypatch.setattr(receiver_module, "REMOTE_GID", os.getegid())
        pin = receiver_module._publish_initial_journal(  # noqa: SLF001
            plan={"plan": 1},
            controller_manifest={"controller": 2},
            loader_raw=b"loader",
            authority_raw=b"authority",
            receiver_raw=b"receiver",
            transport_attempt={"attempt": 3},
        )
        try:
            assert pin.inventory() == frozenset(
                receiver_module.REMOTE_JOURNAL_INITIAL_INVENTORY
            )
            live_parent.rename(root / "detached")
            live_parent.mkdir(mode=0o700)
            replacement = live_parent / "journal"
            replacement.mkdir(mode=0o700)
            with pytest.raises(
                receiver_module.V42FormalProbeReceiverError,
                match="ancestry changed",
            ):
                pin.write_once(receiver_module.REMOTE_ADMISSION_NAME, b"admission")
            assert not any(replacement.iterdir())
        finally:
            pin.close()


def test_frame_round_trip_has_one_magic_four_lengths_and_exact_eof() -> None:
    sections = (b"controller", b"authority", b"receiver", b'{"plan":1}')
    frame = loader.build_probe_frame_v42r3(
        controller_manifest_raw=sections[0],
        authority_raw=sections[1],
        receiver_raw=sections[2],
        ingress_raw=sections[3],
    )
    assert frame.startswith(loader.FRAME_MAGIC)
    offset = len(loader.FRAME_MAGIC)
    assert struct.unpack(">QQQQ", frame[offset : offset + 32]) == tuple(
        len(raw) for raw in sections
    )
    assert loader._decode_probe_frame_bytes(frame) == sections  # noqa: SLF001


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: raw[:-1],
        lambda raw: raw + b"x",
        lambda raw: b"X" + raw[1:],
        lambda raw: raw[: len(loader.FRAME_MAGIC)]
        + struct.pack(">QQQQ", 2**63, 1, 1, 1)
        + raw[len(loader.FRAME_MAGIC) + 32 :],
    ],
)
def test_frame_rejects_truncation_trailing_magic_and_length_mutation(mutate) -> None:
    frame = loader.build_probe_frame_v42r3(
        controller_manifest_raw=b"c",
        authority_raw=b"a",
        receiver_raw=b"r",
        ingress_raw=b"i",
    )
    with pytest.raises(loader.V42FormalProbeLoaderError):
        loader._decode_probe_frame_bytes(mutate(frame))  # noqa: SLF001


def test_artifact_fact_rejects_hash_count_and_git_blob_drift() -> None:
    raw = b"exact source\n"
    fact = _source_fact(loader.RECEIVER_RELATIVE, raw)
    loader._verify_raw_fact(  # noqa: SLF001
        raw=raw,
        relative=loader.RECEIVER_RELATIVE,
        fact=fact,
        expected_sha256=hashlib.sha256(raw).hexdigest(),
        expected_count=len(raw),
    )
    for field, value in (
        ("sha256", "0" * 64),
        ("byte_count", len(raw) + 1),
        ("git_blob_oid", "0" * 40),
    ):
        changed = dict(fact)
        changed[field] = value
        with pytest.raises(loader.V42FormalProbeLoaderError):
            loader._verify_raw_fact(  # noqa: SLF001
                raw=raw,
                relative=loader.RECEIVER_RELATIVE,
                fact=changed,
                expected_sha256=hashlib.sha256(raw).hexdigest(),
                expected_count=len(raw),
            )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "acfqp.mutated"),
        ("schema_version", "42.3.1"),
    ],
)
def test_controller_schema_and_version_mutation_fail_before_import(
    field: str, value: str,
) -> None:
    document = _controller()
    document[field] = value
    with pytest.raises(loader.V42FormalProbeLoaderError):
        loader._controller_facts(document)  # noqa: SLF001


def test_controller_requires_all_three_exact_source_only_artifacts() -> None:
    document = _controller()
    document["source_facts"] = document["source_facts"][:-1]
    with pytest.raises(loader.V42FormalProbeLoaderError):
        loader._controller_facts(document)  # noqa: SLF001


def test_verified_importer_seals_package_locations_metadata_and_module_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_name = "scripts.v42r3_verified_import_test"
    child_name = package_name + ".child"
    package_relative = "scripts/v42r3_verified_import_test/__init__.py"
    child_relative = "scripts/v42r3_verified_import_test/child.py"
    raws = {
        package_relative: b"VALUE = 1\n",
        child_relative: b"VALUE = 2\n",
    }
    facts = {
        relative: _source_fact(relative, raw) for relative, raw in raws.items()
    }
    finder = loader._VerifiedSourceFinder(  # noqa: SLF001
        legacy_facts=facts, injected={}
    )
    monkeypatch.setattr(finder, "_legacy_raw", lambda relative: raws[relative])
    sys.meta_path.insert(0, finder)
    try:
        package = importlib.import_module(package_name)
        child = importlib.import_module(child_name)
        finder.verify_loaded()
        assert package.__path__ == []
        assert package.__spec__.submodule_search_locations == []
        assert child.__spec__.submodule_search_locations is None

        original_file = child.__file__
        child.__file__ = "/unverified/live/source.py"
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        child.__file__ = original_file

        original_package = child.__package__
        child.__package__ = "scripts"
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        child.__package__ = original_package

        original_path = package.__path__
        package.__path__ = ["/unverified/live/package"]
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        package.__path__ = original_path

        original_loader = child.__loader__
        child.__loader__ = object()
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        child.__loader__ = original_loader

        original_spec_loader = child.__spec__.loader
        child.__spec__.loader = object()
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        child.__spec__.loader = original_spec_loader

        original_origin = child.__spec__.origin
        child.__spec__.origin = "/unverified/live/source.py"
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        child.__spec__.origin = original_origin

        original_locations = package.__spec__.submodule_search_locations
        package.__spec__.submodule_search_locations = ["/unverified/live/package"]
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        package.__spec__.submodule_search_locations = original_locations

        sys.meta_path.remove(finder)
        sys.meta_path.append(finder)
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        sys.meta_path.remove(finder)
        sys.meta_path.insert(0, finder)

        rogue_name = package_name + ".rogue"
        sys.modules[rogue_name] = types.ModuleType(rogue_name)
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        del sys.modules[rogue_name]

        sys.modules[child_name] = types.ModuleType(child_name)
        with pytest.raises(loader.V42FormalProbeLoaderError):
            finder.verify_loaded()
        sys.modules[child_name] = child
        finder.verify_loaded()
    finally:
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
        sys.modules.pop(child_name, None)
        sys.modules.pop(package_name, None)


def test_loader_and_receiver_freeze_python312_and_exclude_old_runtime_literals() -> None:
    combined = LOADER_PATH.read_text(encoding="utf-8") + RECEIVER_PATH.read_text(
        encoding="utf-8"
    )
    forbidden = ("python" + "310", "3" + ".10", "(3, " + "10, 12)")
    assert all(token not in combined for token in forbidden)
    assert '"/usr/bin/python3.12"' in combined
    assert "(3, 12, 3)" in combined
    assert "/usr/lib/python312.zip" in combined


def test_python_tcb_rejects_symlink_target_and_binary_hash_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42r3-tcb-", dir="/tmp") as raw_dir:
        test_root = Path(raw_dir)
        real = test_root / "python3.12"
        raw = b"registered interpreter bytes"
        real.write_bytes(raw)
        real.chmod(0o755)
        invocation = test_root / "python3"
        invocation.symlink_to(real.name)
        monkeypatch.setattr(loader, "PYTHON_INVOCATION_PATH", str(invocation))
        monkeypatch.setattr(loader, "PYTHON_REAL_PATH", str(real))
        monkeypatch.setattr(loader, "PYTHON_PROC_EXE_PATH", str(real))
        monkeypatch.setattr(loader, "PYTHON_REAL_BYTE_COUNT", len(raw))
        monkeypatch.setattr(
            loader, "PYTHON_REAL_SHA256", hashlib.sha256(raw).hexdigest()
        )
        monkeypatch.setattr(loader, "PYTHON_TCB_UID", os.geteuid())
        monkeypatch.setattr(loader, "PYTHON_TCB_GID", os.getegid())
        loader._verify_python_tcb()  # noqa: SLF001

        invocation.unlink()
        invocation.symlink_to("python3.13")
        with pytest.raises(loader.V42FormalProbeLoaderError):
            loader._verify_python_tcb()  # noqa: SLF001

        invocation.unlink()
        invocation.symlink_to(real.name)
        monkeypatch.setattr(loader, "PYTHON_REAL_SHA256", "0" * 64)
        with pytest.raises(loader.V42FormalProbeLoaderError):
            loader._verify_python_tcb()  # noqa: SLF001


def test_receiver_pin_construction_failure_closes_opened_descriptor(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptors = [os.open("/dev/null", os.O_RDONLY) for _ in range(2)]
    issued = list(descriptors)
    monkeypatch.setattr(
        receiver_module.os, "open", lambda *_args, **_kwargs: issued.pop(0)
    )
    with pytest.raises(receiver_module.V42FormalProbeReceiverError):
        receiver_module._ExecutablePin("/usr/bin/env")  # noqa: SLF001
    with pytest.raises(receiver_module.V42FormalProbeReceiverError):
        receiver_module._SourcePin(  # noqa: SLF001
            Path("/usr/bin/env"), {"byte_count": 1, "sha256": "0" * 64}
        )
    for descriptor in descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def test_scientific_exec_pin_failures_close_in_reverse_without_masking(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        receiver_module.legacy,
        "verify_live_source_matches_manifest_v42",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        receiver_module, "_scientific_runner_fact", lambda _manifest: {}
    )
    events: list[str] = []

    class RunnerPin:
        descriptor = 7
        sha256 = "1" * 64
        byte_count = 1

        def __init__(self, *_args, **_kwargs) -> None:
            events.append("runner-open")

        def verify(self) -> None:
            raise RuntimeError("primary runner verification")

        def close(self) -> None:
            events.append("runner-close")
            raise RuntimeError("runner close must not mask")

    class PythonConstructionFailure:
        def __init__(self, *_args, **_kwargs) -> None:
            raise RuntimeError("python pin construction")

    monkeypatch.setattr(receiver_module, "_SourcePin", RunnerPin)
    monkeypatch.setattr(
        receiver_module, "_ExecutablePin", PythonConstructionFailure
    )
    with pytest.raises(RuntimeError, match="python pin construction"):
        receiver_module._exec_scientific_runner(  # noqa: SLF001
            plan={},
            source_manifest={},
            loader_source_raw=b"loader",
            runner_role="PREPARE_SSH",
            cross_version_gate={},
            live_tool_facts={},
        )
    assert events == ["runner-open", "runner-close"]

    events.clear()

    class PythonPin:
        descriptor = 8
        fact: dict[str, Any] = {}

        def __init__(self, *_args, **_kwargs) -> None:
            events.append("python-open")

        def verify(self) -> None:
            pass

        def close(self) -> None:
            events.append("python-close")
            raise RuntimeError("python close must not mask")

    monkeypatch.setattr(receiver_module, "_ExecutablePin", PythonPin)
    with pytest.raises(RuntimeError, match="primary runner verification"):
        receiver_module._exec_scientific_runner(  # noqa: SLF001
            plan={},
            source_manifest={},
            loader_source_raw=b"loader",
            runner_role="PREPARE_SSH",
            cross_version_gate={},
            live_tool_facts={},
        )
    assert events == [
        "runner-open", "python-open", "python-close", "runner-close"
    ]


def test_subprocess_setup_failure_kills_reaps_and_cleanup_never_masks(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    processes: list[Any] = []

    class Stream:
        closed = False

        def fileno(self) -> int:
            return 99

        def close(self) -> None:
            self.closed = True
            events.append("stream-close")
            raise RuntimeError("stream cleanup must not mask")

    class Process:
        pid = 4321

        def __init__(self) -> None:
            self.stdout = Stream()
            self.stderr = Stream()
            processes.append(self)

        def poll(self):
            return None

        def wait(self, *, timeout: float):
            del timeout
            events.append("wait")
            return -9

        def kill(self) -> None:
            events.append("kill")

    class Selector:
        def register(self, *_args, **_kwargs) -> None:
            raise RuntimeError("primary selector registration")

        def close(self) -> None:
            events.append("selector-close")
            raise RuntimeError("selector cleanup must not mask")

    class Pin:
        path = "/usr/bin/systemctl"
        descriptor = 10

        def verify(self) -> None:
            pass

    monkeypatch.setattr(
        receiver_module.subprocess, "Popen", lambda *_args, **_kwargs: Process()
    )
    monkeypatch.setattr(receiver_module.selectors, "DefaultSelector", Selector)
    monkeypatch.setattr(receiver_module.os, "set_blocking", lambda *_args: None)
    monkeypatch.setattr(
        receiver_module.os,
        "killpg",
        lambda *_args: events.append("killpg"),
    )

    calls = (
        lambda: receiver_module._run_systemctl_show(Pin()),  # noqa: SLF001
        lambda: receiver_module._run_pinned_command(  # noqa: SLF001
            pin=Pin(),
            argv=("/usr/bin/systemctl",),
            environment={},
            stdout_cap=1,
            stderr_cap=1,
            timeout_seconds=1.0,
        ),
    )
    for call in calls:
        before = len(processes)
        with pytest.raises(RuntimeError, match="primary selector registration"):
            call()
        assert len(processes) == before + 1
        assert processes[-1].stdout.closed is True
        assert processes[-1].stderr.closed is True
    assert events.count("killpg") == 2
    assert events.count("wait") == 2
    assert events.count("selector-close") == 2
    assert events.count("stream-close") == 4

def test_receiver_effect_surface_is_explicit_and_excludes_direct_destructive_apis() -> None:
    raw = RECEIVER_PATH.read_text(encoding="utf-8")
    forbidden = (
        "os.mkdir(",
        "os.makedirs(",
        "os.unlink(",
        "os.replace(",
        "Path.write_",
        "systemctl start",
        "systemctl stop",
        "systemctl reset-failed",
    )
    assert all(token not in raw for token in forbidden)
    assert 'argv.extend(("--no-pager", "show"))' in raw
    assert "construction_k7_standard_2048_formal_transport_v42r1" not in raw
    assert {
        loader.PREPARE_MODE,
        loader.INSPECT_PREPARE_MODE,
        loader.ADMIT_MODE,
        loader.INSPECT_LAUNCH_MODE,
        loader.SERVICE_BOOTSTRAP_MODE,
        loader.SERVICE_WRAPPER_MODE,
    } <= {token for token in loader.ALL_MODES if token in raw}


def test_production_files_exist_and_authority_path_is_declared() -> None:
    assert LOADER_PATH.is_file()
    assert RECEIVER_PATH.is_file()
    # The authority is produced by a separate add-only successor component;
    # the loader's path contract is still fixed independently here.
    assert str(AUTHORITY_PATH).endswith(loader.AUTHORITY_RELATIVE)


def test_receiver_source_compiles_as_one_in_memory_entry() -> None:
    raw = RECEIVER_PATH.read_bytes()
    code = compile(raw, "<v42r3-formal-probe-receiver>", "exec", dont_inherit=True)
    assert code.co_name == "<module>"


def test_phase2_mode_schema_and_remote_root_inventory(receiver_module) -> None:
    expected_ssh = frozenset(
        {
            "--probe-host-epoch-v42r3",
            "--prepare-once-v42r3",
            "--inspect-prepare-v42r3",
            "--admit-launch-v42r3",
            "--inspect-launch-v42r3",
        }
    )
    expected_service = frozenset(
        {
            "--formal-launch-service-bootstrap-v42r3",
            "--formal-launch-service-wrapper-v42r3",
        }
    )
    expected_scientific = frozenset(
        {"--scientific-prepare-fd-v42r3", "--scientific-launch-fd-v42r3"}
    )
    assert loader.SSH_MODES == expected_ssh
    assert loader.SERVICE_MODES == expected_service
    assert loader.SCIENTIFIC_FD_MODES == expected_scientific
    assert receiver_module.ALL_MODES == expected_ssh | expected_service
    assert loader.SCHEMA_VERSION == receiver_module.SCHEMA_VERSION == "42.3.0"
    assert all(schema.endswith(".v42r3") for schema in receiver_module.INGRESS_SCHEMAS.values())
    root = (
        "/home/erzhu419/mine_code/"
        ".acfqp-v42-remote-ordinal2-formal-transport-v42r3r2"
    )
    assert loader.REMOTE_V42R3_JOURNAL_ROOT == root
    assert str(receiver_module.REMOTE_V42R3_JOURNAL_ROOT) == root
    assert loader.FIXED_REMOTE_ROOT == "/home/erzhu419/mine_code/.acfqp-v42-remote-ordinal2"
    assert str(receiver_module.FIXED_REMOTE_ROOT) == loader.FIXED_REMOTE_ROOT


def _systemd_run_argv(receiver_module, attempt_id: str, bootstrap: tuple[str, ...]) -> list[str]:
    return [
        receiver_module.TOOL_PATHS["systemd_run"],
        "--user",
        "--quiet",
        "--no-ask-password",
        "--service-type=exec",
        "--unit=" + receiver_module._unit_name(attempt_id),  # noqa: SLF001
        "--slice=background.slice",
        "--property=Restart=no",
        "--property=RemainAfterExit=yes",
        "--property=SuccessExitStatus=2",
        "--property=UMask=0077",
        "--property=KillMode=mixed",
        "--property=TimeoutStopSec=30s",
        "--property=RuntimeMaxSec=606300s",
        "--property=StandardInput=null",
        "--property=StandardOutput=null",
        "--property=StandardError=null",
        "--working-directory=" + str(receiver_module.FIXED_SOURCE_ROOT),
        "--",
        *bootstrap,
    ]


def test_systemd_run_accepts_only_exact_detached_service_profile(receiver_module) -> None:
    attempt_id = "a" * 64
    bootstrap = ("/usr/bin/python3", "-I", "service-loader")
    exact = _systemd_run_argv(receiver_module, attempt_id, bootstrap)
    assert receiver_module._verify_systemd_run_argv(  # noqa: SLF001
        exact, attempt_id, bootstrap
    ) == tuple(exact)

    for forbidden in (
        "--wait",
        "--pipe",
        "--pty",
        "--scope",
        "--collect",
        "--property=BindsTo=session.scope",
        "--binds-to=session.scope",
        "--wai",
        "--setenv=UNTRUSTED=1",
    ):
        changed = list(exact)
        changed.insert(changed.index("--"), forbidden)
        with pytest.raises(receiver_module.V42FormalProbeReceiverError):
            receiver_module._verify_systemd_run_argv(  # noqa: SLF001
                changed, attempt_id, bootstrap
            )

    changed_tail = list(exact)
    changed_tail[-1] = "mutated-loader"
    with pytest.raises(receiver_module.V42FormalProbeReceiverError):
        receiver_module._verify_systemd_run_argv(  # noqa: SLF001
            changed_tail, attempt_id, bootstrap
        )


def test_loaded_service_contract_rejects_stdio_lifecycle_and_root_drift(
    receiver_module,
) -> None:
    attempt_id = "b" * 64
    unit_name = receiver_module._unit_name(attempt_id)  # noqa: SLF001
    exact: dict[str, Any] = {
        "Id": unit_name,
        "Type": "exec",
        "Restart": "no",
        "RemainAfterExit": "yes",
        "SuccessExitStatus": "2",
        "UMask": "0077",
        "KillMode": "mixed",
        "StandardInput": "null",
        "StandardOutput": "null",
        "StandardError": "null",
        "WorkingDirectory": str(receiver_module.FIXED_SOURCE_ROOT),
        "FragmentPath": "/run/user/1000/systemd/transient/" + unit_name,
        "Environment": "",
        "Slice": "background.slice",
    }
    receiver_module._verify_loaded_service_contract(exact, attempt_id)  # noqa: SLF001
    for field, value in (
        ("Type", "simple"),
        ("Restart", "on-failure"),
        ("StandardOutput", "journal"),
        ("WorkingDirectory", str(receiver_module.REMOTE_V42R3_JOURNAL_ROOT)),
        ("Environment", "UNTRUSTED=1"),
        ("Slice", "session.scope"),
    ):
        changed = dict(exact)
        changed[field] = value
        with pytest.raises(receiver_module.V42FormalProbeReceiverError):
            receiver_module._verify_loaded_service_contract(  # noqa: SLF001
                changed, attempt_id
            )


def test_remote_tool_fact_projections_must_agree(receiver_module) -> None:
    facts = {
        name: {"path": path, "sha256": name}
        for name, path in receiver_module.TOOL_PATHS.items()
    }
    plan = {
        "host_epoch_receipt": {"remote_tool_facts": facts},
        "native_activation_binding": {"remote_tool_facts": facts},
    }
    assert receiver_module._expected_tool_facts(plan) == facts  # noqa: SLF001
    changed = {name: dict(value) for name, value in facts.items()}
    changed["python"]["sha256"] = "drift"
    plan["native_activation_binding"] = {"remote_tool_facts": changed}
    with pytest.raises(receiver_module.V42FormalProbeReceiverError):
        receiver_module._expected_tool_facts(plan)  # noqa: SLF001


def test_live_host_epoch_rejects_stale_manager_and_closes_observer_pin(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_manager = {
        "kernel_boot_id": "11111111-1111-4111-8111-111111111111",
        "linger_enabled": True,
        "linger_path": "/var/lib/systemd/linger/erzhu419",
        "user_manager_invocation_id": "22222222-2222-4222-8222-222222222222",
        "user_manager_main_pid": 1234,
        "user_manager_control_group": "/user.slice/user-1000.slice/user@1000.service",
    }
    stale_manager = dict(expected_manager)
    stale_manager["kernel_boot_id"] = "33333333-3333-4333-8333-333333333333"
    facts = {
        name: {"path": path, "sha256": name}
        for name, path in receiver_module.TOOL_PATHS.items()
    }
    plan = {
        "remote_tool_facts": facts,
        "host_epoch_receipt": {
            "remote_tool_facts": facts,
            "manager_binding": expected_manager,
        },
    }

    class Pin:
        closed = False

        def close(self) -> None:
            self.closed = True

    pin = Pin()
    monkeypatch.setattr(
        receiver_module, "_observe_tool_facts", lambda: (facts, pin)
    )
    monkeypatch.setattr(
        receiver_module, "_manager_binding", lambda _pin: stale_manager
    )
    with pytest.raises(
        receiver_module.V42FormalProbeReceiverError,
        match="host epoch or live tool facts changed",
    ):
        receiver_module._require_live_host_epoch(plan)  # noqa: SLF001
    assert pin.closed is True


def test_stale_epoch_stops_prepare_exec(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    stale = receiver_module.V42FormalProbeReceiverError("stale host epoch")
    effects: list[str] = []
    plan: dict[str, Any] = {"formal_transport_plan_id": "a" * 64}

    monkeypatch.setattr(
        receiver_module,
        "_join_controller_sources",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        receiver_module,
        "_verify_fixed_materialization",
        lambda _plan: None,
    )
    monkeypatch.setattr(
        receiver_module.legacy,
        "verify_remote_control_phase_inventory_v42r1",
        lambda *_args, **_kwargs: {"source_manifest": {}},
    )
    monkeypatch.setattr(
        receiver_module,
        "_cross_version_gate",
        lambda **_kwargs: {"cross_version_scientific_state_gate_id": "b" * 64},
    )
    monkeypatch.setattr(
        receiver_module,
        "_require_live_host_epoch",
        lambda _plan: (_ for _ in ()).throw(stale),
    )
    monkeypatch.setattr(
        receiver_module,
        "REMOTE_V42R3_JOURNAL_ROOT",
        tmp_path / "absent-journal",
    )
    monkeypatch.setattr(receiver_module.os, "isatty", lambda _fd: False)
    monkeypatch.setattr(receiver_module.os, "readlink", lambda _path: "pipe:[1]")
    monkeypatch.setattr(
        receiver_module,
        "_exec_scientific_runner",
        lambda **_kwargs: effects.append("exec"),
    )
    monkeypatch.setattr(
        receiver_module,
        "_authority_api",
        lambda _name: lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        receiver_module,
        "_effect_ingress",
        lambda *_args, **_kwargs: ({"formal_prepare_attempt": {}}, plan),
    )
    with pytest.raises(receiver_module.V42FormalProbeReceiverError, match="stale"):
        receiver_module._prepare_once(  # noqa: SLF001
            ingress_raw=b"prepare",
            expected_plan_id="a" * 64,
            controller_manifest={},
            loader_artifact={},
            authority_artifact={},
            receiver_artifact={},
            loader_source_raw=b"loader",
        )
    assert effects == []


def test_stale_epoch_stops_launch_before_publication_or_spawn(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    effects: list[str] = []
    stale = receiver_module.V42FormalProbeReceiverError("stale host epoch")
    plan: dict[str, Any] = {"formal_transport_plan_id": "a" * 64}
    receipt = {"prepare_receipt_id": "c" * 64}
    local = {"local_launch_attempt_id": "d" * 64}
    attempt = {"formal_launch_transport_attempt_id": "e" * 64}
    document = {
        "prepare_receipt": receipt,
        "local_launch_attempt": local,
        "formal_launch_transport_attempt": attempt,
    }
    monkeypatch.setattr(
        receiver_module,
        "_effect_ingress",
        lambda *_args, **_kwargs: (document, plan),
    )
    monkeypatch.setattr(
        receiver_module, "_join_controller_sources", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        receiver_module,
        "_prepare_receipt",
        lambda: (receipt, receiver_module.canonical_json_bytes(receipt)),
    )
    monkeypatch.setattr(
        receiver_module.legacy,
        "verify_local_launch_attempt_v42r1",
        lambda *_args, **_kwargs: local,
    )
    monkeypatch.setattr(
        receiver_module.legacy,
        "verify_remote_control_phase_inventory_v42r1",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        receiver_module, "_cross_version_gate", lambda **_kwargs: {}
    )
    monkeypatch.setattr(
        receiver_module,
        "_authority_api",
        lambda _name: lambda *_args, **_kwargs: attempt,
    )
    monkeypatch.setattr(
        receiver_module,
        "_require_live_host_epoch",
        lambda _plan: (_ for _ in ()).throw(stale),
    )
    monkeypatch.setattr(
        receiver_module,
        "_publish_initial_journal",
        lambda **_kwargs: effects.append("publish"),
    )
    monkeypatch.setattr(
        receiver_module,
        "_run_pinned_command",
        lambda **_kwargs: effects.append("spawn"),
    )
    with pytest.raises(receiver_module.V42FormalProbeReceiverError, match="stale"):
        receiver_module._admit_launch(  # noqa: SLF001
            ingress_raw=b"launch",
            expected_plan_id="a" * 64,
            controller_manifest={},
            loader_artifact={},
            authority_artifact={},
            receiver_artifact={},
            loader_source_raw=b"loader",
            authority_source_raw=b"authority",
            receiver_source_raw=b"receiver",
        )
    assert effects == []


def test_post_spawn_epoch_drift_never_publishes_exact_admission(
    receiver_module: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    effects: list[str] = []
    plan: dict[str, Any] = {"formal_transport_plan_id": "a" * 64}
    receipt = {"prepare_receipt_id": "c" * 64}
    local = {"local_launch_attempt_id": "d" * 64}
    attempt = {"formal_launch_transport_attempt_id": "e" * 64}
    document = {
        "prepare_receipt": receipt,
        "local_launch_attempt": local,
        "formal_launch_transport_attempt": attempt,
    }
    tools = {"systemd_run": {"sha256": "f" * 64}}
    manager = {"kernel_boot_id": "11111111-1111-4111-8111-111111111111"}
    gate_calls = 0

    def epoch_gate(_plan):
        nonlocal gate_calls
        gate_calls += 1
        if gate_calls == 3:
            raise receiver_module.V42FormalProbeReceiverError(
                "epoch changed after spawn"
            )
        return tools, manager

    monkeypatch.setattr(
        receiver_module,
        "_effect_ingress",
        lambda *_args, **_kwargs: (document, plan),
    )
    monkeypatch.setattr(
        receiver_module, "_join_controller_sources", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        receiver_module,
        "_prepare_receipt",
        lambda: (receipt, receiver_module.canonical_json_bytes(receipt)),
    )
    monkeypatch.setattr(
        receiver_module.legacy,
        "verify_local_launch_attempt_v42r1",
        lambda *_args, **_kwargs: local,
    )
    monkeypatch.setattr(
        receiver_module.legacy,
        "verify_remote_control_phase_inventory_v42r1",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        receiver_module, "_cross_version_gate", lambda **_kwargs: {}
    )

    def authority_api(name: str):
        if name == "verify_formal_launch_transport_attempt_v42r3":
            return lambda *_args, **_kwargs: attempt
        if name == "build_systemd_run_argv_v42r3":
            return lambda **_kwargs: ("systemd-run",)
        if name == "build_launch_admission_receipt_v42r3":
            return lambda **_kwargs: effects.append("build_admission")
        raise AssertionError(name)

    monkeypatch.setattr(receiver_module, "_authority_api", authority_api)
    monkeypatch.setattr(receiver_module, "_require_live_host_epoch", epoch_gate)

    class JournalPin:
        def verify(self) -> None:
            pass

        def write_once(self, _name: str, _raw: bytes) -> None:
            effects.append("admission_write")

        def inventory(self) -> frozenset[str]:
            return frozenset()

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        receiver_module,
        "_publish_initial_journal",
        lambda **_kwargs: (effects.append("initial_journal") or JournalPin()),
    )
    monkeypatch.setattr(
        receiver_module.processio,
        "write_once",
        lambda *_args, **_kwargs: effects.append("durable_write"),
    )
    monkeypatch.setattr(
        receiver_module, "_service_loader_argv", lambda **_kwargs: ("bootstrap",)
    )
    monkeypatch.setattr(
        receiver_module,
        "_verify_systemd_run_argv",
        lambda *_args, **_kwargs: ("systemd-run",),
    )

    class Pin:
        fact = tools["systemd_run"]
        descriptor = 9

        def __init__(self, _path: str) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(receiver_module, "_ExecutablePin", Pin)
    monkeypatch.setattr(
        receiver_module,
        "_run_pinned_command",
        lambda **_kwargs: (effects.append("spawn") or (0, b"", b"")),
    )
    monkeypatch.setattr(
        receiver_module,
        "_await_clean_wrapper",
        lambda **_kwargs: {"LoadState": "loaded"},
    )

    with pytest.raises(
        receiver_module.V42FormalProbeReceiverError,
        match="epoch changed after spawn",
    ):
        receiver_module._admit_launch(  # noqa: SLF001
            ingress_raw=b"launch",
            expected_plan_id="a" * 64,
            controller_manifest={},
            loader_artifact={},
            authority_artifact={},
            receiver_artifact={},
            loader_source_raw=b"loader",
            authority_source_raw=b"authority",
            receiver_source_raw=b"receiver",
        )
    assert gate_calls == 3
    assert effects == ["initial_journal", "durable_write", "spawn"]

def test_each_effect_path_gates_epoch_before_exec_publication_or_spawn() -> None:
    tree = ast.parse(RECEIVER_PATH.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    def call_lines(function: str, target: str) -> list[int]:
        return sorted(
            node.lineno
            for node in ast.walk(functions[function])
            if isinstance(node, ast.Call)
            and (
                isinstance(node.func, ast.Name) and node.func.id == target
                or isinstance(node.func, ast.Attribute)
                and node.func.attr == target
            )
        )

    prepare_gate = call_lines("_prepare_once", "_require_live_host_epoch")
    assert prepare_gate and prepare_gate[-1] < call_lines(
        "_prepare_once", "_exec_scientific_runner"
    )[0]
    scientific_gate = call_lines(
        "_exec_scientific_runner", "_require_live_host_epoch"
    )
    assert scientific_gate and scientific_gate[-1] < call_lines(
        "_exec_scientific_runner", "execve"
    )[0]

    launch_gates = call_lines("_admit_launch", "_require_live_host_epoch")
    assert len(launch_gates) == 3
    assert launch_gates[0] < call_lines("_admit_launch", "_publish_initial_journal")[0]
    assert launch_gates[1] < call_lines("_admit_launch", "_run_pinned_command")[0]
    assert call_lines("_admit_launch", "_run_pinned_command")[0] < launch_gates[2]
    assert launch_gates[2] < call_lines("_admit_launch", "write_once")[-1]

    bootstrap_gate = call_lines("_service_bootstrap", "_require_live_host_epoch")
    assert bootstrap_gate and bootstrap_gate[-1] < call_lines(
        "_service_bootstrap", "execve"
    )[0]

    wrapper_gates = call_lines("_service_wrapper", "_require_live_host_epoch")
    wrapper_writes = call_lines("_service_wrapper", "write_once")
    wrapper_exec = call_lines("_service_wrapper", "_exec_scientific_runner")
    assert len(wrapper_gates) == 3
    assert wrapper_gates[1] < wrapper_writes[0]
    assert wrapper_gates[2] < wrapper_exec[0]


@pytest.mark.parametrize(
    ("receipt_present", "local_present", "launch_present", "expected_phase"),
    [
        (False, False, False, "POST_MATERIALIZATION_PREPARE"),
        (True, False, False, "POST_PREPARE_AWAITING_LOCAL_LAUNCH"),
        (True, True, False, "POST_PREPARE_PRELAUNCH"),
        (True, True, True, "POST_LAUNCH"),
    ],
)
def test_read_only_phase_selection_recovers_without_replay(
    receiver_module,
    monkeypatch: pytest.MonkeyPatch,
    receipt_present: bool,
    local_present: bool,
    launch_present: bool,
    expected_phase: str,
) -> None:
    receipt = {"prepare_receipt_id": "c" * 64}

    def state(path: Path) -> str:
        if path.name == receiver_module.legacy.PREPARE_RECEIPT_NAME:
            return "REGULAR_FILE" if receipt_present else "ABSENT"
        if path.name == receiver_module.legacy.LOCAL_LAUNCH_ATTEMPT_NAME:
            return "REGULAR_FILE" if local_present else "ABSENT"
        if path.name == receiver_module.legacy.LAUNCH_HOST_ATTESTATION_NAME:
            return "REGULAR_FILE" if launch_present else "ABSENT"
        raise AssertionError(path)

    phases: list[tuple[str, dict[str, Any] | None]] = []

    def verify(phase: str, *, prepare_receipt=None):
        phases.append((phase, prepare_receipt))
        return {"phase": phase}

    monkeypatch.setattr(receiver_module, "_path_state", state)
    monkeypatch.setattr(receiver_module, "_prepare_receipt", lambda: (receipt, b"r"))
    monkeypatch.setattr(
        receiver_module.legacy, "verify_remote_control_phase_inventory_v42r1", verify
    )
    observed_receipt, phase = receiver_module._current_legacy_scientific_phase()  # noqa: SLF001
    assert observed_receipt == (receipt if receipt_present else None)
    assert phase == {"phase": expected_phase}
    assert phases == [
        (expected_phase, receipt if receipt_present else None)
    ]


def test_read_only_probe_and_inspect_call_graph_cannot_reach_effect_roles() -> None:
    tree = ast.parse(RECEIVER_PATH.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    graph: dict[str, set[str]] = {}
    for name, node in functions.items():
        graph[name] = {
            call.func.id
            for call in ast.walk(node)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        } & set(functions)
    reachable = {"_host_probe", "_inspect_prepare", "_inspect_launch"}
    frontier = list(reachable)
    while frontier:
        current = frontier.pop()
        for target in graph[current] - reachable:
            reachable.add(target)
            frontier.append(target)
    assert reachable.isdisjoint(
        {
            "_prepare_once",
            "_admit_launch",
            "_publish_initial_journal",
            "_service_bootstrap",
            "_service_wrapper",
            "_exec_scientific_runner",
            "_run_pinned_command",
        }
    )


def _journal_inputs() -> dict[str, Any]:
    return {
        "plan": {"schema_version": "42.3.0", "formal_transport_plan_id": "d" * 64},
        "controller_manifest": {"controller_source_manifest_id": "e" * 64},
        "loader_raw": b"loader-source\n",
        "authority_raw": b"authority-source\n",
        "receiver_raw": b"receiver-source\n",
        "transport_attempt": {"formal_launch_transport_attempt_id": "f" * 64},
    }


def test_initial_journal_is_six_ordered_o_excl_0400_durable_publications(
    receiver_module, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-journal-parent-", dir="/tmp"
    ) as raw_parent:
        journal = Path(raw_parent) / "journal"
        monkeypatch.setattr(receiver_module, "REMOTE_V42R3_JOURNAL_ROOT", journal)
        original = receiver_module._FormalJournalPin.write_once  # noqa: SLF001
        publication_order: list[str] = []

        def recording_write_once(pin: Any, name: str, raw: bytes) -> None:
            publication_order.append(name)
            original(pin, name, raw)

        monkeypatch.setattr(
            receiver_module._FormalJournalPin,  # noqa: SLF001
            "write_once",
            recording_write_once,
        )
        pin = receiver_module._publish_initial_journal(  # noqa: SLF001
            **_journal_inputs()
        )
        pin.close()
        assert stat.S_IMODE(journal.stat().st_mode) == 0o700
        assert tuple(publication_order) == (
            receiver_module.REMOTE_PLAN_NAME,
            receiver_module.REMOTE_CONTROLLER_NAME,
            receiver_module.REMOTE_LOADER_NAME,
            receiver_module.REMOTE_AUTHORITY_NAME,
            receiver_module.REMOTE_RECEIVER_NAME,
            receiver_module.REMOTE_TRANSPORT_ATTEMPT_NAME,
        )
        assert all(
            stat.S_IMODE(entry.lstat().st_mode) == 0o400
            and entry.lstat().st_nlink == 1
            for entry in journal.iterdir()
        )
        before = {entry.name: entry.read_bytes() for entry in journal.iterdir()}
        with pytest.raises(Exception):
            receiver_module._publish_initial_journal(**_journal_inputs())  # noqa: SLF001
        assert {entry.name: entry.read_bytes() for entry in journal.iterdir()} == before
        assert len(publication_order) == 6


def test_partial_journal_fault_is_retained_and_never_replayed(
    receiver_module, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-fault-parent-", dir="/tmp"
    ) as raw_parent:
        journal = Path(raw_parent) / "journal"
        monkeypatch.setattr(receiver_module, "REMOTE_V42R3_JOURNAL_ROOT", journal)
        original = receiver_module._FormalJournalPin.write_once  # noqa: SLF001
        calls: list[str] = []

        def fail_after_three(pin: Any, name: str, raw: bytes) -> None:
            if len(calls) == 3:
                raise RuntimeError("injected publication fault")
            calls.append(name)
            original(pin, name, raw)

        monkeypatch.setattr(
            receiver_module._FormalJournalPin,  # noqa: SLF001
            "write_once",
            fail_after_three,
        )
        with pytest.raises(RuntimeError, match="injected publication fault"):
            receiver_module._publish_initial_journal(**_journal_inputs())  # noqa: SLF001
        assert calls == list(receiver_module.REMOTE_JOURNAL_INITIAL_INVENTORY[:3])
        retained = {entry.name: entry.read_bytes() for entry in journal.iterdir()}
        with pytest.raises(Exception):
            receiver_module._publish_initial_journal(**_journal_inputs())  # noqa: SLF001
        assert {entry.name: entry.read_bytes() for entry in journal.iterdir()} == retained
        assert calls == list(receiver_module.REMOTE_JOURNAL_INITIAL_INVENTORY[:3])


def test_service_loader_uses_stable_nofollow_journal_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42r3-loader-journal-", dir="/tmp"
    ) as raw_root:
        journal = Path(raw_root)
        values = {
            loader.REMOTE_LOADER_NAME: b"loader-source\n",
            loader.REMOTE_CONTROLLER_NAME: b"controller\n",
            loader.REMOTE_AUTHORITY_NAME: b"authority\n",
            loader.REMOTE_RECEIVER_NAME: b"receiver\n",
            loader.REMOTE_PLAN_NAME: b"plan\n",
        }
        for name, raw in values.items():
            path = journal / name
            path.write_bytes(raw)
            path.chmod(0o400)
        monkeypatch.setattr(loader, "REMOTE_V42R3_JOURNAL_ROOT", str(journal))
        assert loader._service_sections(values[loader.REMOTE_LOADER_NAME]) == (  # noqa: SLF001
            values[loader.REMOTE_CONTROLLER_NAME],
            values[loader.REMOTE_AUTHORITY_NAME],
            values[loader.REMOTE_RECEIVER_NAME],
            values[loader.REMOTE_PLAN_NAME],
        )
        receiver_path = journal / loader.REMOTE_RECEIVER_NAME
        receiver_path.unlink()
        receiver_path.symlink_to(journal / loader.REMOTE_AUTHORITY_NAME)
        with pytest.raises((OSError, loader.V42FormalProbeLoaderError)):
            loader._service_sections(values[loader.REMOTE_LOADER_NAME])  # noqa: SLF001
