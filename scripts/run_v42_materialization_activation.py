"""Local V42 materialization activation driver.

The driver has exactly three operations: a repeatable read-only resource
probe, one activation of a selected COMPLETE pre-formal receipt, and a
repeatable read-only classifier.  It reuses the frozen pre-formal sender's
descriptor-pinned OpenSSH child pump; activation publishes its local attempt
and network-start marker durably before spawning that child.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Callable

from acfqp import construction_k7_standard_2048_materialization_activation_v42r1 as activation
from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as preformal
from acfqp import construction_k7_standard_2048_remote_execution_authority_v42r1 as authority
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from scripts import run_v42_preformal_upload_sender as frozen_sender


MAXIMUM_DOCUMENT_BYTES = 32 * 1024**2
MAXIMUM_STDOUT_BYTES = 32 * 1024**2
STDERR_CAP = 64 * 1024
SSH_TIMEOUT_SECONDS = 900.0
ROOT = Path(__file__).resolve().parents[1]


class V42MaterializationActivationDriverError(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise V42MaterializationActivationDriverError(message)


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAXIMUM_DOCUMENT_BYTES:
        _fail(label + " envelope changed")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V42MaterializationActivationDriverError(
            label + " is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(label + " is not a canonical JSON object")
    return value


def _read_stable_program(path: str, artifact: dict[str, Any], label: str) -> bytes:
    if (
        type(path) is not str
        or not path.startswith("/")
        or ".." in path.split("/")
        or type(artifact) is not dict
    ):
        _fail(label + " path or artifact changed")
    before = os.lstat(path)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size != artifact.get("byte_count")
        or not 0 < before.st_size <= MAXIMUM_DOCUMENT_BYTES
    ):
        _fail(label + " storage changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail(label + " changed before open")
        chunks: list[bytes] = []
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(descriptor, min(1024 * 1024, before.st_size - offset), offset)
            if not chunk:
                _fail(label + " ended early")
            chunks.append(chunk)
            offset += len(chunk)
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.lstat(path)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after_fd, field)
        or getattr(before, field) != getattr(after_path, field)
        for field in fields
    ):
        _fail(label + " changed while read")
    raw = b"".join(chunks)
    if hashlib.sha256(raw).hexdigest() != artifact.get("sha256"):
        _fail(label + " bytes changed")
    return raw


def _verify_driver_self(plan: dict[str, Any]) -> None:
    artifact = plan.get("activation_driver_artifact")
    if type(artifact) is not dict:
        _fail("activation driver artifact changed")
    direct = os.path.abspath(__file__)
    _read_stable_program(direct, artifact, "activation driver")


def _secure_directory(path: str) -> int:
    parent = str(Path(path).parent)
    if not os.path.isdir(parent):
        _fail("activation journal parent is absent")
    previous = os.umask(0o077)
    try:
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            pass
    finally:
        os.umask(previous)
    observed = os.lstat(path)
    if (
        not stat.S_ISDIR(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o700
        or observed.st_uid != os.geteuid()
        or observed.st_gid != os.getegid()
    ):
        _fail("activation journal root changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    os.fsync(descriptor)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    return descriptor


def _directory_component_identity(observed: os.stat_result) -> tuple[int, ...]:
    """Identity fields stable under unrelated activity in a shared directory."""
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_uid,
        observed.st_gid,
    )


@dataclass
class _LexicalDirectoryPins:
    path: str
    component_names: tuple[str, ...]
    descriptors: tuple[int, ...]
    identities: tuple[tuple[int, ...], ...]
    persistent_anchors: tuple[tuple[int, str, dict[str, Any]], ...] = ()

    @property
    def descriptor(self) -> int:
        return self.descriptors[-1]

    def verify_named(self) -> None:
        if (
            len(self.descriptors) != len(self.component_names) + 1
            or len(self.identities) != len(self.descriptors)
            or _directory_component_identity(os.fstat(self.descriptors[0]))
            != self.identities[0]
        ):
            _fail("activation local directory root anchor changed")
        for index, component in enumerate(self.component_names):
            parent_fd = self.descriptors[index]
            held_fd = self.descriptors[index + 1]
            named = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
            held = os.fstat(held_fd)
            expected = self.identities[index + 1]
            if (
                not stat.S_ISDIR(named.st_mode)
                or _directory_component_identity(named) != expected
                or _directory_component_identity(held) != expected
            ):
                _fail("activation local directory lexical chain changed")
        for parent_index, anchor_name, document in self.persistent_anchors:
            _read_document_at(
                self.descriptors[parent_index], anchor_name, document
            )

    def ensure_persistent_component_anchors(self) -> None:
        anchors: list[tuple[int, str, dict[str, Any]]] = []
        absolute = ""
        effective_uid = os.geteuid()
        effective_groups = {os.getegid(), *os.getgroups()}
        for index, component in enumerate(self.component_names):
            absolute += "/" + component
            parent_stat = os.fstat(self.descriptors[index])
            parent_mode = stat.S_IMODE(parent_stat.st_mode)
            writable = (
                effective_uid == 0
                or (
                    parent_stat.st_uid == effective_uid
                    and bool(parent_mode & stat.S_IWUSR)
                )
                or (
                    parent_stat.st_gid in effective_groups
                    and bool(parent_mode & stat.S_IWGRP)
                )
                or bool(parent_mode & stat.S_IWOTH)
            )
            if not writable:
                continue
            document = {
                "schema": (
                    "acfqp.v42_local_activation_lexical_component_identity.v42r1"
                ),
                "path": absolute,
                "st_dev": self.identities[index + 1][0],
                "st_ino": self.identities[index + 1][1],
                "st_mode": self.identities[index + 1][2],
                "st_uid": self.identities[index + 1][3],
                "st_gid": self.identities[index + 1][4],
                "same_named_component_required_for_activation_reentry": True,
            }
            anchor_name = (
                ".acfqp-v42-activation-component-"
                + hashlib.sha256(absolute.encode("utf-8")).hexdigest()
                + ".json"
            )
            try:
                os.stat(
                    anchor_name,
                    dir_fd=self.descriptors[index],
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                try:
                    _write_once(self.descriptors[index], anchor_name, document)
                except FileExistsError:
                    _read_document_at(
                        self.descriptors[index], anchor_name, document
                    )
            else:
                _read_document_at(self.descriptors[index], anchor_name, document)
            anchors.append((index, anchor_name, document))
        self.persistent_anchors = tuple(anchors)
        self.verify_named()

    def close(self) -> None:
        for descriptor in reversed(self.descriptors):
            os.close(descriptor)


def _open_lexical_directory(path: str) -> _LexicalDirectoryPins:
    parsed = Path(path)
    if not parsed.is_absolute() or ".." in parsed.parts:
        _fail("activation local directory path changed")
    current = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    descriptors = [current]
    identities = [_directory_component_identity(os.fstat(current))]
    component_names: list[str] = []
    try:
        for component in parsed.parts[1:]:
            before = os.stat(component, dir_fd=current, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                _fail("activation local directory component changed type")
            successor = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=current,
            )
            opened = os.fstat(successor)
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                os.close(successor)
                _fail("activation local directory changed during open")
            current = successor
            descriptors.append(current)
            identities.append(_directory_component_identity(opened))
            component_names.append(component)
        result = _LexicalDirectoryPins(
            path=path,
            component_names=tuple(component_names),
            descriptors=tuple(descriptors),
            identities=tuple(identities),
        )
        result.verify_named()
        return result
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _journal_root_identity(path: str, observed: os.stat_result) -> dict[str, Any]:
    return {
        "schema": "acfqp.v42_local_activation_journal_root_identity.v42r1",
        "path": path,
        "st_dev": observed.st_dev,
        "st_ino": observed.st_ino,
        "mode": stat.S_IMODE(observed.st_mode),
        "uid": observed.st_uid,
        "gid": observed.st_gid,
        "st_nlink": observed.st_nlink,
    }


@dataclass
class _PinnedJournal:
    path: str
    root_name: str
    anchor_name: str
    network_cut_anchor_name: str
    parent_pins: _LexicalDirectoryPins
    parent_fd: int
    descriptor: int
    identity: dict[str, Any]

    def verify_named(self) -> None:
        self.parent_pins.verify_named()
        current = os.stat(
            self.root_name, dir_fd=self.parent_fd, follow_symlinks=False
        )
        held = os.fstat(self.descriptor)
        if (
            not stat.S_ISDIR(current.st_mode)
            or _journal_root_identity(self.path, current) != self.identity
            or _journal_root_identity(self.path, held) != self.identity
        ):
            _fail("activation journal named inode changed")
        _read_document_at(self.parent_fd, self.anchor_name, self.identity)
        self.parent_pins.verify_named()

    def _network_cut_document(self, network_start: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema": "acfqp.v42_local_activation_external_network_cut.v42r1",
            "journal_root_identity": self.identity,
            "network_start": network_start,
            "network_effect_may_start_after_this_anchor_is_durable": True,
            "same_activation_identity_retry_forbidden": True,
        }

    def read_external_network_cut(
        self, network_start: dict[str, Any]
    ) -> dict[str, Any] | None:
        try:
            os.stat(
                self.network_cut_anchor_name,
                dir_fd=self.parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return None
        expected = self._network_cut_document(network_start)
        return _read_document_at(
            self.parent_fd, self.network_cut_anchor_name, expected
        )

    def publish_external_network_cut(
        self, network_start: dict[str, Any]
    ) -> tuple[int, ...]:
        self.verify_named()
        expected = self._network_cut_document(network_start)
        identity = _write_once(
            self.parent_fd, self.network_cut_anchor_name, expected
        )
        self.verify_named()
        _read_document_at(
            self.parent_fd,
            self.network_cut_anchor_name,
            expected,
            expected_identity=identity,
        )
        return identity

    def close(self) -> None:
        os.close(self.descriptor)
        self.parent_pins.close()


def _secure_pinned_journal(path: str) -> _PinnedJournal:
    parsed = Path(path)
    if not parsed.is_absolute() or ".." in parsed.parts or not parsed.name:
        _fail("activation journal path changed")
    parent_pins = _open_lexical_directory(str(parsed.parent))
    parent_pins.ensure_persistent_component_anchors()
    parent_fd = parent_pins.descriptor
    created = False
    try:
        previous = os.umask(0o077)
        try:
            try:
                os.mkdir(parsed.name, 0o700, dir_fd=parent_fd)
                created = True
            except FileExistsError:
                pass
        finally:
            os.umask(previous)
        descriptor = os.open(
            parsed.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o700
            or observed.st_uid != os.geteuid()
            or observed.st_gid != os.getegid()
        ):
            _fail("activation journal root storage changed")
        identity = _journal_root_identity(path, observed)
        anchor_name = "." + parsed.name + ".ROOT_IDENTITY.json"
        network_cut_anchor_name = "." + parsed.name + ".NETWORK_CUT.json"
        if created:
            os.fsync(descriptor)
            _write_once(parent_fd, anchor_name, identity)
            os.fsync(parent_fd)
        else:
            _read_document_at(parent_fd, anchor_name, identity)
        result = _PinnedJournal(
            path=path,
            root_name=parsed.name,
            anchor_name=anchor_name,
            network_cut_anchor_name=network_cut_anchor_name,
            parent_pins=parent_pins,
            parent_fd=parent_fd,
            descriptor=descriptor,
            identity=identity,
        )
        result.verify_named()
        return result
    except BaseException:
        try:
            os.close(descriptor)
        except UnboundLocalError:
            pass
        parent_pins.close()
        raise


def _file_identity(observed: os.stat_result) -> tuple[int, ...]:
    return tuple(
        getattr(observed, field)
        for field in (
            "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
            "st_size", "st_mtime_ns", "st_ctime_ns",
        )
    )


def _write_once(
    directory_fd: int, name: str, document: dict[str, Any]
) -> tuple[int, ...]:
    raw = canonical_json_bytes(document)
    previous = os.umask(0o077)
    try:
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o400,
            dir_fd=directory_fd,
        )
    finally:
        os.umask(previous)
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail("activation journal write made no progress")
            offset += written
        os.fsync(descriptor)
        observed = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if (
        (observed.st_dev, observed.st_ino) != (final.st_dev, final.st_ino)
        or stat.S_IMODE(final.st_mode) != 0o400
        or final.st_uid != os.geteuid()
        or final.st_gid != os.getegid()
        or final.st_nlink != 1
        or final.st_size != len(raw)
    ):
        _fail("activation journal file changed after publication")
    os.fsync(directory_fd)
    return _file_identity(final)


def _read_document_stable_at(
    directory_fd: int,
    name: str,
    *,
    expected_identity: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != os.geteuid()
        or before.st_gid != os.getegid()
        or before.st_nlink != 1
        or not 0 < before.st_size <= MAXIMUM_DOCUMENT_BYTES
    ):
        _fail("activation journal storage changed: " + name)
    descriptor = os.open(
        name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory_fd
    )
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("activation journal file changed before open")
        raw = b""
        while len(raw) < before.st_size:
            chunk = os.read(descriptor, before.st_size - len(raw))
            if not chunk:
                _fail("activation journal file ended early")
            raw += chunk
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after_fd, field)
        or getattr(before, field) != getattr(after_path, field)
        for field in fields
    ):
        _fail("activation journal file changed while read")
    if expected_identity is not None and _file_identity(after_path) != expected_identity:
        _fail("activation journal published inode changed: " + name)
    return _canonical_document(raw, name)


def _read_document_at(
    directory_fd: int,
    name: str,
    expected: dict[str, Any],
    *,
    expected_identity: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    document = _read_document_stable_at(
        directory_fd, name, expected_identity=expected_identity
    )
    if document != expected:
        _fail("activation journal document changed: " + name)
    return document


_CONTROL_REFERENCE_CAPS = {
    authority.SOURCE_MANIFEST_NAME: 64 * 1024**2,
    authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: 4 * 1024**2,
    authority.REMOTE_BOOTSTRAP_PYZ_NAME: 64 * 1024**2,
    authority.SOURCE_CAPSULE_NAME: 2 * 1024**3,
    authority.TRANSPORT_MANIFEST_NAME: 64 * 1024**2,
}


def _verify_control_root_reference(
    control_root: str, activation_plan: dict[str, Any]
) -> dict[str, Any]:
    facts = activation_plan.get("control_facts")
    if type(facts) is not list:
        _fail("activation evidence control facts changed type")
    by_name = {
        row.get("name"): row for row in facts if type(row) is dict
    }
    if set(by_name) != set(preformal.CONTROL_NAMES) or len(by_name) != len(facts):
        _fail("activation evidence control facts changed inventory")
    pins = _open_lexical_directory(control_root)
    root_fd = pins.descriptor
    try:
        pins.verify_named()
        if sorted(os.listdir(root_fd)) != list(preformal.CONTROL_NAMES):
            _fail("activation evidence control root inventory changed")
        rows: list[dict[str, Any]] = []
        for name in preformal.CONTROL_NAMES:
            expected = by_name[name]
            expected_count = expected.get("byte_count")
            expected_sha = expected.get("sha256")
            cap = _CONTROL_REFERENCE_CAPS[name]
            if (
                type(expected_count) is not int
                or not 0 < expected_count <= cap
                or type(expected_sha) is not str
                or len(expected_sha) != 64
            ):
                _fail("activation evidence control identity changed: " + name)
            before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != os.geteuid()
                or before.st_gid != os.getegid()
                or before.st_nlink != 1
                or before.st_size != expected_count
            ):
                _fail("activation evidence control storage changed: " + name)
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=root_fd,
            )
            digest = hashlib.sha256()
            try:
                opened = os.fstat(descriptor)
                if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                    _fail("activation evidence control changed before open")
                offset = 0
                while offset < expected_count:
                    chunk = os.pread(
                        descriptor,
                        min(1024 * 1024, expected_count - offset),
                        offset,
                    )
                    if not chunk:
                        _fail("activation evidence control ended early: " + name)
                    digest.update(chunk)
                    offset += len(chunk)
                if os.pread(descriptor, 1, expected_count):
                    _fail("activation evidence control exceeded expected size")
                after_fd = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            after_path = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            fields = (
                "st_dev", "st_ino", "st_mode", "st_uid", "st_gid",
                "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns",
            )
            if (
                digest.hexdigest() != expected_sha
                or any(
                    getattr(before, field) != getattr(after_fd, field)
                    or getattr(before, field) != getattr(after_path, field)
                    for field in fields
                )
            ):
                _fail("activation evidence control changed while hashed: " + name)
            rows.append(
                {
                    "name": name,
                    "path": str(Path(control_root) / name),
                    "mode": stat.S_IMODE(before.st_mode),
                    "uid": before.st_uid,
                    "gid": before.st_gid,
                    "st_nlink": before.st_nlink,
                    "byte_count": expected_count,
                    "sha256": expected_sha,
                }
            )
        pins.verify_named()
        if sorted(os.listdir(root_fd)) != list(preformal.CONTROL_NAMES):
            _fail("activation evidence control root changed after hashing")
        return {
            "control_root": control_root,
            "control_facts": rows,
            "exact_inventory": list(preformal.CONTROL_NAMES),
            "all_files_read_nofollow_from_pinned_root": True,
            "all_file_bytes_hashed_with_bounded_reads": True,
            "whole_root_first_last_snapshot_equal": True,
        }
    finally:
        pins.close()


def _ensure_exact_pre_marker_prefix(
    directory_fd: int,
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
) -> None:
    names = sorted(os.listdir(directory_fd))
    plan_name = activation.LOCAL_ACTIVATION_PLAN_NAME
    attempt_name = activation.LOCAL_ACTIVATION_ATTEMPT_NAME
    if names == []:
        _write_once(directory_fd, plan_name, activation_plan)
        _write_once(directory_fd, attempt_name, local_attempt)
    elif names == [plan_name]:
        _read_document_at(directory_fd, plan_name, activation_plan)
        _write_once(directory_fd, attempt_name, local_attempt)
    elif names == sorted((plan_name, attempt_name)):
        _read_document_at(directory_fd, plan_name, activation_plan)
        _read_document_at(directory_fd, attempt_name, local_attempt)
    else:
        _fail("activation journal is not an exact recoverable pre-marker prefix")
    if sorted(os.listdir(directory_fd)) != sorted((plan_name, attempt_name)):
        _fail("activation pre-marker inventory changed")
    os.fsync(directory_fd)


def _existing_post_marker_outcome(
    directory_fd: int,
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
) -> dict[str, Any] | None:
    base = {
        activation.LOCAL_ACTIVATION_PLAN_NAME,
        activation.LOCAL_ACTIVATION_ATTEMPT_NAME,
        activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
    }
    names = set(os.listdir(directory_fd))
    if activation.LOCAL_ACTIVATION_NETWORK_START_NAME not in names:
        return None
    _read_document_at(
        directory_fd, activation.LOCAL_ACTIVATION_PLAN_NAME, activation_plan
    )
    _read_document_at(
        directory_fd, activation.LOCAL_ACTIVATION_ATTEMPT_NAME, local_attempt
    )
    _read_document_at(
        directory_fd, activation.LOCAL_ACTIVATION_NETWORK_START_NAME, network_start
    )
    receipt_name = activation.LOCAL_ACTIVATION_RECEIPT_NAME
    ambiguity_name = activation.LOCAL_ACTIVATION_AMBIGUITY_NAME
    if names == base:
        ambiguity = activation.build_local_materialization_activation_ambiguity_v42r1(
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
            reason_code="RECOVERED_POST_MARKER_WITHOUT_DURABLE_OUTCOME",
        )
        _write_once(directory_fd, ambiguity_name, ambiguity)
        return ambiguity
    if names == base | {receipt_name}:
        document = _read_document_stable_at(directory_fd, receipt_name)
        return activation.verify_local_materialization_activation_receipt_v42r1(
            document,
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
            remote_attempt_id=document.get(
                "remote_materialization_activation_attempt_id"
            ),
        )
    if names == base | {ambiguity_name}:
        document = _read_document_stable_at(directory_fd, ambiguity_name)
        return activation.verify_local_materialization_activation_ambiguity_v42r1(
            document,
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
        )
    _fail("activation post-marker journal inventory changed")


def _close_external_cut_without_inner_marker(
    directory_fd: int,
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
) -> dict[str, Any]:
    plan_name = activation.LOCAL_ACTIVATION_PLAN_NAME
    attempt_name = activation.LOCAL_ACTIVATION_ATTEMPT_NAME
    ambiguity_name = activation.LOCAL_ACTIVATION_AMBIGUITY_NAME
    base = {plan_name, attempt_name}
    names = set(os.listdir(directory_fd))
    if names not in (base, base | {ambiguity_name}):
        _fail("external activation cut journal inventory changed")
    _read_document_at(directory_fd, plan_name, activation_plan)
    _read_document_at(directory_fd, attempt_name, local_attempt)
    ambiguity = activation.build_local_materialization_activation_ambiguity_v42r1(
        activation_plan=activation_plan,
        local_attempt=local_attempt,
        network_start=network_start,
        reason_code="RECOVERED_EXTERNAL_NETWORK_CUT_WITHOUT_INNER_MARKER",
    )
    if ambiguity_name in names:
        return activation.verify_local_materialization_activation_ambiguity_v42r1(
            _read_document_stable_at(directory_fd, ambiguity_name),
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
        )
    _write_once(directory_fd, ambiguity_name, ambiguity)
    return ambiguity


def _verify_selected_preformal_receipt_join(
    *, activation_plan: dict[str, Any], preformal_receipt: dict[str, Any]
) -> None:
    if type(preformal_receipt) is not dict:
        _fail("selected pre-formal receipt changed type")
    try:
        raw = canonical_json_bytes(preformal_receipt)
    except Exception as error:
        raise V42MaterializationActivationDriverError(
            "selected pre-formal receipt is not canonical"
        ) from error
    if len(raw) > MAXIMUM_DOCUMENT_BYTES:
        _fail("selected pre-formal receipt exceeded cap")
    payload = dict(preformal_receipt)
    receipt_id = payload.pop("preformal_upload_receipt_id", None)
    if (
        preformal_receipt.get("schema") != preformal.PREFORMAL_UPLOAD_RECEIPT_SCHEMA
        or type(receipt_id) is not str
        or len(receipt_id) != 64
        or any(character not in "0123456789abcdef" for character in receipt_id)
        or receipt_id
        != hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:preformal-upload-receipt\0"
            + canonical_json_bytes(payload)
        ).hexdigest()
        or receipt_id != activation_plan.get("preformal_upload_receipt_id")
    ):
        _fail("selected pre-formal receipt identity or activation join changed")
    if (
        preformal_receipt.get("scratch_root_fact", {}).get("path")
        != activation_plan.get("preformal_scratch_root")
        or preformal_receipt.get("ledger_stage_fact", {}).get("path")
        != activation_plan.get("preformal_ledger_stage_root")
    ):
        _fail("selected pre-formal receipt path join changed")


@dataclass
class _PreparedDispatch:
    pins: Any
    child: Any

    def verify(self, plan: dict[str, Any]) -> None:
        self.pins.verify()
        self.child.verify_prepared()
        fingerprint = frozen_sender._derive_identity_fingerprint_v42r1(  # noqa: SLF001
            plan=plan, pins=self.pins
        )
        if fingerprint != plan["ssh_client_contract"]["identity_public_fingerprint"]:
            _fail("activation dispatch identity fingerprint changed")
        self.pins.verify()
        self.child.verify_prepared()

    def close(self) -> None:
        self.child.close()
        self.pins.close()


def _prepare_dispatch(
    *, plan: dict[str, Any], argv: list[str], segments: tuple[bytes, ...]
) -> _PreparedDispatch:
    pins = frozen_sender._open_local_dispatch_pins_v42r1(plan)  # noqa: SLF001
    try:
        child = frozen_sender._prepare_pinned_child(  # noqa: SLF001
            executable_fd=pins.ssh.descriptor,
            argv=tuple(argv),
            environment=dict(preformal.LOCAL_DISPATCH_ENVIRONMENT),
            segments=segments,
            stdout_cap=MAXIMUM_STDOUT_BYTES,
            stderr_cap=STDERR_CAP,
            timeout_seconds=float(SSH_TIMEOUT_SECONDS),
        )
        prepared = _PreparedDispatch(pins=pins, child=child)
        prepared.verify(plan)
        return prepared
    except BaseException:
        pins.close()
        raise


def _exact_stdout_document(observation: Any, label: str) -> dict[str, Any]:
    if (
        not observation.exec_succeeded
        or observation.returncode != 0
        or observation.timed_out
        or observation.stdout_overflow
        or not observation.stdout_eof
        or observation.stderr_total_byte_count != 0
        or not observation.stderr_eof
        or not observation.stdin_complete
        or not observation.stdout_raw.endswith(b"\n")
        or observation.stdout_raw.count(b"\n") != 1
    ):
        _fail(label + " did not close with one exact response")
    return _canonical_document(observation.stdout_raw[:-1], label)


def _dispatch_read_only(
    *, plan: dict[str, Any], argv: list[str], receiver_raw: bytes, envelope: dict[str, Any]
) -> dict[str, Any]:
    prepared = _prepare_dispatch(
        plan=plan,
        argv=argv,
        segments=(receiver_raw, canonical_json_bytes(envelope)),
    )
    try:
        prepared.verify(plan)
        observation = prepared.child.spawn_and_pump()
        prepared.pins.verify()
    finally:
        prepared.close()
    return _exact_stdout_document(observation, "read-only activation response")


def execute_resource_probe_v42r1(
    *, resource_plan: dict[str, Any], preformal_receipt: dict[str, Any], loader_path: str,
    receiver_path: str, dispatch: Callable[..., dict[str, Any]] = _dispatch_read_only,
) -> dict[str, Any]:
    _verify_driver_self(resource_plan)
    loader_raw = _read_stable_program(
        loader_path, resource_plan["activation_loader_artifact"], "activation loader"
    )
    receiver_raw = _read_stable_program(
        receiver_path, resource_plan["activation_receiver_artifact"], "activation receiver"
    )
    argv = activation.materialize_authorized_resource_probe_argv_v42r1(
        resource_plan=resource_plan
    )
    envelope = {
        "schema": "acfqp.v42_preactivation_resource_probe_ingress.v42r1",
        "operation": "READ_ONLY_PREACTIVATION_RESOURCE_PROBE",
        "resource_plan": resource_plan,
        "preformal_receipt": preformal_receipt,
    }
    observed = dispatch(
        plan=resource_plan, argv=argv, receiver_raw=receiver_raw, envelope=envelope
    )
    if (
        observed.get("only_current_ssh_ingress_process_started") is not True
        or observed.get("additional_or_durable_remote_process_started") is not False
        or observed.get("remote_mutation_performed") is not False
    ):
        _fail("resource probe observation changed effect semantics")
    return activation.build_preactivation_resource_result_v42r1(
        resource_plan=resource_plan,
        preformal_receipt=preformal_receipt,
        stage=observed.get("resource_observation_stage"),
        observed_hostname=observed.get("observed_hostname"),
        observed_user=observed.get("observed_user"),
        observed_uid=observed.get("observed_uid"),
        observed_gid=observed.get("observed_gid"),
        observed_python=observed.get("observed_python"),
        memory_total_bytes=observed.get("memory_total_bytes"),
        memory_available_bytes=observed.get("memory_available_bytes"),
        swap_total_bytes=observed.get("swap_total_bytes"),
        swap_free_bytes=observed.get("swap_free_bytes"),
        filesystem_available_bytes=observed.get("filesystem_available_bytes"),
        cgroup_memory_ancestry=observed.get("cgroup_memory_ancestry"),
        selected_remote_snapshot=observed.get("selected_remote_snapshot"),
    )


def execute_activation_v42r1(
    *, activation_plan: dict[str, Any], preformal_receipt: dict[str, Any], loader_path: str,
    receiver_path: str, service_path: str, local_effective_uid: int,
    journal_publisher: Callable[[str, dict[str, Any]], None] | None = None,
    prepared_dispatch_factory: Callable[..., _PreparedDispatch] = _prepare_dispatch,
) -> dict[str, Any]:
    _verify_driver_self(activation_plan)
    _verify_selected_preformal_receipt_join(
        activation_plan=activation_plan, preformal_receipt=preformal_receipt
    )
    _read_stable_program(loader_path, activation_plan["activation_loader_artifact"], "activation loader")
    receiver_raw = _read_stable_program(
        receiver_path, activation_plan["activation_receiver_artifact"], "activation receiver"
    )
    service_raw = _read_stable_program(
        service_path, activation_plan["activation_service_artifact"], "activation service"
    )
    local = activation.build_local_materialization_activation_attempt_v42r1(
        activation_plan=activation_plan, local_effective_uid=local_effective_uid
    )
    network = activation.build_materialization_activation_network_start_v42r1(
        activation_plan=activation_plan, local_attempt=local
    )
    remote = activation.build_remote_materialization_activation_attempt_v42r1(
        activation_plan=activation_plan,
        local_attempt=local,
        network_start=network,
        observed_remote_snapshot=activation_plan["selected_remote_snapshot"],
        observed_remote_ingress_argv=activation.materialize_authorized_remote_ingress_argv_v42r1(
            activation_plan=activation_plan,
            local_activation_attempt_id=local["local_materialization_activation_attempt_id"],
        ),
        observed_hostname=activation_plan["expected_remote_hostname"],
        observed_user=authority.REMOTE_USER,
        observed_uid=authority.REMOTE_UID,
        observed_gid=authority.REMOTE_GID,
    )
    envelope = {
        "schema": "acfqp.v42_materialization_activation_ingress.v42r1",
        "operation": "ACTIVATE_SELECTED_COMPLETE_RECEIPT",
        "activation_plan": activation_plan,
        "local_activation_attempt": local,
        "network_start": network,
        "remote_activation_attempt": remote,
        "service_source_utf8": service_raw.decode("utf-8", errors="strict"),
    }
    argv = activation.materialize_authorized_ssh_argv_v42r1(
        activation_plan=activation_plan,
        local_activation_attempt_id=local["local_materialization_activation_attempt_id"],
    )
    journal: _PinnedJournal | None = None
    if journal_publisher is None:
        journal = _secure_pinned_journal(local["local_control_root"])
        try:
            external_cut = journal.read_external_network_cut(network)
            existing = _existing_post_marker_outcome(
                journal.descriptor,
                activation_plan=activation_plan,
                local_attempt=local,
                network_start=network,
            )
            if existing is not None:
                journal.close()
                journal = None
                return existing
            if external_cut is not None:
                ambiguity = _close_external_cut_without_inner_marker(
                    journal.descriptor,
                    activation_plan=activation_plan,
                    local_attempt=local,
                    network_start=network,
                )
                journal.verify_named()
                journal.close()
                journal = None
                return ambiguity
            _ensure_exact_pre_marker_prefix(
                journal.descriptor,
                activation_plan=activation_plan,
                local_attempt=local,
            )
            journal.verify_named()
        except BaseException:
            journal.close()
            journal = None
            raise
    else:
        journal_publisher("PLAN", activation_plan)
        journal_publisher("ATTEMPT", local)
    try:
        prepared = prepared_dispatch_factory(
            plan=activation_plan,
            argv=argv,
            segments=(receiver_raw, canonical_json_bytes(envelope)),
        )
    except BaseException:
        if journal is not None:
            journal.close()
            journal = None
        raise
    published_network = False
    dispatch_error: BaseException | None = None
    observation: Any | None = None
    try:
        prepared.verify(activation_plan)
        if journal_publisher is None:
            assert journal is not None
            journal.verify_named()
            _read_document_at(
                journal.descriptor,
                activation.LOCAL_ACTIVATION_PLAN_NAME,
                activation_plan,
            )
            _read_document_at(
                journal.descriptor, activation.LOCAL_ACTIVATION_ATTEMPT_NAME, local
            )
            journal.publish_external_network_cut(network)
            network_identity = _write_once(
                journal.descriptor,
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                network,
            )
            journal.verify_named()
            _read_document_at(
                journal.descriptor,
                activation.LOCAL_ACTIVATION_NETWORK_START_NAME,
                network,
                expected_identity=network_identity,
            )
            published_network = True
        else:
            journal_publisher("NETWORK_START", network)
            published_network = True
        observation = prepared.child.spawn_and_pump()
        prepared.pins.verify()
    except BaseException as error:
        dispatch_error = error
    finally:
        prepared.close()
    if not published_network:
        if journal is not None:
            journal.close()
            journal = None
        if dispatch_error is not None:
            raise dispatch_error
        _fail("activation network cut was not durably published")
    try:
        if dispatch_error is not None or observation is None:
            raise V42MaterializationActivationDriverError(
                "activation SSH did not produce an exact observation"
            )
        ingress = _exact_stdout_document(observation, "activation ingress response")
        result = activation.build_local_materialization_activation_receipt_v42r1(
            activation_plan=activation_plan,
            local_attempt=local,
            network_start=network,
            remote_attempt_id=remote[
                "remote_materialization_activation_attempt_id"
            ],
            ingress_result=ingress,
        )
        outcome_name = activation.LOCAL_ACTIVATION_RECEIPT_NAME
    except (V42MaterializationActivationDriverError, activation.V42MaterializationActivationError):
        result = activation.build_local_materialization_activation_ambiguity_v42r1(
            activation_plan=activation_plan,
            local_attempt=local,
            network_start=network,
            reason_code="SSH_OUTCOME_NOT_EXACT",
        )
        outcome_name = activation.LOCAL_ACTIVATION_AMBIGUITY_NAME
    if journal_publisher is None:
        assert journal is not None
        try:
            journal.verify_named()
            _write_once(journal.descriptor, outcome_name, result)
            journal.verify_named()
        finally:
            journal.close()
            journal = None
    else:
        journal_publisher("OUTCOME", result)
    return result


def execute_read_only_classification_v42r1(
    *, activation_plan: dict[str, Any], local_attempt: dict[str, Any],
    network_start: dict[str, Any], preformal_receipt: dict[str, Any], loader_path: str,
    receiver_path: str, evidence_root: str | None = None,
    preformal_plan: dict[str, Any] | None = None,
    preformal_attempt: dict[str, Any] | None = None,
    preformal_outcome: dict[str, Any] | None = None,
    resource_plan: dict[str, Any] | None = None,
    resource_result: dict[str, Any] | None = None,
    control_root: str | None = None,
    dispatch: Callable[..., dict[str, Any]] = _dispatch_read_only,
) -> dict[str, Any]:
    _verify_driver_self(activation_plan)
    if evidence_root is not None:
        existing_final = _read_existing_final_evidence(
            evidence_root=evidence_root,
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
            preformal_receipt=preformal_receipt,
        )
        if existing_final is not None:
            _final, selected = existing_final
            classification = selected.get("classification")
            if type(classification) is not dict:
                _fail("final activation evidence classification changed type")
            return classification
    _read_stable_program(loader_path, activation_plan["activation_loader_artifact"], "activation loader")
    receiver_raw = _read_stable_program(
        receiver_path, activation_plan["activation_receiver_artifact"], "activation receiver"
    )
    argv = activation.materialize_authorized_classifier_argv_v42r1(
        activation_plan=activation_plan,
        local_activation_attempt_id=local_attempt[
            "local_materialization_activation_attempt_id"
        ],
    )
    envelope = {
        "schema": "acfqp.v42_materialization_activation_classify_ingress.v42r1",
        "operation": "READ_ONLY_CLASSIFY_ACTIVATION",
        "activation_plan": activation_plan,
        "local_activation_attempt": local_attempt,
        "network_start": network_start,
    }
    observed = dispatch(
        plan=activation_plan, argv=argv, receiver_raw=receiver_raw, envelope=envelope
    )
    if (
        observed.get("remote_mutation_performed") is not False
        or observed.get("activation_retry_authorized") is not False
        or observed.get(
            "additional_durable_or_mutating_remote_process_started"
        ) is not False
    ):
        _fail("activation classifier observation changed effect semantics")
    documents = observed.get("remote_documents")
    if type(documents) is not dict:
        _fail("activation classifier omitted remote documents")
    fixed_root_evidence = observed.get("fixed_root_evidence")
    if (
        type(fixed_root_evidence) is not dict
        or set(fixed_root_evidence)
        != {
            "inventory_before",
            "inventory_after",
            "documents",
            "collected_subset_only_not_whole_tree",
        }
        or fixed_root_evidence.get("inventory_before")
        != fixed_root_evidence.get("inventory_after")
        or fixed_root_evidence.get("collected_subset_only_not_whole_tree") is not True
        or type(fixed_root_evidence.get("documents")) is not dict
    ):
        _fail("activation classifier fixed-root evidence changed")
    fixed_inventory = fixed_root_evidence["inventory_before"]
    if (
        type(fixed_inventory) is not list
        or fixed_inventory != sorted(set(fixed_inventory))
        or any(type(name) is not str or not name for name in fixed_inventory)
        or any(name not in fixed_inventory for name in fixed_root_evidence["documents"])
    ):
        _fail("activation classifier fixed-root evidence inventory changed")
    classification = activation.build_materialization_activation_classification_v42r1(
        activation_plan=activation_plan,
        local_attempt=local_attempt,
        network_start=network_start,
        preformal_receipt=preformal_receipt,
        remote_attempt=documents.get("remote_attempt"),
        service_receipt=documents.get("service_receipt"),
        publish_ready=documents.get("publish_ready"),
        terminal=documents.get("terminal"),
        failure=documents.get("failure"),
        observation_before=observed.get("observation_before"),
        observation_after=observed.get("observation_after"),
    )
    if evidence_root is not None:
        _persist_read_only_classification_evidence(
            evidence_root=evidence_root,
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
            preformal_receipt=preformal_receipt,
            observed=observed,
            classification=classification,
            preformal_plan=preformal_plan,
            preformal_attempt=preformal_attempt,
            preformal_outcome=preformal_outcome,
            resource_plan=resource_plan,
            resource_result=resource_result,
            control_root=control_root,
        )
    return classification


def _write_or_verify_document(
    directory_fd: int, name: str, document: dict[str, Any]
) -> None:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        try:
            _write_once(directory_fd, name, document)
            return
        except FileExistsError:
            pass
    _read_document_at(directory_fd, name, document)


_SNAPSHOT_NAME = re.compile(r"ACTIVATION_READ_ONLY_SNAPSHOT_([0-9]{8})\.json")
_FINAL_EVIDENCE_INDEX_NAME = "MATERIALIZATION_ACTIVATION_FINAL_EVIDENCE_INDEX.json"


def _read_snapshot_chain(
    directory_fd: int,
    *,
    activation_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    names = sorted(
        name for name in os.listdir(directory_fd) if _SNAPSHOT_NAME.fullmatch(name)
    )
    if len(names) > 4096:
        _fail("activation read-only snapshot chain exceeded its cap")
    previous_id: str | None = None
    documents: list[dict[str, Any]] = []
    for ordinal, name in enumerate(names, start=1):
        match = _SNAPSHOT_NAME.fullmatch(name)
        if match is None or int(match.group(1), 10) != ordinal:
            _fail("activation read-only snapshot ordinals changed")
        document = _read_document_stable_at(directory_fd, name)
        payload = dict(document)
        identity = payload.pop("activation_read_only_snapshot_id", None)
        if (
            document.get("schema")
            != "acfqp.v42_materialization_activation_read_only_snapshot.v42r1"
            or document.get("snapshot_ordinal") != ordinal
            or document.get("previous_snapshot_id") != previous_id
            or document.get("materialization_activation_plan_id")
            != activation_plan["materialization_activation_plan_id"]
            or type(identity) is not str
            or identity
            != hashlib.sha256(
                b"acfqp:v42-remote-ordinal2:activation-read-only-snapshot\0"
                + canonical_json_bytes(payload)
            ).hexdigest()
        ):
            _fail("activation read-only snapshot chain changed")
        previous_id = identity
        documents.append(document)
    return documents


def _append_read_only_snapshot(
    directory_fd: int,
    *,
    activation_plan: dict[str, Any],
    observed: dict[str, Any],
    classification: dict[str, Any],
) -> dict[str, Any]:
    chain = _read_snapshot_chain(directory_fd, activation_plan=activation_plan)
    latest = chain[-1] if chain else None
    if (
        latest is not None
        and latest.get("observation") == observed
        and latest.get("classification") == classification
    ):
        return latest
    if len(chain) >= 4096:
        _fail("activation read-only snapshot chain cannot append beyond its cap")
    ordinal = len(chain) + 1
    payload = {
        "schema": "acfqp.v42_materialization_activation_read_only_snapshot.v42r1",
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "snapshot_ordinal": ordinal,
        "previous_snapshot_id": (
            None
            if latest is None
            else latest["activation_read_only_snapshot_id"]
        ),
        "observation": observed,
        "classification": classification,
        "remote_observation_only": True,
        "activation_effect_replay_authorized": False,
    }
    document = {
        **payload,
        "activation_read_only_snapshot_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:activation-read-only-snapshot\0"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    name = f"ACTIVATION_READ_ONLY_SNAPSHOT_{ordinal:08d}.json"
    try:
        _write_once(directory_fd, name, document)
    except FileExistsError:
        _read_document_at(directory_fd, name, document)
    return document


def _read_verified_final_evidence_at(
    directory_fd: int,
    *,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
    preformal_receipt: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    try:
        final_before = os.stat(
            _FINAL_EVIDENCE_INDEX_NAME,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    final_identity = _file_identity(final_before)
    final = _read_document_stable_at(
        directory_fd,
        _FINAL_EVIDENCE_INDEX_NAME,
        expected_identity=final_identity,
    )
    expected_keys = {
        "schema",
        "materialization_activation_plan_id",
        "activation_read_only_snapshot_id",
        "activation_classification_id",
        "remote_materialization_transport_terminal_id",
        "remote_materialization_attempt_id",
        "materialization_terminal_id",
        "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified",
        "bootstrap_terminal_exact_shared_materialization_ids_verified",
        "bootstrap_launcher_consumed_activation_transport_terminal_id",
        "downstream_launcher_terminal_id_join_remains_defense_in_depth",
        "formal_evidence_bundle_complete_under_bounded_successor_claim",
        "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim",
        "materialization_activation_final_evidence_index_id",
    }
    payload = dict(final)
    claimed = payload.pop("materialization_activation_final_evidence_index_id", None)
    if (
        set(final) != expected_keys
        or final.get("schema")
        != "acfqp.v42_materialization_activation_final_evidence_index.v42r1"
        or final.get("materialization_activation_plan_id")
        != activation_plan["materialization_activation_plan_id"]
        or final.get(
            "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified"
        )
        is not True
        or final.get(
            "bootstrap_terminal_exact_shared_materialization_ids_verified"
        )
        is not True
        or final.get("bootstrap_launcher_consumed_activation_transport_terminal_id")
        is not False
        or final.get(
            "downstream_launcher_terminal_id_join_remains_defense_in_depth"
        )
        is not True
        or final.get(
            "formal_evidence_bundle_complete_under_bounded_successor_claim"
        )
        is not True
        or final.get(
            "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim"
        )
        is not True
        or type(claimed) is not str
        or claimed
        != hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:activation-final-evidence-index\0"
            + canonical_json_bytes(payload)
        ).hexdigest()
    ):
        _fail("final activation evidence index changed")
    snapshots = _read_snapshot_chain(
        directory_fd, activation_plan=activation_plan
    )
    if not snapshots:
        _fail("final activation evidence omitted its selected snapshot")
    selected = snapshots[-1]
    classification = selected.get("classification")
    observation = selected.get("observation")
    if (
        final.get("activation_read_only_snapshot_id")
        != selected.get("activation_read_only_snapshot_id")
        or type(classification) is not dict
        or type(observation) is not dict
        or classification.get("classification") != "COMPLETE_TRANSPORT_SUCCESS"
        or final.get("activation_classification_id")
        != classification.get("materialization_activation_classification_id")
        or final.get("remote_materialization_transport_terminal_id")
        != classification.get("remote_materialization_transport_terminal_id")
    ):
        _fail("final activation evidence does not select the snapshot chain tail")

    remote_mapping = observation.get("remote_documents")
    if type(remote_mapping) is not dict:
        _fail("final activation evidence omitted remote document facts")
    remote_names = {
        "remote_attempt": activation.REMOTE_ACTIVATION_ATTEMPT_NAME,
        "service_receipt": activation.REMOTE_ACTIVATION_SERVICE_RECEIPT_NAME,
        "publish_ready": activation.REMOTE_ACTIVATION_READY_NAME,
        "terminal": activation.REMOTE_ACTIVATION_TERMINAL_NAME,
        "failure": activation.REMOTE_ACTIVATION_FAILURE_NAME,
    }
    loaded: dict[str, dict[str, Any]] = {}
    identities: dict[str, tuple[int, ...]] = {}
    for key, name in remote_names.items():
        expected = remote_mapping.get(key)
        if expected is None:
            if key != "failure":
                _fail("final activation evidence omitted a success document")
            try:
                os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            _fail("final activation evidence contains a conflicting failure")
        if type(expected) is not dict:
            _fail("final activation evidence remote document changed type")
        identity = _file_identity(
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        )
        document = _read_document_stable_at(
            directory_fd, name, expected_identity=identity
        )
        if document != expected:
            _fail("final activation evidence remote document changed")
        loaded[name] = document
        identities[name] = identity
    expected_classification = (
        activation.build_materialization_activation_classification_v42r1(
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
            preformal_receipt=preformal_receipt,
            remote_attempt=remote_mapping["remote_attempt"],
            service_receipt=remote_mapping["service_receipt"],
            publish_ready=remote_mapping["publish_ready"],
            terminal=remote_mapping["terminal"],
            failure=None,
            observation_before=observation.get("observation_before"),
            observation_after=observation.get("observation_after"),
        )
    )
    if classification != expected_classification:
        _fail("final activation classification semantics changed")

    for name in (
        authority.SOURCE_MANIFEST_NAME,
        authority.TRANSPORT_MANIFEST_NAME,
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
        authority.MATERIALIZATION_TERMINAL_NAME,
    ):
        identity = _file_identity(
            os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        )
        loaded[name] = _read_document_stable_at(
            directory_fd, name, expected_identity=identity
        )
        identities[name] = identity
    bootstrap = _verified_bootstrap_success_for_final_index(
        activation_plan=activation_plan,
        classification=classification,
        documents=loaded,
    )
    if (
        bootstrap is None
        or final.get("remote_materialization_attempt_id")
        != bootstrap["remote_materialization_attempt_id"]
        or final.get("materialization_terminal_id")
        != bootstrap["materialization_terminal_id"]
    ):
        _fail("final activation bootstrap success join changed")
    for name, identity in identities.items():
        _read_document_at(
            directory_fd,
            name,
            loaded[name],
            expected_identity=identity,
        )
    if _read_snapshot_chain(
        directory_fd, activation_plan=activation_plan
    ) != snapshots:
        _fail("final activation snapshot chain changed during verification")
    _read_document_at(
        directory_fd,
        _FINAL_EVIDENCE_INDEX_NAME,
        final,
        expected_identity=final_identity,
    )
    return final, selected


def _verified_bootstrap_success_for_final_index(
    *,
    activation_plan: dict[str, Any],
    classification: dict[str, Any],
    documents: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if classification.get("classification") != "COMPLETE_TRANSPORT_SUCCESS":
        return None
    required = (
        authority.SOURCE_MANIFEST_NAME,
        authority.TRANSPORT_MANIFEST_NAME,
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
        authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
        authority.MATERIALIZATION_TERMINAL_NAME,
        activation.REMOTE_ACTIVATION_TERMINAL_NAME,
    )
    if any(name not in documents for name in required):
        return None
    source = authority.verify_source_manifest_v42r1(
        documents[authority.SOURCE_MANIFEST_NAME]
    )
    transport = authority.verify_transport_manifest_v42r1(
        documents[authority.TRANSPORT_MANIFEST_NAME], source_manifest=source
    )
    local = authority.verify_local_materialization_attempt_v42r1(
        documents[authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME],
        source_manifest=source,
        transport_manifest=transport,
    )
    remote = authority.verify_remote_materialization_attempt_v42r1(
        documents[authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME],
        local_materialization_attempt=local,
        source_manifest=source,
        transport_manifest=transport,
    )
    terminal = authority.verify_materialization_terminal_v42r1(
        documents[authority.MATERIALIZATION_TERMINAL_NAME],
        local_materialization_attempt=local,
        remote_materialization_attempt=remote,
        source_manifest=source,
        transport_manifest=transport,
    )
    activation_terminal = documents[activation.REMOTE_ACTIVATION_TERMINAL_NAME]
    if (
        activation_terminal.get("local_materialization_attempt_id")
        != local["local_materialization_attempt_id"]
        or activation_terminal.get("source_manifest_id") != source["source_manifest_id"]
        or activation_terminal.get("transport_manifest_id")
        != transport["transport_manifest_id"]
        or activation_terminal.get("trusted_bootstrap_outer_command")
        != activation_plan["trusted_bootstrap_outer_command"]
        or activation_terminal.get("trusted_bootstrap_outer_command")
        != authority.remote_bootstrap_outer_command_v42r1(transport)
        or activation_terminal.get("fixed_root_snapshot", {}).get("root_path")
        != str(authority.REMOTE_ROOT)
        or activation_plan.get("fixed_remote_root") != str(authority.REMOTE_ROOT)
        or activation_terminal.get(
            "terminal_verified_by_service_before_exact_outer_exec"
        )
        is not True
        or activation_terminal.get(
            "terminal_id_and_canonical_bytes_reverified_by_same_service_context_before_exec"
        )
        is not True
        or activation_terminal.get(
            "trusted_bootstrap_outer_exec_started_at_terminal_publication"
        )
        is not False
        or activation_terminal.get(
            "durable_terminal_authorizes_same_service_context_next_step_exact_outer_exec"
        )
        is not True
        or activation_terminal.get(
            "downstream_launcher_evidence_terminal_id_join_is_defense_in_depth"
        )
        is not True
        or activation_terminal.get(
            "downstream_launcher_evidence_terminal_id_join_implemented"
        )
        is not False
    ):
        _fail("activation terminal does not join bootstrap materialization success")
    return {
        "remote_materialization_attempt_id": remote[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": terminal["materialization_terminal_id"],
    }


def _read_existing_final_evidence(
    *,
    evidence_root: str,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
    preformal_receipt: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    try:
        pins = _open_lexical_directory(evidence_root)
    except FileNotFoundError:
        return None
    try:
        pins.verify_named()
        result = _read_verified_final_evidence_at(
            pins.descriptor,
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
            preformal_receipt=preformal_receipt,
        )
        pins.verify_named()
        return result
    finally:
        pins.close()


def _persist_read_only_classification_evidence(
    *,
    evidence_root: str,
    activation_plan: dict[str, Any],
    local_attempt: dict[str, Any],
    network_start: dict[str, Any],
    preformal_receipt: dict[str, Any],
    observed: dict[str, Any],
    classification: dict[str, Any],
    preformal_plan: dict[str, Any] | None = None,
    preformal_attempt: dict[str, Any] | None = None,
    preformal_outcome: dict[str, Any] | None = None,
    resource_plan: dict[str, Any] | None = None,
    resource_result: dict[str, Any] | None = None,
    control_root: str | None = None,
) -> None:
    if (
        type(evidence_root) is not str
        or not evidence_root.startswith("/")
        or ".." in evidence_root.split("/")
    ):
        _fail("activation evidence root changed")
    remote = observed.get("remote_documents")
    fixed = observed.get("fixed_root_evidence")
    if type(remote) is not dict or type(fixed) is not dict:
        _fail("activation evidence source documents changed")
    documents: dict[str, dict[str, Any]] = {
        preformal.PREFORMAL_RECEIPT_NAME: preformal_receipt,
        activation.LOCAL_ACTIVATION_PLAN_NAME: activation_plan,
        activation.LOCAL_ACTIVATION_ATTEMPT_NAME: local_attempt,
        activation.LOCAL_ACTIVATION_NETWORK_START_NAME: network_start,
    }
    upstream = {
        preformal.PREFORMAL_PLAN_NAME: preformal_plan,
        preformal.PREFORMAL_ATTEMPT_NAME: preformal_attempt,
        preformal.PREFORMAL_OUTCOME_NAME: preformal_outcome,
        "PREACTIVATION_RESOURCE_PROBE_PLAN.json": resource_plan,
        "PREACTIVATION_RESOURCE_RESULT.json": resource_result,
    }
    present_upstream = sum(value is not None for value in upstream.values())
    if present_upstream not in (0, len(upstream)):
        _fail("activation evidence upstream DAG is incomplete")
    if present_upstream:
        for name, value in upstream.items():
            if type(value) is not dict:
                _fail("activation evidence upstream document changed type")
            documents[name] = value
    if control_root is not None:
        if (
            type(control_root) is not str
            or not control_root.startswith("/")
            or ".." in control_root.split("/")
        ):
            _fail("activation evidence control root changed")
        control_reference = _verify_control_root_reference(
            control_root, activation_plan
        )
        documents["ACTIVATION_EVIDENCE_ROOTS.json"] = {
            "schema": "acfqp.v42_materialization_activation_evidence_roots.v42r1",
            "activation_evidence_root": evidence_root,
            "control_evidence_root": control_root,
            "preformal_evidence_root": evidence_root,
            "resource_evidence_root": evidence_root,
            "controls_are_retained_by_stable_reference_not_hardlink_or_copy": True,
            "expected_exact_control_names": list(preformal.CONTROL_NAMES),
            "control_reference_snapshot": control_reference,
            "formal_loader_must_reverify_all_control_bytes_and_storage": True,
            "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim": True,
        }
    remote_names = {
        "remote_attempt": activation.REMOTE_ACTIVATION_ATTEMPT_NAME,
        "service_receipt": activation.REMOTE_ACTIVATION_SERVICE_RECEIPT_NAME,
        "publish_ready": activation.REMOTE_ACTIVATION_READY_NAME,
        "terminal": activation.REMOTE_ACTIVATION_TERMINAL_NAME,
        "failure": activation.REMOTE_ACTIVATION_FAILURE_NAME,
    }
    for key, name in remote_names.items():
        value = remote.get(key)
        if value is not None:
            if type(value) is not dict:
                _fail("activation remote evidence document changed type")
            documents[name] = value
    fixed_documents = fixed.get("documents")
    if type(fixed_documents) is not dict:
        _fail("activation fixed-root evidence documents changed type")
    for name, value in fixed_documents.items():
        if (
            type(name) is not str
            or "/" in name
            or name in documents
            or type(value) is not dict
        ):
            _fail("activation fixed-root evidence name or document changed")
        documents[name] = value
    pinned = _secure_pinned_journal(evidence_root)
    descriptor = pinned.descriptor
    try:
        pinned.verify_named()
        existing_final = _read_verified_final_evidence_at(
            descriptor,
            activation_plan=activation_plan,
            local_attempt=local_attempt,
            network_start=network_start,
            preformal_receipt=preformal_receipt,
        )
        if existing_final is not None:
            _final, selected = existing_final
            if (
                selected.get("observation") != observed
                or selected.get("classification") != classification
            ):
                _fail(
                    "final activation evidence forbids a regressed or different observation"
                )
        for name in sorted(documents):
            _write_or_verify_document(descriptor, name, documents[name])
            pinned.verify_named()
        snapshot = _append_read_only_snapshot(
            descriptor,
            activation_plan=activation_plan,
            observed=observed,
            classification=classification,
        )
        bootstrap = _verified_bootstrap_success_for_final_index(
            activation_plan=activation_plan,
            classification=classification,
            documents=documents,
        )
        try:
            os.stat(
                _FINAL_EVIDENCE_INDEX_NAME,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
            final_exists = True
        except FileNotFoundError:
            final_exists = False
        if bootstrap is None:
            if final_exists:
                _fail("final activation evidence regressed after publication")
        else:
            final_payload = {
                "schema": "acfqp.v42_materialization_activation_final_evidence_index.v42r1",
                "materialization_activation_plan_id": activation_plan[
                    "materialization_activation_plan_id"
                ],
                "activation_read_only_snapshot_id": snapshot[
                    "activation_read_only_snapshot_id"
                ],
                "activation_classification_id": classification[
                    "materialization_activation_classification_id"
                ],
                "remote_materialization_transport_terminal_id": classification[
                    "remote_materialization_transport_terminal_id"
                ],
                **bootstrap,
                "activation_service_terminal_before_exact_bootstrap_exec_protocol_verified": True,
                "bootstrap_terminal_exact_shared_materialization_ids_verified": True,
                "bootstrap_launcher_consumed_activation_transport_terminal_id": False,
                "downstream_launcher_terminal_id_join_remains_defense_in_depth": True,
                "formal_evidence_bundle_complete_under_bounded_successor_claim": True,
                "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim": True,
            }
            final_index = {
                **final_payload,
                "materialization_activation_final_evidence_index_id": hashlib.sha256(
                    b"acfqp:v42-remote-ordinal2:activation-final-evidence-index\0"
                    + canonical_json_bytes(final_payload)
                ).hexdigest(),
            }
            _write_or_verify_document(
                descriptor, _FINAL_EVIDENCE_INDEX_NAME, final_index
            )
        os.fsync(descriptor)
        pinned.verify_named()
    finally:
        pinned.close()


def _load_request(path: str) -> dict[str, Any]:
    if type(path) is not str or not path.startswith("/") or ".." in path.split("/"):
        _fail("activation driver request path changed")
    before = os.lstat(path)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or not 0 < before.st_size <= MAXIMUM_DOCUMENT_BYTES
    ):
        _fail("activation driver request storage changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("activation driver request changed before open")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                _fail("activation driver request ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("activation driver request exceeded observed size")
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.lstat(path)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after_fd, field)
        or getattr(before, field) != getattr(after_path, field)
        for field in fields
    ):
        _fail("activation driver request changed while read")
    raw = b"".join(chunks)
    return _canonical_document(raw, "activation driver request")


def _read_regular_candidate(path: str, cap: int, label: str) -> bytes:
    if (
        type(path) is not str
        or not path.startswith("/")
        or ".." in path.split("/")
        or type(cap) is not int
        or cap <= 0
    ):
        _fail(label + " path or cap changed")
    before = os.lstat(path)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or not 0 < before.st_size <= cap
    ):
        _fail(label + " storage changed")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail(label + " changed before open")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail(label + " ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail(label + " exceeded observed size")
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.lstat(path)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    )
    if any(
        getattr(before, field) != getattr(after_fd, field)
        or getattr(before, field) != getattr(after_path, field)
        for field in fields
    ):
        _fail(label + " changed while read")
    return b"".join(chunks)


def _load_document_from_root(root: str, name: str) -> dict[str, Any]:
    pins = _open_lexical_directory(root)
    try:
        pins.verify_named()
        document = _read_document_stable_at(pins.descriptor, name)
        pins.verify_named()
        return document
    finally:
        pins.close()


_PREFORMAL_PREDECESSOR_CHAIN_NAME = "PREFORMAL_PREDECESSOR_CHAIN.json"
_PREFORMAL_SELECTED_DOCUMENT_NAMES = (
    preformal.PREFORMAL_PLAN_NAME,
    preformal.PREFORMAL_ATTEMPT_NAME,
    preformal.PREFORMAL_RECEIPT_NAME,
    preformal.PREFORMAL_OUTCOME_NAME,
)
_PREFORMAL_COMPLETE_SLOT_AUXILIARY_NAMES = (
    preformal.PREFORMAL_KNOWN_HOSTS_NAME,
    preformal.PREFORMAL_STREAM_HEADER_NAME,
    preformal.PREFORMAL_NETWORK_START_NAME,
)


def _read_predecessor_chain_at(
    directory_fd: int,
    *,
    expected_identity: tuple[int, ...] | None = None,
) -> tuple[list[dict[str, dict[str, Any]]], tuple[int, ...]]:
    name = _PREFORMAL_PREDECESSOR_CHAIN_NAME
    before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if expected_identity is not None and _file_identity(before) != expected_identity:
        _fail("pre-formal predecessor chain published inode changed")
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_IMODE(before.st_mode) != 0o400
        or before.st_uid != os.geteuid()
        or before.st_gid != os.getegid()
        or before.st_nlink != 1
        or not 0 < before.st_size <= MAXIMUM_DOCUMENT_BYTES
    ):
        _fail("pre-formal predecessor chain storage changed")
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=directory_fd,
    )
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _fail("pre-formal predecessor chain changed before open")
        raw = b""
        while len(raw) < before.st_size:
            chunk = os.read(descriptor, before.st_size - len(raw))
            if not chunk:
                _fail("pre-formal predecessor chain ended early")
            raw += chunk
        if os.read(descriptor, 1):
            _fail("pre-formal predecessor chain exceeded observed size")
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if _file_identity(before) != _file_identity(after_fd) or _file_identity(
        before
    ) != _file_identity(after_path):
        _fail("pre-formal predecessor chain changed while read")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V42MaterializationActivationDriverError(
            "pre-formal predecessor chain is not canonical"
        ) from error
    if type(value) is not list or canonical_json_bytes(value) != raw:
        _fail("pre-formal predecessor chain is not canonical")
    return value, _file_identity(after_path)


def _load_preformal_selected_bundle(
    root: str,
) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, dict[str, Any]]],
]:
    """Read the selected pre-formal chain as one pinned, revalidated snapshot."""

    pins = _open_lexical_directory(root)
    try:
        pins.verify_named()
        inventory_before = sorted(os.listdir(pins.descriptor))
        required = set(_PREFORMAL_SELECTED_DOCUMENT_NAMES)
        allowed = required | set(_PREFORMAL_COMPLETE_SLOT_AUXILIARY_NAMES)
        predecessor_present = _PREFORMAL_PREDECESSOR_CHAIN_NAME in inventory_before
        if predecessor_present:
            allowed.add(_PREFORMAL_PREDECESSOR_CHAIN_NAME)
        if not required.issubset(inventory_before) or set(inventory_before) not in (
            required | ({_PREFORMAL_PREDECESSOR_CHAIN_NAME} if predecessor_present else set()),
            allowed,
        ):
            _fail("selected pre-formal evidence inventory changed")
        documents: dict[str, dict[str, Any]] = {}
        identities: dict[str, tuple[int, ...]] = {}
        for name in _PREFORMAL_SELECTED_DOCUMENT_NAMES:
            document = _read_document_stable_at(pins.descriptor, name)
            identity = _file_identity(
                os.stat(name, dir_fd=pins.descriptor, follow_symlinks=False)
            )
            documents[name] = document
            identities[name] = identity
            pins.verify_named()
        if predecessor_present:
            predecessor, predecessor_identity = _read_predecessor_chain_at(
                pins.descriptor
            )
        else:
            predecessor = []
            predecessor_identity = None
        for name in _PREFORMAL_SELECTED_DOCUMENT_NAMES:
            _read_document_at(
                pins.descriptor,
                name,
                documents[name],
                expected_identity=identities[name],
            )
            pins.verify_named()
        if predecessor_identity is not None:
            final_predecessor, _ = _read_predecessor_chain_at(
                pins.descriptor, expected_identity=predecessor_identity
            )
            if final_predecessor != predecessor:
                _fail("pre-formal predecessor chain changed between reads")
        if sorted(os.listdir(pins.descriptor)) != inventory_before:
            _fail("selected pre-formal evidence inventory changed after read")
        pins.verify_named()
        return documents, predecessor
    finally:
        pins.close()


def _load_predecessor_chain(root: str) -> list[dict[str, dict[str, Any]]]:
    """Compatibility helper; production orchestration uses the grouped reader."""

    pins = _open_lexical_directory(root)
    try:
        pins.verify_named()
        try:
            value, identity = _read_predecessor_chain_at(pins.descriptor)
        except FileNotFoundError:
            return []
        final, _ = _read_predecessor_chain_at(
            pins.descriptor, expected_identity=identity
        )
        if final != value:
            _fail("pre-formal predecessor chain changed between reads")
        pins.verify_named()
        return value
    finally:
        pins.close()


def _load_control_raws(control_root: str) -> dict[str, bytes]:
    pins = _open_lexical_directory(control_root)
    try:
        pins.verify_named()
        if sorted(os.listdir(pins.descriptor)) != list(preformal.CONTROL_NAMES):
            _fail("retained local control inventory changed")
        result: dict[str, bytes] = {}
        for name in preformal.CONTROL_NAMES:
            before = os.stat(
                name, dir_fd=pins.descriptor, follow_symlinks=False
            )
            cap = _CONTROL_REFERENCE_CAPS[name]
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != os.geteuid()
                or before.st_gid != os.getegid()
                or before.st_nlink != 1
                or not 0 < before.st_size <= cap
            ):
                _fail("retained local control storage changed: " + name)
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=pins.descriptor,
            )
            try:
                opened = os.fstat(descriptor)
                if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                    _fail("retained local control changed before open")
                chunks: list[bytes] = []
                remaining = before.st_size
                while remaining:
                    chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                    if not chunk:
                        _fail("retained local control ended early: " + name)
                    chunks.append(chunk)
                    remaining -= len(chunk)
                if os.read(descriptor, 1):
                    _fail("retained local control exceeded observed size")
                after_fd = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            after_path = os.stat(
                name, dir_fd=pins.descriptor, follow_symlinks=False
            )
            if (
                _file_identity(before) != _file_identity(after_fd)
                or _file_identity(before) != _file_identity(after_path)
            ):
                _fail("retained local control changed while read: " + name)
            result[name] = b"".join(chunks)
            pins.verify_named()
        if sorted(os.listdir(pins.descriptor)) != list(preformal.CONTROL_NAMES):
            _fail("retained local control inventory changed after read")
        return result
    finally:
        pins.close()


def orchestrate_activation_from_retained_v42r1(
    *,
    preformal_evidence_root: str,
    expected_preformal_plan_id: str,
    control_root: str,
    resource_evidence_root: str,
    activation_evidence_root: str,
    preformal_loader_path: str,
    preformal_receiver_path: str,
    loader_path: str,
    receiver_path: str,
    service_path: str,
    activation_authority_path: str,
    resource_dispatch: Callable[..., dict[str, Any]] = _dispatch_read_only,
    prepared_dispatch_factory: Callable[..., _PreparedDispatch] = _prepare_dispatch,
    classification_dispatch: Callable[..., dict[str, Any]] = _dispatch_read_only,
) -> dict[str, Any]:
    """Build and durably advance the full local activation DAG from retained roots."""

    controls = _load_control_raws(control_root)
    preformal_loader_raw = _read_regular_candidate(
        preformal_loader_path, 4 * 1024**2, "pre-formal loader"
    )
    preformal_receiver_raw = _read_regular_candidate(
        preformal_receiver_path, 4 * 1024**2, "pre-formal receiver"
    )
    loader_raw = _read_regular_candidate(loader_path, 4 * 1024**2, "activation loader")
    receiver_raw = _read_regular_candidate(
        receiver_path, 4 * 1024**2, "activation receiver"
    )
    service_raw = _read_regular_candidate(
        service_path, 4 * 1024**2, "activation service"
    )
    driver_raw = _read_regular_candidate(
        os.path.abspath(__file__), 4 * 1024**2, "activation driver"
    )
    activation_authority_raw = _read_regular_candidate(
        activation_authority_path, 4 * 1024**2, "activation authority"
    )
    if (
        type(expected_preformal_plan_id) is not str
        or re.fullmatch(r"[0-9a-f]{64}", expected_preformal_plan_id) is None
    ):
        _fail("expected pre-formal plan identity changed")
    preformal_bundle, predecessor_chain = _load_preformal_selected_bundle(
        preformal_evidence_root
    )
    preformal_plan_document = preformal_bundle[preformal.PREFORMAL_PLAN_NAME]
    preformal_plan = preformal.verify_preformal_upload_plan_against_controls_v42r1(
        preformal_plan_document,
        control_raw_by_name=controls,
        loader_source_raw=preformal_loader_raw,
        receiver_source_raw=preformal_receiver_raw,
        predecessor_chain=predecessor_chain,
    )
    if preformal_plan.get("preformal_upload_plan_id") != expected_preformal_plan_id:
        _fail("selected pre-formal plan does not match the caller anchor")
    preformal_attempt = preformal.verify_preformal_upload_attempt_against_controls_v42r1(
        preformal_bundle[preformal.PREFORMAL_ATTEMPT_NAME],
        plan=preformal_plan,
        control_raw_by_name=controls,
        loader_source_raw=preformal_loader_raw,
        receiver_source_raw=preformal_receiver_raw,
        predecessor_chain=predecessor_chain,
    )
    preformal_receipt = preformal.verify_preformal_upload_receipt_against_controls_v42r1(
        preformal_bundle[preformal.PREFORMAL_RECEIPT_NAME],
        plan=preformal_plan,
        attempt=preformal_attempt,
        control_raw_by_name=controls,
        loader_source_raw=preformal_loader_raw,
        receiver_source_raw=preformal_receiver_raw,
        predecessor_chain=predecessor_chain,
    )
    preformal_outcome = preformal.verify_preformal_upload_outcome_v42r1(
        preformal_bundle[preformal.PREFORMAL_OUTCOME_NAME],
        plan=preformal_plan,
        attempt=preformal_attempt,
        receipt=preformal_receipt,
    )
    resource_plan = activation.build_preactivation_resource_probe_plan_v42r1(
        preformal_plan=preformal_plan,
        preformal_attempt=preformal_attempt,
        preformal_receipt=preformal_receipt,
        preformal_outcome=preformal_outcome,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        service_source_raw=service_raw,
        driver_source_raw=driver_raw,
        activation_authority_source_raw=activation_authority_raw,
        control_raw_by_name=controls,
    )
    resource_journal = _secure_pinned_journal(resource_evidence_root)
    try:
        _write_or_verify_document(
            resource_journal.descriptor,
            "PREACTIVATION_RESOURCE_PROBE_PLAN.json",
            resource_plan,
        )
        resource_journal.verify_named()
        try:
            resource_result = _read_document_stable_at(
                resource_journal.descriptor,
                "PREACTIVATION_RESOURCE_RESULT.json",
            )
            resource_result = activation.verify_preactivation_resource_result_v42r1(
                resource_result,
                resource_plan=resource_plan,
                preformal_receipt=preformal_receipt,
            )
        except FileNotFoundError:
            resource_result = execute_resource_probe_v42r1(
                resource_plan=resource_plan,
                preformal_receipt=preformal_receipt,
                loader_path=loader_path,
                receiver_path=receiver_path,
                dispatch=resource_dispatch,
            )
            _write_once(
                resource_journal.descriptor,
                "PREACTIVATION_RESOURCE_RESULT.json",
                resource_result,
            )
        resource_journal.verify_named()
    finally:
        resource_journal.close()
    activation_plan = activation.build_materialization_activation_plan_v42r1(
        preformal_plan=preformal_plan,
        preformal_attempt=preformal_attempt,
        preformal_receipt=preformal_receipt,
        preformal_outcome=preformal_outcome,
        resource_plan=resource_plan,
        resource_result=resource_result,
        control_raw_by_name=controls,
        loader_source_raw=loader_raw,
        receiver_source_raw=receiver_raw,
        service_source_raw=service_raw,
        driver_source_raw=driver_raw,
        activation_authority_source_raw=activation_authority_raw,
    )
    activation_outcome = execute_activation_v42r1(
        activation_plan=activation_plan,
        preformal_receipt=preformal_receipt,
        loader_path=loader_path,
        receiver_path=receiver_path,
        service_path=service_path,
        local_effective_uid=os.geteuid(),
        prepared_dispatch_factory=prepared_dispatch_factory,
    )
    local_attempt = activation.build_local_materialization_activation_attempt_v42r1(
        activation_plan=activation_plan, local_effective_uid=os.geteuid()
    )
    network_start = activation.build_materialization_activation_network_start_v42r1(
        activation_plan=activation_plan, local_attempt=local_attempt
    )
    classification = execute_read_only_classification_v42r1(
        activation_plan=activation_plan,
        local_attempt=local_attempt,
        network_start=network_start,
        preformal_receipt=preformal_receipt,
        loader_path=loader_path,
        receiver_path=receiver_path,
        evidence_root=activation_evidence_root,
        preformal_plan=preformal_plan,
        preformal_attempt=preformal_attempt,
        preformal_outcome=preformal_outcome,
        resource_plan=resource_plan,
        resource_result=resource_result,
        control_root=control_root,
        dispatch=classification_dispatch,
    )
    final_evidence = _read_existing_final_evidence(
        evidence_root=activation_evidence_root,
        activation_plan=activation_plan,
        local_attempt=local_attempt,
        network_start=network_start,
        preformal_receipt=preformal_receipt,
    )
    return {
        "schema": "acfqp.v42_materialization_activation_orchestration_result.v42r1",
        "preactivation_resource_probe_plan_id": resource_plan[
            "preactivation_resource_probe_plan_id"
        ],
        "preactivation_resource_result_id": resource_result[
            "preactivation_resource_result_id"
        ],
        "materialization_activation_plan_id": activation_plan[
            "materialization_activation_plan_id"
        ],
        "local_activation_outcome": activation_outcome,
        "read_only_classification": classification,
        "materialization_activation_final_evidence_index_id": (
            None
            if final_evidence is None
            else final_evidence[0][
                "materialization_activation_final_evidence_index_id"
            ]
        ),
        "activation_evidence_root": activation_evidence_root,
        "resource_evidence_root": resource_evidence_root,
        "control_root": control_root,
        "same_activation_identity_retry_forbidden": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--read-only-resource-probe", action="store_true")
    modes.add_argument("--activate-selected-receipt", action="store_true")
    modes.add_argument("--read-only-classify", action="store_true")
    modes.add_argument("--orchestrate-from-retained", action="store_true")
    parser.add_argument("--request")
    parser.add_argument("--preformal-evidence-root")
    parser.add_argument("--expected-preformal-plan-id")
    parser.add_argument("--control-root")
    parser.add_argument("--resource-evidence-root")
    parser.add_argument("--activation-evidence-root")
    parser.add_argument(
        "--preformal-loader-path",
        default=str(ROOT / preformal.PREFORMAL_LOADER_SOURCE_RELATIVE),
    )
    parser.add_argument(
        "--preformal-receiver-path",
        default=str(ROOT / preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE),
    )
    parser.add_argument(
        "--activation-loader-path",
        default=str(ROOT / "scripts/v42_materialization_activation_loader.py"),
    )
    parser.add_argument(
        "--activation-receiver-path",
        default=str(ROOT / "scripts/v42_materialization_activation_receiver.py"),
    )
    parser.add_argument(
        "--activation-service-path",
        default=str(ROOT / "scripts/v42_materialization_activation_service.py"),
    )
    parser.add_argument(
        "--activation-authority-path",
        default=str(
            ROOT
            / "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py"
        ),
    )
    args = parser.parse_args(argv)
    if args.orchestrate_from_retained:
        roots = (
            args.preformal_evidence_root,
            args.expected_preformal_plan_id,
            args.control_root,
            args.resource_evidence_root,
            args.activation_evidence_root,
        )
        if any(value is None for value in roots) or args.request is not None:
            _fail("retained orchestration roots changed or request was supplied")
        result = orchestrate_activation_from_retained_v42r1(
            preformal_evidence_root=args.preformal_evidence_root,
            expected_preformal_plan_id=args.expected_preformal_plan_id,
            control_root=args.control_root,
            resource_evidence_root=args.resource_evidence_root,
            activation_evidence_root=args.activation_evidence_root,
            preformal_loader_path=args.preformal_loader_path,
            preformal_receiver_path=args.preformal_receiver_path,
            loader_path=args.activation_loader_path,
            receiver_path=args.activation_receiver_path,
            service_path=args.activation_service_path,
            activation_authority_path=args.activation_authority_path,
        )
    else:
        if args.request is None:
            _fail("activation operation requires an exact request")
        request = _load_request(args.request)
        if args.read_only_resource_probe:
            result = execute_resource_probe_v42r1(**request)
        elif args.activate_selected_receipt:
            result = execute_activation_v42r1(
                **request, local_effective_uid=os.geteuid()
            )
        else:
            result = execute_read_only_classification_v42r1(**request)
    os.write(1, canonical_json_bytes(result) + b"\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except V42MaterializationActivationDriverError as error:
        os.write(2, ("activation driver rejected: " + str(error) + "\n").encode("utf-8"))
        raise SystemExit(71)
