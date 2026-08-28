#!/usr/bin/env python3
"""Source-bound, read-only V42 activation-successor finalizer.

This driver never invokes the activation ingress, systemd-run, or the trusted
bootstrap materializer.  Its only permitted remote operation is the
repeatable read-only successor inspection.  All durable writes are local,
O_EXCL publications in a new sibling evidence directory; the retained V42r1
activation collector is opened read-only and is never modified.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
from typing import Any, NoReturn

from acfqp import (
    construction_k7_standard_2048_activation_successor_v42r2 as successor,
)
from acfqp import (
    construction_k7_standard_2048_materialization_activation_v42r1 as activation,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from scripts import run_v42_materialization_activation as legacy_activation_driver


DOMAIN = "acfqp:v42-remote-ordinal2:"
SCHEMA_VERSION = "42.2.0"

LOCAL_ATTEMPT_SCHEMA = (
    "acfqp.v42_activation_successor_local_read_only_attempt.v42r2"
)
NETWORK_START_SCHEMA = (
    "acfqp.v42_activation_successor_read_only_network_start.v42r2"
)
EVIDENCE_ROOTS_SCHEMA = (
    "acfqp.v42_activation_successor_evidence_roots.v42r2"
)
INGRESS_SCHEMA = "acfqp.v42_activation_successor_read_only_ingress.v42r2"
INGRESS_OPERATION = "READ_ONLY_OBSERVE_NESTED_TERMINAL"

LOCAL_ATTEMPT_ID = "activation_successor_local_read_only_attempt_id"
NETWORK_START_ID = "activation_successor_read_only_network_start_id"
CONTROLLER_SOURCE_MANIFEST_NAME = "ACTIVATION_SUCCESSOR_SOURCE_MANIFEST.json"
PLAN_NAME = "ACTIVATION_SUCCESSOR_PLAN.json"
LOCAL_ATTEMPT_NAME = "ACTIVATION_SUCCESSOR_LOCAL_ATTEMPT.json"
NETWORK_START_NAME = "ACTIVATION_SUCCESSOR_NETWORK_START.00000001.json"
RECEIVER_OBSERVATION_NAME = (
    "ACTIVATION_SUCCESSOR_RECEIVER_OBSERVATION.00000001.json"
)
OBSERVATION_NAME = "ACTIVATION_SUCCESSOR_OBSERVATION.00000001.json"
PATH_RECEIPT_NAME = "ACTIVATION_SUCCESSOR_PATH_PROVENANCE_RECEIPT.00000001.json"
CLASSIFICATION_NAME = "ACTIVATION_SUCCESSOR_CLASSIFICATION.00000001.json"
SNAPSHOT_NAME = "ACTIVATION_SUCCESSOR_READ_ONLY_SNAPSHOT.00000001.json"
OBSERVED_REMOTE_ATTEMPT_NAME = (
    "SUCCESSOR_OBSERVED_REMOTE_MATERIALIZATION_ATTEMPT.json"
)
OBSERVED_SOURCE_TERMINAL_NAME = (
    "SUCCESSOR_OBSERVED_SOURCE_MATERIALIZATION_TERMINAL.json"
)
FINAL_INDEX_NAME = "ACTIVATION_SUCCESSOR_FINAL_EVIDENCE_INDEX.json"
LEGACY_CORE_ANCHOR_NAME = "ACTIVATION_SUCCESSOR_LEGACY_CORE_ANCHOR.json"
EVIDENCE_ROOTS_NAME = "ACTIVATION_SUCCESSOR_EVIDENCE_ROOTS.json"

PUBLICATION_ORDER = (
    CONTROLLER_SOURCE_MANIFEST_NAME,
    PLAN_NAME,
    LOCAL_ATTEMPT_NAME,
    NETWORK_START_NAME,
    RECEIVER_OBSERVATION_NAME,
    PATH_RECEIPT_NAME,
    OBSERVATION_NAME,
    OBSERVED_REMOTE_ATTEMPT_NAME,
    OBSERVED_SOURCE_TERMINAL_NAME,
    CLASSIFICATION_NAME,
    SNAPSHOT_NAME,
    FINAL_INDEX_NAME,
    LEGACY_CORE_ANCHOR_NAME,
    EVIDENCE_ROOTS_NAME,
)

PREDECESSOR_PLAN_NAME = activation.LOCAL_ACTIVATION_PLAN_NAME
PREDECESSOR_FINAL_NAME = "MATERIALIZATION_ACTIVATION_FINAL_EVIDENCE_INDEX.json"

MAXIMUM_DOCUMENT_BYTES = 64 * 1024**2
MAXIMUM_SOURCE_BYTES = 8 * 1024**2
SUCCESSOR_ROOT_PREFIX = ".acfqp-v42-local-activation-successor-"
ROOT = Path(__file__).resolve().parents[1]
LEGACY_ACTIVATION_DRIVER_RELATIVE = (
    "scripts/run_v42_materialization_activation.py"
)
_HEX64 = re.compile(r"[0-9a-f]{64}")


class V42ActivationSuccessorFinalizerError(RuntimeError):
    """The successor evidence DAG or its read-only boundary changed."""


def _fail(message: str) -> NoReturn:
    raise V42ActivationSuccessorFinalizerError(message)


def _canonical_document(raw_or_document: bytes | Mapping[str, Any], label: str) -> dict[str, Any]:
    try:
        if type(raw_or_document) is bytes:
            document = loads_canonical_json(raw_or_document)
            if canonical_json_bytes(document) != raw_or_document:
                _fail(label + " bytes are not canonical")
        elif isinstance(raw_or_document, Mapping):
            document = loads_canonical_json(canonical_json_bytes(dict(raw_or_document)))
        else:
            _fail(label + " changed type")
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42ActivationSuccessorFinalizerError(
            label + " is not canonical JSON"
        ) from error
    if type(document) is not dict:
        _fail(label + " is not an object")
    return document


def _content_document(
    payload: Mapping[str, Any], *, identity: str, domain_suffix: str
) -> dict[str, Any]:
    normalized = _canonical_document(dict(payload), identity + " payload")
    if identity in normalized:
        _fail(identity + " appeared inside its payload")
    return {
        **normalized,
        identity: hashlib.sha256(
            (DOMAIN + domain_suffix).encode("ascii")
            + b"\0"
            + canonical_json_bytes(normalized)
        ).hexdigest(),
    }


def _directory_identity(observed: os.stat_result) -> tuple[int, ...]:
    return (
        observed.st_dev, observed.st_ino, observed.st_mode,
        observed.st_uid, observed.st_gid,
    )


def _file_identity(observed: os.stat_result) -> tuple[int, ...]:
    return (
        observed.st_dev, observed.st_ino, observed.st_mode,
        observed.st_uid, observed.st_gid, observed.st_nlink,
        observed.st_size, observed.st_mtime_ns, observed.st_ctime_ns,
    )


def _identity_document(
    observed: os.stat_result, *, node_type: str, include_times: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "node_type": node_type,
        "mode": stat.S_IMODE(observed.st_mode),
        "uid": observed.st_uid,
        "gid": observed.st_gid,
        "st_dev": observed.st_dev,
        "st_ino": observed.st_ino,
        "st_nlink": observed.st_nlink,
        "st_size": observed.st_size,
    }
    if include_times:
        result.update(
            {
                "st_mtime_ns": observed.st_mtime_ns,
                "st_ctime_ns": observed.st_ctime_ns,
            }
        )
    return result


def _read_source_against_manifest(
    *, relative_path: str, source_manifest: Mapping[str, Any],
) -> bytes:
    facts = source_manifest.get("source_facts")
    if type(facts) is not list:
        _fail("successor source manifest facts changed")
    rows = [row for row in facts if row.get("relative_path") == relative_path]
    if len(rows) != 1 or type(rows[0]) is not dict:
        _fail("successor source manifest omitted an executable source")
    fact = rows[0]
    path = ROOT.joinpath(*relative_path.split("/"))
    before = path.lstat()
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
        | os.O_CLOEXEC,
    )
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o644
            or opened.st_uid != os.geteuid()
            or opened.st_gid != os.getegid()
            or opened.st_nlink != 1
            or not 0 < opened.st_size <= MAXIMUM_SOURCE_BYTES
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
        ):
            _fail("successor executable source storage changed: " + relative_path)
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail("successor executable source ended early: " + relative_path)
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("successor executable source grew while read: " + relative_path)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    final = path.lstat()
    if (
        _file_identity(before) != _file_identity(opened)
        or _file_identity(opened) != _file_identity(after)
        or _file_identity(after) != _file_identity(final)
    ):
        _fail("successor executable source changed while read: " + relative_path)
    raw = b"".join(chunks)
    expected = {
        "relative_path": relative_path,
        "git_mode": "100644",
        "git_object_type": "blob",
        "git_blob_oid": hashlib.sha1(  # noqa: S324 - Git identity
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if fact != expected:
        _fail("successor executable source differs from its source fact")
    return raw


@dataclass
class _DirectoryPin:
    path: Path
    chain: list[tuple[int, str | None, tuple[int, ...]]]

    @classmethod
    def open(cls, path: Path, *, mode: int = 0o700) -> "_DirectoryPin":
        if not path.is_absolute() or ".." in path.parts:
            _fail("evidence directory path changed")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open("/", flags)
        chain = [(descriptor, None, _directory_identity(os.fstat(descriptor)))]
        try:
            for component in path.parts[1:]:
                before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                child = os.open(component, flags, dir_fd=descriptor)
                opened = os.fstat(child)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or (before.st_dev, before.st_ino)
                    != (opened.st_dev, opened.st_ino)
                ):
                    os.close(child)
                    _fail("evidence directory changed while opening")
                chain.append((child, component, _directory_identity(opened)))
                descriptor = child
            root = os.fstat(descriptor)
            if (
                stat.S_IMODE(root.st_mode) != mode
                or root.st_uid != os.geteuid()
                or root.st_gid != os.getegid()
            ):
                _fail("evidence directory ownership or mode changed")
            result = cls(path=path, chain=chain)
            result.verify()
            return result
        except BaseException:
            for opened, _, _ in reversed(chain):
                os.close(opened)
            raise

    @property
    def descriptor(self) -> int:
        return self.chain[-1][0]

    def verify(self) -> None:
        for index, (descriptor, name, identity) in enumerate(self.chain):
            if _directory_identity(os.fstat(descriptor)) != identity:
                _fail("held evidence directory changed")
            if index:
                assert name is not None
                named = os.stat(
                    name, dir_fd=self.chain[index - 1][0], follow_symlinks=False
                )
                if _directory_identity(named) != identity:
                    _fail("named evidence directory changed")

    def inventory(self) -> list[str]:
        self.verify()
        result = sorted(os.listdir(self.descriptor))
        self.verify()
        return result

    def read(self, name: str, cap: int = MAXIMUM_DOCUMENT_BYTES) -> bytes:
        if not name or "/" in name or name in {".", ".."}:
            _fail("evidence filename changed")
        self.verify()
        named = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            dir_fd=self.descriptor,
        )
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o400
                or before.st_uid != os.geteuid()
                or before.st_gid != os.getegid()
                or before.st_nlink != 1
                or not 0 < before.st_size <= cap
                or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
            ):
                _fail("evidence file storage changed: " + name)
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    _fail("evidence file ended early: " + name)
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _fail("evidence file grew while read: " + name)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        if _file_identity(before) != _file_identity(after) or _file_identity(after) != _file_identity(final):
            _fail("evidence file changed while read: " + name)
        self.verify()
        return b"".join(chunks)

    def close(self) -> None:
        for descriptor, _, _ in reversed(self.chain):
            os.close(descriptor)
        self.chain.clear()


def _capture_read_only_root_state(pin: _DirectoryPin) -> dict[str, Any]:
    """Capture one stable metadata cut without reading unrelated contents."""

    pin.verify()
    root_before = os.fstat(pin.descriptor)
    inventory_before = pin.inventory()
    entries: dict[str, dict[str, Any]] = {}
    for name in inventory_before:
        observed = os.stat(name, dir_fd=pin.descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(observed.st_mode)
            or stat.S_IMODE(observed.st_mode) != 0o400
            or observed.st_uid != os.geteuid()
            or observed.st_gid != os.getegid()
            or observed.st_nlink != 1
            or observed.st_size <= 0
        ):
            _fail("retained predecessor entry storage changed: " + name)
        entries[name] = _identity_document(
            observed, node_type="REGULAR_FILE", include_times=True
        )
    inventory_after = pin.inventory()
    root_after = os.fstat(pin.descriptor)
    if (
        inventory_before != inventory_after
        or _directory_identity(root_before) != _directory_identity(root_after)
    ):
        _fail("retained predecessor root changed during metadata cut")
    for name in inventory_after:
        observed = os.stat(name, dir_fd=pin.descriptor, follow_symlinks=False)
        if entries[name] != _identity_document(
            observed, node_type="REGULAR_FILE", include_times=True
        ):
            _fail("retained predecessor entry changed during metadata cut")
    return {
        "root_identity": _identity_document(
            root_after, node_type="DIRECTORY", include_times=False
        ),
        "inventory": inventory_after,
        "entry_identities": entries,
    }


@dataclass
class _SuccessorJournal:
    pin: _DirectoryPin
    created: bool

    @classmethod
    def open_or_create(
        cls, path: Path, *, predecessor_root: Path
    ) -> "_SuccessorJournal":
        if (
            not path.is_absolute()
            or ".." in path.parts
            or path.parent != predecessor_root.parent
            or not path.name.startswith(SUCCESSOR_ROOT_PREFIX)
        ):
            _fail("successor evidence root is not an exact sibling")
        parent = _DirectoryPin.open(path.parent, mode=0o755)
        created = False
        try:
            previous_umask = os.umask(0o077)
            try:
                os.mkdir(path.name, 0o700, dir_fd=parent.descriptor)
                created = True
            except FileExistsError:
                pass
            finally:
                os.umask(previous_umask)
            if created:
                os.fsync(parent.descriptor)
            parent.verify()
        finally:
            parent.close()
        return cls(pin=_DirectoryPin.open(path), created=created)

    def publish_or_verify(self, name: str, document: Mapping[str, Any]) -> None:
        raw = canonical_json_bytes(dict(document))
        self.pin.verify()
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                0o400,
                dir_fd=self.pin.descriptor,
            )
        except FileExistsError:
            if self.pin.read(name, max(len(raw), 1)) != raw:
                _fail("retained successor artifact changed: " + name)
            return
        try:
            os.fchmod(descriptor, 0o400)
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    _fail("successor artifact publication made no progress")
                view = view[written:]
            os.fsync(descriptor)
            observed = os.fstat(descriptor)
            if (
                not stat.S_ISREG(observed.st_mode)
                or stat.S_IMODE(observed.st_mode) != 0o400
                or observed.st_uid != os.geteuid()
                or observed.st_gid != os.getegid()
                or observed.st_nlink != 1
                or observed.st_size != len(raw)
            ):
                _fail("published successor artifact storage changed")
            identity = _file_identity(observed)
        finally:
            os.close(descriptor)
        os.fsync(self.pin.descriptor)
        named = os.stat(name, dir_fd=self.pin.descriptor, follow_symlinks=False)
        if _file_identity(named) != identity:
            _fail("published successor artifact named inode changed")
        self.pin.verify()

    def verify_unique_files(self) -> None:
        identities: set[tuple[int, int]] = set()
        for name in self.pin.inventory():
            observed = os.stat(name, dir_fd=self.pin.descriptor, follow_symlinks=False)
            if not stat.S_ISREG(observed.st_mode):
                _fail("successor journal contains a nonregular entry")
            identity = (observed.st_dev, observed.st_ino)
            if identity in identities:
                _fail("successor journal files alias one inode")
            identities.add(identity)

    def verify_publication_prefix(self) -> None:
        inventory = self.pin.inventory()
        allowed_prefixes = {
            frozenset(PUBLICATION_ORDER[:length])
            for length in range(len(PUBLICATION_ORDER) + 1)
        }
        if frozenset(inventory) not in allowed_prefixes:
            _fail("successor journal is not one exact publication prefix")
        self.verify_unique_files()

    def close(self) -> None:
        self.pin.close()


def build_local_attempt_v42r2(
    *, successor_plan: Mapping[str, Any],
    controller_source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    source = successor.verify_activation_successor_source_manifest_v42r2(
        controller_source_manifest
    )
    plan_id = successor_plan.get("activation_successor_read_only_plan_id")
    if _HEX64.fullmatch(str(plan_id)) is None:
        _fail("activation successor plan identity changed")
    payload = {
        "schema": LOCAL_ATTEMPT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "activation_successor_read_only_plan_id": plan_id,
        "activation_successor_source_manifest_id": source[
            "activation_successor_source_manifest_id"
        ],
        "inspection_ordinal": 1,
        "read_only_remote_observation_only": True,
        "activation_effect_replay_authorized": False,
        "remote_root_creation_or_rebuild_authorized": False,
        "formal_effect_authorized_by_this_attempt": False,
    }
    return _content_document(
        payload,
        identity=LOCAL_ATTEMPT_ID,
        domain_suffix="activation-successor-local-read-only-attempt",
    )


def verify_local_attempt_v42r2(
    raw_or_document: bytes | Mapping[str, Any], *,
    successor_plan: Mapping[str, Any],
    controller_source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor local attempt")
    expected = build_local_attempt_v42r2(
        successor_plan=successor_plan,
        controller_source_manifest=controller_source_manifest,
    )
    if document != expected:
        _fail("successor local attempt changed")
    return document


def build_network_start_v42r2(
    *, successor_plan: Mapping[str, Any], local_attempt: Mapping[str, Any]
) -> dict[str, Any]:
    if (
        local_attempt.get("activation_successor_read_only_plan_id")
        != successor_plan.get("activation_successor_read_only_plan_id")
        or _HEX64.fullmatch(str(local_attempt.get(LOCAL_ATTEMPT_ID))) is None
    ):
        _fail("successor network start lost its local attempt join")
    payload = {
        "schema": NETWORK_START_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "activation_successor_read_only_plan_id": successor_plan[
            "activation_successor_read_only_plan_id"
        ],
        LOCAL_ATTEMPT_ID: local_attempt[LOCAL_ATTEMPT_ID],
        "inspection_ordinal": 1,
        "only_read_only_ssh_ingress_may_start_after_publication": True,
        "additional_or_durable_remote_process_authorized": False,
        "remote_filesystem_mutation_authorized": False,
        "activation_or_bootstrap_effect_replay_authorized": False,
    }
    return _content_document(
        payload,
        identity=NETWORK_START_ID,
        domain_suffix="activation-successor-read-only-network-start",
    )


def verify_network_start_v42r2(
    raw_or_document: bytes | Mapping[str, Any], *,
    successor_plan: Mapping[str, Any], local_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor network start")
    expected = build_network_start_v42r2(
        successor_plan=successor_plan, local_attempt=local_attempt
    )
    if document != expected:
        _fail("successor network start changed")
    return document


def build_evidence_roots_v42r2(
    *, predecessor_activation_evidence_root: Path,
    successor_evidence_root: Path,
    predecessor_state_before: Mapping[str, Any],
    predecessor_state_after: Mapping[str, Any],
    successor_plan: Mapping[str, Any],
    final_evidence_index: Mapping[str, Any],
    legacy_core_anchor: Mapping[str, Any],
) -> dict[str, Any]:
    before = _canonical_document(
        predecessor_state_before, "predecessor root state before"
    )
    after = _canonical_document(
        predecessor_state_after, "predecessor root state after"
    )
    if before != after:
        _fail("retained predecessor activation evidence changed")
    if (
        predecessor_activation_evidence_root.parent
        != successor_evidence_root.parent
        or predecessor_activation_evidence_root == successor_evidence_root
        or successor_evidence_root.name.startswith(SUCCESSOR_ROOT_PREFIX) is False
        or PREDECESSOR_FINAL_NAME in before.get("inventory", [])
    ):
        _fail("successor evidence roots changed")
    # The caller has just rebuilt the full pure chain; this local roots record
    # only repeats its already verified terminal joins.
    final = _canonical_document(final_evidence_index, "successor final")
    anchor = _canonical_document(legacy_core_anchor, "successor legacy anchor")
    plan_id = successor_plan.get("activation_successor_read_only_plan_id")
    final_id = final.get("activation_successor_final_evidence_index_id")
    anchor_id = anchor.get("activation_successor_legacy_core_anchor_id")
    if (
        _HEX64.fullmatch(str(plan_id)) is None
        or _HEX64.fullmatch(str(final_id)) is None
        or _HEX64.fullmatch(str(anchor_id)) is None
        or anchor.get("activation_successor_final_evidence_index_id") != final_id
    ):
        _fail("successor roots lost the native final or anchor join")
    return {
        "schema": EVIDENCE_ROOTS_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "predecessor_activation_evidence_root": str(
            predecessor_activation_evidence_root
        ),
        "successor_evidence_root": str(successor_evidence_root),
        "predecessor_root_identity_before": before["root_identity"],
        "predecessor_root_identity_after": after["root_identity"],
        "predecessor_inventory_before": before["inventory"],
        "predecessor_inventory_after": after["inventory"],
        "predecessor_entry_identities_before": before["entry_identities"],
        "predecessor_entry_identities_after": after["entry_identities"],
        "activation_successor_read_only_plan_id": plan_id,
        "activation_successor_final_evidence_index_id": final_id,
        "activation_successor_legacy_core_anchor_id": anchor_id,
        "expected_exact_successor_evidence_names": sorted(PUBLICATION_ORDER),
        "predecessor_activation_evidence_opened_read_only": True,
        "predecessor_activation_evidence_mutated": False,
        "predecessor_all_identities_and_inventory_equal_before_after": True,
        "successor_evidence_published_o_excl_mode_0400_and_fsynced": True,
        "legacy_snapshot_or_final_synthesized": False,
        "activation_effect_replayed": False,
        "remote_root_created_or_rebuilt": False,
    }


def verify_evidence_roots_v42r2(
    raw_or_document: bytes | Mapping[str, Any], **build_arguments: Any,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "successor evidence roots")
    expected = build_evidence_roots_v42r2(**build_arguments)
    if document != expected:
        _fail("successor evidence roots changed")
    return document


def _build_ingress(successor_plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": INGRESS_SCHEMA,
        "operation": INGRESS_OPERATION,
        "activation_successor_read_only_plan": dict(successor_plan),
    }


def _dispatch_read_only_successor(
    *, plan: dict[str, Any], argv: list[str], receiver_raw: bytes,
    envelope: dict[str, Any],
) -> dict[str, Any]:
    """Use the frozen descriptor-pinned OpenSSH pump for one read-only query."""

    return legacy_activation_driver._dispatch_read_only(  # noqa: SLF001
        plan=plan,
        argv=argv,
        receiver_raw=receiver_raw,
        envelope=envelope,
    )


def _load_predecessor_prefix(
    *, pin: _DirectoryPin, expected_plan_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = pin.inventory()
    if PREDECESSOR_FINAL_NAME in inventory:
        _fail("retained activation evidence already contains a legacy final")
    if PREDECESSOR_PLAN_NAME not in inventory:
        _fail("retained activation evidence omitted its plan")
    plan = _canonical_document(pin.read(PREDECESSOR_PLAN_NAME), "legacy plan")
    if plan.get("materialization_activation_plan_id") != expected_plan_id:
        _fail("retained activation plan differs from caller anchor")
    chain = legacy_activation_driver._read_snapshot_chain(  # noqa: SLF001
        pin.descriptor, activation_plan=plan
    )
    if not chain:
        _fail("retained activation evidence omitted its snapshot chain")
    return plan, chain[-1]


def _verify_legacy_dispatch_driver_source(
    *, legacy_plan: Mapping[str, Any], source_manifest: Mapping[str, Any],
) -> bytes:
    raw = _read_source_against_manifest(
        relative_path=LEGACY_ACTIVATION_DRIVER_RELATIVE,
        source_manifest=source_manifest,
    )
    artifact = legacy_plan.get("activation_driver_artifact")
    expected = {
        "relative_path": LEGACY_ACTIVATION_DRIVER_RELATIVE,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_oid": hashlib.sha1(  # noqa: S324 - Git identity
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
        "git_mode": "100644",
        "git_object_type": "blob",
    }
    if (
        type(artifact) is not dict
        or any(artifact.get(key) != value for key, value in expected.items())
    ):
        _fail("legacy dispatch driver differs from retained activation plan")
    return raw


def orchestrate_activation_successor_v42r2(
    *, predecessor_activation_evidence_root: Path,
    successor_evidence_root: Path,
    expected_legacy_activation_plan_id: str,
    controller_source_manifest: Mapping[str, Any],
    dispatch: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verify the retained prefix and construct the native successor DAG."""

    if (
        not isinstance(predecessor_activation_evidence_root, Path)
        or not isinstance(successor_evidence_root, Path)
        or not predecessor_activation_evidence_root.is_absolute()
        or not successor_evidence_root.is_absolute()
        or ".." in predecessor_activation_evidence_root.parts
        or ".." in successor_evidence_root.parts
        or _HEX64.fullmatch(expected_legacy_activation_plan_id) is None
    ):
        _fail("successor orchestration arguments changed")
    source_manifest = (
        successor.verify_activation_successor_source_manifest_v42r2(
            controller_source_manifest
        )
    )
    loader_raw = _read_source_against_manifest(
        relative_path=successor.SUCCESSOR_LOADER_RELATIVE,
        source_manifest=source_manifest,
    )
    receiver_raw = _read_source_against_manifest(
        relative_path=successor.SUCCESSOR_RECEIVER_RELATIVE,
        source_manifest=source_manifest,
    )
    predecessor = _DirectoryPin.open(
        predecessor_activation_evidence_root, mode=0o700
    )
    journal: _SuccessorJournal | None = None
    try:
        predecessor_before = _capture_read_only_root_state(predecessor)
        legacy_plan, legacy_snapshot_tail = _load_predecessor_prefix(
            pin=predecessor,
            expected_plan_id=expected_legacy_activation_plan_id,
        )
        _verify_legacy_dispatch_driver_source(
            legacy_plan=legacy_plan, source_manifest=source_manifest
        )
        plan_arguments = {
            "legacy_activation_plan": legacy_plan,
            "legacy_snapshot_tail": legacy_snapshot_tail,
            "successor_source_manifest": source_manifest,
            "successor_evidence_root": str(successor_evidence_root),
            "loader_source_raw": loader_raw,
            "receiver_source_raw": receiver_raw,
        }
        plan = successor.build_activation_successor_read_only_plan_v42r2(
            **plan_arguments
        )
        successor.verify_activation_successor_read_only_plan_v42r2(
            plan, **plan_arguments
        )
        journal = _SuccessorJournal.open_or_create(
            successor_evidence_root,
            predecessor_root=predecessor_activation_evidence_root,
        )
        journal.verify_publication_prefix()
        journal.publish_or_verify(
            CONTROLLER_SOURCE_MANIFEST_NAME, source_manifest
        )
        journal.publish_or_verify(PLAN_NAME, plan)
        local_attempt = build_local_attempt_v42r2(
            successor_plan=plan,
            controller_source_manifest=source_manifest,
        )
        journal.publish_or_verify(LOCAL_ATTEMPT_NAME, local_attempt)
        network_start = build_network_start_v42r2(
            successor_plan=plan, local_attempt=local_attempt
        )
        journal.publish_or_verify(NETWORK_START_NAME, network_start)

        if RECEIVER_OBSERVATION_NAME in journal.pin.inventory():
            raw_observation = successor.verify_activation_successor_receiver_observation_v42r2(
                journal.pin.read(RECEIVER_OBSERVATION_NAME)
            )
        else:
            ssh_argv = successor.materialize_activation_successor_ssh_argv_v42r2(
                plan, loader_source_raw=loader_raw
            )
            selected_dispatch = dispatch or _dispatch_read_only_successor
            observed = selected_dispatch(
                plan=plan,
                argv=ssh_argv,
                receiver_raw=receiver_raw,
                envelope=_build_ingress(plan),
            )
            raw_observation = successor.verify_activation_successor_receiver_observation_v42r2(
                dict(observed)
            )
            journal.publish_or_verify(
                RECEIVER_OBSERVATION_NAME, raw_observation
            )

        predecessor_after = _capture_read_only_root_state(predecessor)
        if predecessor_after != predecessor_before:
            _fail("retained activation evidence changed across successor query")
        if PREDECESSOR_FINAL_NAME in predecessor.inventory():
            _fail("legacy final appeared across successor query")

        receipt = successor.build_activation_successor_path_provenance_receipt_v42r2(
            plan=plan, receiver_observation=raw_observation
        )
        successor.verify_activation_successor_path_provenance_receipt_v42r2(
            receipt, plan=plan, receiver_observation=raw_observation
        )
        journal.publish_or_verify(PATH_RECEIPT_NAME, receipt)
        observation = successor.build_activation_successor_observation_v42r2(
            plan=plan, path_provenance_receipt=receipt
        )
        successor.verify_activation_successor_observation_v42r2(
            observation, plan=plan
        )
        journal.publish_or_verify(OBSERVATION_NAME, observation)
        documents = observation["documents"]
        journal.publish_or_verify(
            OBSERVED_REMOTE_ATTEMPT_NAME,
            documents[successor.REMOTE_ATTEMPT_RELATIVE_PATH],
        )
        journal.publish_or_verify(
            OBSERVED_SOURCE_TERMINAL_NAME,
            documents[successor.SOURCE_TERMINAL_RELATIVE_PATH],
        )
        classification = successor.build_activation_successor_classification_v42r2(
            plan=plan, observation=observation
        )
        successor.verify_activation_successor_classification_v42r2(
            classification, plan=plan, observation=observation
        )
        journal.publish_or_verify(CLASSIFICATION_NAME, classification)
        snapshot = successor.build_activation_successor_snapshot_v42r2(
            plan=plan,
            observation=observation,
            classification=classification,
        )
        successor.verify_activation_successor_snapshot_v42r2(
            snapshot,
            plan=plan,
            observation=observation,
            classification=classification,
        )
        journal.publish_or_verify(SNAPSHOT_NAME, snapshot)
        final = successor.build_activation_successor_final_evidence_index_v42r2(
            plan=plan, snapshot=snapshot, classification=classification
        )
        successor.verify_activation_successor_final_evidence_index_v42r2(
            final, plan=plan, snapshot=snapshot, classification=classification
        )
        journal.publish_or_verify(FINAL_INDEX_NAME, final)
        anchor = successor.build_activation_successor_legacy_core_anchor_v42r2(
            final_evidence_index=final,
            preactivation_resource_result_id=plan[
                "preactivation_resource_result_id"
            ],
        )
        successor.verify_activation_successor_legacy_core_anchor_v42r2(
            anchor,
            final_evidence_index=final,
            preactivation_resource_result_id=plan[
                "preactivation_resource_result_id"
            ],
        )
        journal.publish_or_verify(LEGACY_CORE_ANCHOR_NAME, anchor)
        roots = build_evidence_roots_v42r2(
            predecessor_activation_evidence_root=(
                predecessor_activation_evidence_root
            ),
            successor_evidence_root=successor_evidence_root,
            predecessor_state_before=predecessor_before,
            predecessor_state_after=predecessor_after,
            successor_plan=plan,
            final_evidence_index=final,
            legacy_core_anchor=anchor,
        )
        journal.publish_or_verify(EVIDENCE_ROOTS_NAME, roots)
        if journal.pin.inventory() != sorted(PUBLICATION_ORDER):
            _fail("successor final evidence inventory changed")
        journal.verify_unique_files()
        predecessor.verify()
        if _capture_read_only_root_state(predecessor) != predecessor_before:
            _fail("retained activation evidence changed before final return")
        return {
            "schema": "acfqp.v42_activation_successor_orchestration_result.v42r2",
            "activation_successor_read_only_plan_id": plan[
                "activation_successor_read_only_plan_id"
            ],
            "activation_successor_final_evidence_index_id": final[
                "activation_successor_final_evidence_index_id"
            ],
            "activation_successor_legacy_core_anchor_id": anchor[
                "activation_successor_legacy_core_anchor_id"
            ],
            "predecessor_activation_evidence_root": str(
                predecessor_activation_evidence_root
            ),
            "successor_evidence_root": str(successor_evidence_root),
            "remote_observation_only": True,
            "activation_effect_replayed": False,
            "legacy_activation_snapshot_or_final_synthesized": False,
        }
    finally:
        if journal is not None:
            journal.close()
        predecessor.close()
