from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Any

import pytest

from scripts import v42_activation_successor_receiver as receiver


@pytest.fixture
def linux_tmp_path() -> Path:
    # The repository's global pytest temp root may be a drvfs mount whose
    # chmod semantics cannot represent the production 0700/0400 contract.
    path = Path(tempfile.mkdtemp(prefix="acfqp-v42r2-receiver-", dir="/tmp"))
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _write_read_only(path: Path, value: object) -> bytes:
    raw = _canonical(value)
    path.write_bytes(raw)
    path.chmod(0o400)
    return raw


def _fixture_root(tmp_path: Path) -> tuple[Path, dict[str, bytes]]:
    root = tmp_path / "fixed-root"
    root.mkdir(mode=0o700)
    source = root / "source"
    source.mkdir(mode=0o700)
    values = {
        "source_manifest": {"kind": "source", "ordinal": 2},
        "transport_manifest": {"kind": "transport", "ordinal": 2},
        "local_materialization_attempt": {"kind": "local-attempt", "ordinal": 2},
        "remote_materialization_attempt": {"kind": "remote-attempt", "ordinal": 2},
        "materialization_terminal": {"kind": "nested-terminal", "ordinal": 2},
    }
    paths = {
        "source_manifest": root / receiver.SOURCE_MANIFEST_NAME,
        "transport_manifest": root / receiver.TRANSPORT_MANIFEST_NAME,
        "local_materialization_attempt": root / receiver.LOCAL_ATTEMPT_NAME,
        "remote_materialization_attempt": root / receiver.REMOTE_ATTEMPT_NAME,
        "materialization_terminal": source / receiver.TERMINAL_NAME,
    }
    raws = {
        role: _write_read_only(paths[role], value)
        for role, value in values.items()
    }
    # These names must appear in inventories, but their bytes are outside the
    # successor inspector's bounded five-document scope.
    (root / "SOURCE_CAPSULE.tar").write_bytes(b"do-not-read-capsule")
    (root / "REMOTE_BOOTSTRAP.pyz").write_bytes(b"do-not-read-pyz")
    (source / "ordinary_source.py").write_bytes(b"raise RuntimeError\n")
    root.chmod(0o700)
    source.chmod(0o700)
    return root, raws


def _tree_fingerprint(root: Path) -> dict[str, tuple[Any, ...]]:
    result: dict[str, tuple[Any, ...]] = {}
    for path in (root, *sorted(root.rglob("*"))):
        observed = path.lstat()
        relative = "." if path == root else path.relative_to(root).as_posix()
        raw = path.read_bytes() if stat.S_ISREG(observed.st_mode) else None
        result[relative] = (
            observed.st_dev,
            observed.st_ino,
            observed.st_mode,
            observed.st_uid,
            observed.st_gid,
            observed.st_nlink,
            observed.st_size,
            observed.st_mtime_ns,
            observed.st_ctime_ns,
            raw,
        )
    return result


def test_observe_reads_exact_five_json_documents_in_one_stable_window(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, raws = _fixture_root(linux_tmp_path)
    before = _tree_fingerprint(root)
    opened: list[tuple[object, int]] = []
    real_open = receiver.os.open

    def recording_open(path: object, flags: int, *args: Any, **kwargs: Any) -> int:
        opened.append((path, flags))
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(receiver.os, "open", recording_open)
    observation = receiver.observe(
        fixed_root=str(root), expected_uid=os.getuid(), expected_gid=os.getgid()
    )
    after = _tree_fingerprint(root)

    assert after == before
    assert observation["schema"] == receiver.OBSERVATION_SCHEMA
    assert observation["observed_document_count"] == 5
    assert observation["remote_mutation_performed"] is False
    assert observation["large_binary_content_read"] is False
    assert observation["only_fixed_small_json_documents_read"] is True
    assert observation["single_pinned_before_after_window"] is True
    assert observation["all_document_reads_nofollow_and_stable"] is True
    assert observation["collected_subset_only_not_whole_tree"] is True
    assert observation["fixed_root_lexical_chain_before"] == observation[
        "fixed_root_lexical_chain_after"
    ]

    fixed = observation["fixed_root"]
    source = observation["source_root"]
    assert fixed["path"] == str(root)
    assert source["path"] == str(root / "source")
    for row in (fixed, source):
        assert row["identity_before"] == row["identity_opened"]
        assert row["identity_before"] == row["identity_after"]
        assert row["inventory_before"] == row["inventory_after"]
    assert "SOURCE_CAPSULE.tar" in fixed["inventory_before"]
    assert "REMOTE_BOOTSTRAP.pyz" in fixed["inventory_before"]
    assert "ordinary_source.py" in source["inventory_before"]

    documents = observation["documents"]
    assert tuple(documents) == tuple(row[0] for row in receiver.DOCUMENT_SPECS)
    for role, parent, name, _maximum in receiver.DOCUMENT_SPECS:
        fact = documents[role]
        expected_parent = root if parent == "fixed_root" else root / "source"
        assert fact["parent"] == parent
        assert fact["relative_name"] == name
        assert fact["absolute_path"] == str(expected_parent / name)
        assert fact["identity_before"] == fact["identity_opened"]
        assert fact["identity_before"] == fact["identity_after"]
        assert fact["identity_before"]["node_type"] == "REGULAR_FILE"
        assert fact["identity_before"]["mode"] == 0o400
        assert fact["identity_before"]["uid"] == os.getuid()
        assert fact["identity_before"]["gid"] == os.getgid()
        assert fact["identity_before"]["st_nlink"] == 1
        assert fact["byte_count"] == len(raws[role])
        assert fact["sha256"] == hashlib.sha256(raws[role]).hexdigest()
        assert _canonical(fact["document"]) == raws[role]

    forbidden = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    assert all(flags & forbidden == 0 for _path, flags in opened)
    regular_open_names = {
        path
        for path, flags in opened
        if isinstance(path, str) and not flags & os.O_DIRECTORY
    }
    assert regular_open_names == {
        receiver.SOURCE_MANIFEST_NAME,
        receiver.TRANSPORT_MANIFEST_NAME,
        receiver.LOCAL_ATTEMPT_NAME,
        receiver.REMOTE_ATTEMPT_NAME,
        receiver.TERMINAL_NAME,
    }
    assert "SOURCE_CAPSULE.tar" not in regular_open_names
    assert "REMOTE_BOOTSTRAP.pyz" not in regular_open_names

    payload = dict(observation)
    claimed = payload.pop("activation_successor_read_only_observation_id")
    assert claimed == hashlib.sha256(
        receiver.OBSERVATION_ID_DOMAIN.encode("ascii")
        + b"\0"
        + _canonical(payload)
    ).hexdigest()


def test_observe_rejects_nested_terminal_replaced_by_top_level_copy(
    linux_tmp_path: Path,
) -> None:
    root, _raws = _fixture_root(linux_tmp_path)
    terminal = root / "source" / receiver.TERMINAL_NAME
    top_level = root / receiver.TERMINAL_NAME
    top_level.write_bytes(terminal.read_bytes())
    top_level.chmod(0o400)
    terminal.unlink()

    with pytest.raises(receiver.V42ActivationSuccessorReceiverError):
        receiver.observe(
            fixed_root=str(root), expected_uid=os.getuid(), expected_gid=os.getgid()
        )


@pytest.mark.parametrize("target", ["source", receiver.REMOTE_ATTEMPT_NAME])
def test_observe_rejects_symlinked_source_or_document(
    linux_tmp_path: Path, target: str
) -> None:
    root, _raws = _fixture_root(linux_tmp_path)
    if target == "source":
        source = root / "source"
        moved = root / "source-real"
        source.rename(moved)
        source.symlink_to(moved, target_is_directory=True)
    else:
        path = root / target
        moved = root / (target + ".real")
        path.rename(moved)
        path.symlink_to(moved.name)

    with pytest.raises(receiver.V42ActivationSuccessorReceiverError):
        receiver.observe(
            fixed_root=str(root), expected_uid=os.getuid(), expected_gid=os.getgid()
        )


def test_observe_rejects_file_change_during_read(
    linux_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _raws = _fixture_root(linux_tmp_path)
    target = root / receiver.SOURCE_MANIFEST_NAME
    real_read = receiver.os.read
    changed = False

    def racing_read(descriptor: int, count: int) -> bytes:
        nonlocal changed
        result = real_read(descriptor, count)
        if result and not changed:
            changed = True
            target.chmod(0o600)
        return result

    monkeypatch.setattr(receiver.os, "read", racing_read)
    with pytest.raises(
        receiver.V42ActivationSuccessorReceiverError,
        match="changed during read",
    ):
        receiver.observe(
            fixed_root=str(root), expected_uid=os.getuid(), expected_gid=os.getgid()
        )


def test_observe_rejects_noncanonical_document(linux_tmp_path: Path) -> None:
    root, _raws = _fixture_root(linux_tmp_path)
    path = root / receiver.LOCAL_ATTEMPT_NAME
    path.chmod(0o600)
    path.write_bytes(b'{"z":1, "a":2}')
    path.chmod(0o400)

    with pytest.raises(
        receiver.V42ActivationSuccessorReceiverError,
        match="exact canonical JSON",
    ):
        receiver.observe(
            fixed_root=str(root), expected_uid=os.getuid(), expected_gid=os.getgid()
        )


def test_receiver_imports_only_python_stdlib() -> None:
    tree = ast.parse(Path(receiver.__file__).read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots <= sys.stdlib_module_names | {"__future__"}
    assert "acfqp" not in imported_roots
