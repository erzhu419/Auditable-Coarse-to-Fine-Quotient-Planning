"""Effectful local journal for the V42 pre-formal upload chain.

The authority documents are pure. This module is the unique cooperating
publisher that turns their token-independent ordinal slots into a durable
branch lock. A slot is unclaimed while it is empty; its first durable PLAN
selects the branch. Complete, fsynced pre-network prefixes may be resumed by
that exact branch. A network-start marker is never resumed here.

This module deliberately does not start SSH. A successor single-entry sender
must retain and recheck equivalent pins through marker publication and the
immediate fork/exec boundary before this transport can be called network-ready.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import fcntl
import os
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class V42PreformalJournalError(RuntimeError):
    pass


def _fail(message: str) -> NoReturn:
    raise V42PreformalJournalError(message)


def _basename(value: str, *, label: str) -> str:
    if not value or "/" in value or value in {".", ".."}:
        _fail(f"{label} basename changed")
    return value


def _basename_at_parent(path: str, parent: Path, *, label: str) -> str:
    parsed = Path(path)
    if parsed.parent != parent or parsed.name == "":
        _fail(f"{label} path escaped its registered parent")
    return _basename(parsed.name, label=label)


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(descriptor, raw[offset:])
        if written <= 0:
            _fail("pre-formal journal write made no progress")
        offset += written


def _file_state(observed: os.stat_result) -> tuple[int, ...]:
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_uid,
        observed.st_gid,
        observed.st_nlink,
        observed.st_size,
        observed.st_mtime_ns,
        observed.st_ctime_ns,
    )


def _file_fact(observed: os.stat_result, *, byte_count: int, label: str) -> None:
    if (
        not stat.S_ISREG(observed.st_mode)
        or stat.S_IMODE(observed.st_mode) != 0o400
        or observed.st_uid != os.geteuid()
        or observed.st_gid != os.getegid()
        or observed.st_nlink != 1
        or observed.st_size != byte_count
    ):
        _fail(f"{label} persisted metadata changed")


def _directory_fact(
    descriptor: int, *, mode: int | None, label: str
) -> os.stat_result:
    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode):
        _fail(f"{label} is not a directory")
    if mode is not None and (
        stat.S_IMODE(observed.st_mode) != mode
        or observed.st_uid != os.geteuid()
        or observed.st_gid != os.getegid()
        or observed.st_nlink < 2
    ):
        _fail(f"{label} directory fact changed")
    return observed


def _named_stat(parent_fd: int, name: str, *, label: str) -> os.stat_result:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as error:
        raise V42PreformalJournalError(
            f"{label} named identity is unavailable"
        ) from error


@dataclass(frozen=True)
class _DirectoryPin:
    parent_fd: int
    name: str
    descriptor: int
    identity: tuple[int, int]
    mode: int | None
    label: str


@dataclass(frozen=True)
class _FilePin:
    directory_fd: int
    name: str
    descriptor: int
    expected_raw: bytes
    state: tuple[int, ...]
    label: str


@dataclass
class _SlotPin:
    directory: _DirectoryPin
    files: dict[str, _FilePin] = field(default_factory=dict)


@dataclass
class _Snapshot:
    root_fd: int
    path_components: list[_DirectoryPin]
    parent_path: Path
    parent_fd: int
    chain: _DirectoryPin
    predecessor_slots: list[_SlotPin]
    current_slot: _SlotPin
    expected_chain_names: list[str]

    def close(self) -> None:
        file_fds: list[int] = []
        for slot in [*self.predecessor_slots, self.current_slot]:
            file_fds.extend(pin.descriptor for pin in slot.files.values())
        for descriptor in reversed(file_fds):
            try:
                os.close(descriptor)
            except OSError:
                pass
        for slot in reversed([*self.predecessor_slots, self.current_slot]):
            try:
                os.close(slot.directory.descriptor)
            except OSError:
                pass
        try:
            fcntl.flock(self.chain.descriptor, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(self.chain.descriptor)
        except OSError:
            pass
        for pin in reversed(self.path_components):
            try:
                os.close(pin.descriptor)
            except OSError:
                pass
        try:
            os.close(self.root_fd)
        except OSError:
            pass


def _verify_directory_pin(pin: _DirectoryPin) -> None:
    before = _directory_fact(pin.descriptor, mode=pin.mode, label=pin.label)
    if (before.st_dev, before.st_ino) != pin.identity:
        _fail(f"{pin.label} held identity changed")
    named = _named_stat(pin.parent_fd, pin.name, label=pin.label)
    if (
        not stat.S_ISDIR(named.st_mode)
        or (named.st_dev, named.st_ino) != pin.identity
    ):
        _fail(f"{pin.label} named identity changed")
    if pin.mode is not None and (
        stat.S_IMODE(named.st_mode) != pin.mode
        or named.st_uid != os.geteuid()
        or named.st_gid != os.getegid()
        or named.st_nlink < 2
    ):
        _fail(f"{pin.label} named directory fact changed")
    after = os.fstat(pin.descriptor)
    if (after.st_dev, after.st_ino) != pin.identity:
        _fail(f"{pin.label} identity changed during rejoin")


def _read_exact(descriptor: int, expected_raw: bytes, *, label: str) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = len(expected_raw)
    while remaining:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            _fail(f"{label} persisted bytes ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1) != b"" or b"".join(chunks) != expected_raw:
        _fail(f"{label} persisted bytes changed")


def _pin_file_at(
    directory_fd: int, name: str, expected_raw: bytes, *, label: str
) -> _FilePin:
    descriptor = -1
    try:
        descriptor = os.open(
            _basename(name, label=label),
            os.O_RDONLY
            | os.O_NONBLOCK
            | os.O_NOCTTY
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )
        before = os.fstat(descriptor)
        _file_fact(before, byte_count=len(expected_raw), label=label)
        named_before = _named_stat(directory_fd, name, label=label)
        if (named_before.st_dev, named_before.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            _fail(f"{label} opened and named identities differ")
        _read_exact(descriptor, expected_raw, label=label)
        after = os.fstat(descriptor)
        named_after = _named_stat(directory_fd, name, label=label)
        if (
            _file_state(after) != _file_state(before)
            or (named_after.st_dev, named_after.st_ino)
            != (after.st_dev, after.st_ino)
        ):
            _fail(f"{label} changed during readback")
        return _FilePin(
            directory_fd=directory_fd,
            name=name,
            descriptor=descriptor,
            expected_raw=expected_raw,
            state=_file_state(after),
            label=label,
        )
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _verify_file_pin(pin: _FilePin) -> None:
    before = os.fstat(pin.descriptor)
    _file_fact(before, byte_count=len(pin.expected_raw), label=pin.label)
    if _file_state(before) != pin.state:
        _fail(f"{pin.label} held file identity changed")
    named_before = _named_stat(pin.directory_fd, pin.name, label=pin.label)
    if (named_before.st_dev, named_before.st_ino) != (
        before.st_dev,
        before.st_ino,
    ):
        _fail(f"{pin.label} named file identity changed")
    _read_exact(pin.descriptor, pin.expected_raw, label=pin.label)
    after = os.fstat(pin.descriptor)
    named_after = _named_stat(pin.directory_fd, pin.name, label=pin.label)
    if (
        _file_state(after) != pin.state
        or (named_after.st_dev, named_after.st_ino)
        != (after.st_dev, after.st_ino)
    ):
        _fail(f"{pin.label} changed during final readback")


def _write_once_at(
    directory_fd: int, name: str, raw: bytes, *, label: str
) -> _FilePin:
    if not raw:
        _fail(f"{label} publication input changed")
    name = _basename(name, label=label)
    created_fd = -1
    pin: _FilePin | None = None
    prior_umask = os.umask(0o077)
    try:
        created_fd = os.open(
            name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o400,
            dir_fd=directory_fd,
        )
    except FileExistsError as error:
        os.umask(prior_umask)
        raise V42PreformalJournalError(
            f"{label} already exists; replay rejected"
        ) from error
    except BaseException:
        os.umask(prior_umask)
        raise
    else:
        os.umask(prior_umask)
    try:
        created_identity = os.fstat(created_fd)
        _write_all(created_fd, raw)
        os.fsync(created_fd)
        written = os.fstat(created_fd)
        _file_fact(written, byte_count=len(raw), label=label)
        if (written.st_dev, written.st_ino) != (
            created_identity.st_dev,
            created_identity.st_ino,
        ):
            _fail(f"{label} created descriptor identity changed")
        pin = _pin_file_at(directory_fd, name, raw, label=label)
        reopened = os.fstat(pin.descriptor)
        created_after_reopen = os.fstat(created_fd)
        named_after_reopen = _named_stat(directory_fd, name, label=label)
        identities = {
            (written.st_dev, written.st_ino),
            (reopened.st_dev, reopened.st_ino),
            (created_after_reopen.st_dev, created_after_reopen.st_ino),
            (named_after_reopen.st_dev, named_after_reopen.st_ino),
        }
        if len(identities) != 1:
            _fail(f"{label} created inode was replaced before readback")
        os.fsync(directory_fd)
        _verify_file_pin(pin)
        return pin
    except BaseException:
        if pin is not None:
            os.close(pin.descriptor)
        raise
    finally:
        if created_fd >= 0:
            os.close(created_fd)


def _open_directory_at(
    parent_fd: int, name: str, *, label: str, mode: int = 0o700
) -> _DirectoryPin:
    name = _basename(name, label=label)
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=parent_fd,
    )
    try:
        observed = _directory_fact(descriptor, mode=mode, label=label)
        pin = _DirectoryPin(
            parent_fd=parent_fd,
            name=name,
            descriptor=descriptor,
            identity=(observed.st_dev, observed.st_ino),
            mode=mode,
            label=label,
        )
        _verify_directory_pin(pin)
        return pin
    except BaseException:
        os.close(descriptor)
        raise


def _create_directory_at(
    parent_fd: int, name: str, *, label: str
) -> _DirectoryPin:
    name = _basename(name, label=label)
    prior_umask = os.umask(0o077)
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
    except FileExistsError as error:
        raise V42PreformalJournalError(
            f"{label} already exists; branch or replay rejected"
        ) from error
    finally:
        os.umask(prior_umask)
    pin = _open_directory_at(parent_fd, name, label=label)
    try:
        _verify_directory_pin(pin)
        os.fsync(pin.descriptor)
        os.fsync(parent_fd)
        return pin
    except BaseException:
        os.close(pin.descriptor)
        raise


def _open_absolute_parent(plan: dict[str, Any]) -> tuple[Path, int, list[_DirectoryPin]]:
    parent = Path(plan["local_transport_parent"])
    if parent != transport.LOCAL_TRANSPORT_PARENT or not parent.is_absolute():
        _fail("pre-formal local transport parent changed")
    parts = parent.parts
    if not parts or parts[0] != "/" or any(
        part in {"", ".", ".."} or "/" in part for part in parts[1:]
    ):
        _fail("pre-formal local transport parent is not canonical absolute")
    root_fd = os.open(
        "/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    pins: list[_DirectoryPin] = []
    current_fd = root_fd
    try:
        for index, component in enumerate(parts[1:], start=1):
            descriptor = -1
            try:
                descriptor = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current_fd,
                )
                observed = _directory_fact(
                    descriptor,
                    mode=None,
                    label=f"local transport ancestor {index}",
                )
                pin = _DirectoryPin(
                    parent_fd=current_fd,
                    name=component,
                    descriptor=descriptor,
                    identity=(observed.st_dev, observed.st_ino),
                    mode=None,
                    label=f"local transport ancestor {index}",
                )
                _verify_directory_pin(pin)
            except BaseException:
                if descriptor >= 0:
                    os.close(descriptor)
                raise
            pins.append(pin)
            current_fd = descriptor
        parent_fact = os.fstat(current_fd)
        if (
            parent_fact.st_uid != os.geteuid()
            or parent_fact.st_gid != os.getegid()
            or stat.S_IMODE(parent_fact.st_mode) & 0o002
        ):
            _fail("pre-formal local transport parent is not safely owned")
        return parent, root_fd, pins
    except BaseException:
        for pin in reversed(pins):
            os.close(pin.descriptor)
        os.close(root_fd)
        raise


def _verify_parent_path(snapshot: _Snapshot) -> None:
    _verify_parent_components(snapshot.path_components, snapshot.parent_fd)


def _verify_parent_components(
    path_components: list[_DirectoryPin], parent_fd: int
) -> None:
    for pin in path_components:
        _verify_directory_pin(pin)
    observed = os.fstat(parent_fd)
    if (
        observed.st_uid != os.geteuid()
        or observed.st_gid != os.getegid()
        or stat.S_IMODE(observed.st_mode) & 0o002
    ):
        _fail("pre-formal local transport parent safety changed")


def _base_publications(
    *, plan: dict[str, Any], attempt: dict[str, Any], header: dict[str, Any]
) -> list[tuple[str, bytes]]:
    # PLAN is first so a generic known-hosts prefix cannot select a branch.
    return [
        (transport.PREFORMAL_PLAN_NAME, canonical_json_bytes(plan)),
        (
            transport.PREFORMAL_KNOWN_HOSTS_NAME,
            transport.PINNED_KNOWN_HOSTS_BYTES,
        ),
        (transport.PREFORMAL_ATTEMPT_NAME, canonical_json_bytes(attempt)),
        (transport.PREFORMAL_STREAM_HEADER_NAME, canonical_json_bytes(header)),
    ]


def _expected_predecessor_publications(
    row: dict[str, dict[str, Any]],
) -> list[tuple[str, bytes]]:
    plan = row["plan"]
    attempt = row["attempt"]
    header = transport._stream_header_from_verified_documents(  # noqa: SLF001
        plan=plan, attempt=attempt
    )
    publications = _base_publications(
        plan=plan, attempt=attempt, header=header
    )
    if row["outcome"]["abandonment_reason_code"] != (
        transport.PREFORMAL_ABANDONMENT_REASON_LOCAL
    ):
        publications.append(
            (
                transport.PREFORMAL_NETWORK_START_NAME,
                canonical_json_bytes(
                    transport._network_start_from_verified_documents(  # noqa: SLF001
                        plan=plan, attempt=attempt
                    )
                ),
            )
        )
    publications.append(
        (
            transport.PREFORMAL_OUTCOME_NAME,
            canonical_json_bytes(row["outcome"]),
        )
    )
    return publications


def _pin_slot_exact(
    directory: _DirectoryPin,
    publications: list[tuple[str, bytes]],
    *,
    label: str,
) -> _SlotPin:
    expected_names = [name for name, _ in publications]
    if sorted(os.listdir(directory.descriptor)) != sorted(expected_names):
        _fail(f"{label} inventory changed")
    slot = _SlotPin(directory=directory)
    try:
        for name, raw in publications:
            slot.files[name] = _pin_file_at(
                directory.descriptor,
                name,
                raw,
                label=f"{label} {name}",
            )
        _verify_slot(slot)
        return slot
    except BaseException:
        for pin in slot.files.values():
            os.close(pin.descriptor)
        raise


def _pin_slot_prefix(
    slot: _SlotPin,
    publications: list[tuple[str, bytes]],
    *,
    label: str,
) -> int:
    observed = set(os.listdir(slot.directory.descriptor))
    names = [name for name, _ in publications]
    prefix_length = next(
        (
            length
            for length in range(len(names) + 1)
            if observed == set(names[:length])
        ),
        None,
    )
    if prefix_length is None:
        _fail(f"{label} inventory is not an exact publication prefix")
    try:
        for name, raw in publications[:prefix_length]:
            slot.files[name] = _pin_file_at(
                slot.directory.descriptor,
                name,
                raw,
                label=f"{label} {name}",
            )
        _verify_slot(slot)
        return prefix_length
    except BaseException:
        for pin in slot.files.values():
            os.close(pin.descriptor)
        slot.files.clear()
        raise


def _verify_slot(slot: _SlotPin) -> None:
    _verify_directory_pin(slot.directory)
    expected_names = sorted(slot.files)
    if sorted(os.listdir(slot.directory.descriptor)) != expected_names:
        _fail(f"{slot.directory.label} inventory changed")
    for pin in slot.files.values():
        _verify_file_pin(pin)
    if sorted(os.listdir(slot.directory.descriptor)) != expected_names:
        _fail(f"{slot.directory.label} inventory changed during verification")
    _verify_directory_pin(slot.directory)


def _verify_snapshot(snapshot: _Snapshot) -> None:
    _verify_parent_path(snapshot)
    _verify_directory_pin(snapshot.chain)
    if sorted(os.listdir(snapshot.chain.descriptor)) != sorted(
        snapshot.expected_chain_names
    ):
        _fail("pre-formal local chain inventory changed")
    for slot in snapshot.predecessor_slots:
        _verify_slot(slot)
    _verify_slot(snapshot.current_slot)
    if sorted(os.listdir(snapshot.chain.descriptor)) != sorted(
        snapshot.expected_chain_names
    ):
        _fail("pre-formal local chain inventory changed during snapshot")
    _verify_directory_pin(snapshot.chain)
    _verify_parent_path(snapshot)


def _verify_snapshot_structure(snapshot: _Snapshot) -> None:
    """Verify the held tree before the current slot inventory is classified."""

    _verify_parent_path(snapshot)
    _verify_directory_pin(snapshot.chain)
    if sorted(os.listdir(snapshot.chain.descriptor)) != sorted(
        snapshot.expected_chain_names
    ):
        _fail("pre-formal local chain inventory changed")
    for slot in snapshot.predecessor_slots:
        _verify_slot(slot)
    _verify_directory_pin(snapshot.current_slot.directory)
    if sorted(os.listdir(snapshot.chain.descriptor)) != sorted(
        snapshot.expected_chain_names
    ):
        _fail("pre-formal local chain inventory changed during snapshot")
    _verify_directory_pin(snapshot.chain)
    _verify_parent_path(snapshot)


def _durable_verify(snapshot: _Snapshot) -> None:
    for slot in [*snapshot.predecessor_slots, snapshot.current_slot]:
        for pin in slot.files.values():
            os.fsync(pin.descriptor)
            _verify_file_pin(pin)
        os.fsync(slot.directory.descriptor)
    os.fsync(snapshot.chain.descriptor)
    os.fsync(snapshot.parent_fd)
    _verify_snapshot(snapshot)


def _durable_verify_predecessors_before_successor_birth(
    *,
    path_components: list[_DirectoryPin],
    parent_fd: int,
    chain: _DirectoryPin,
    predecessor_slots: list[_SlotPin],
    expected_prior_names: list[str],
) -> None:
    """Make the complete predecessor chain durable before creating a slot."""

    for slot in predecessor_slots:
        for pin in slot.files.values():
            os.fsync(pin.descriptor)
            _verify_file_pin(pin)
        os.fsync(slot.directory.descriptor)
    os.fsync(chain.descriptor)
    os.fsync(parent_fd)
    _verify_parent_components(path_components, parent_fd)
    _verify_directory_pin(chain)
    if sorted(os.listdir(chain.descriptor)) != sorted(expected_prior_names):
        _fail("pre-formal predecessor inventory changed before successor birth")
    for slot in predecessor_slots:
        _verify_slot(slot)
    if sorted(os.listdir(chain.descriptor)) != sorted(expected_prior_names):
        _fail("pre-formal predecessor inventory changed during durability gate")
    _verify_directory_pin(chain)
    _verify_parent_components(path_components, parent_fd)


def _open_snapshot(
    *,
    plan: dict[str, Any],
    predecessor_chain: list[dict[str, dict[str, Any]]],
    create_current_if_absent: bool,
) -> _Snapshot:
    parent_path, root_fd, path_components = _open_absolute_parent(plan)
    parent_fd = path_components[-1].descriptor if path_components else root_fd
    chain: _DirectoryPin | None = None
    predecessor_slots: list[_SlotPin] = []
    current_directory: _DirectoryPin | None = None
    try:
        chain_name = _basename_at_parent(
            plan["local_chain_root"],
            parent_path,
            label="pre-formal chain root",
        )
        try:
            chain = _open_directory_at(
                parent_fd, chain_name, label="pre-formal chain root"
            )
        except FileNotFoundError:
            if plan["preformal_upload_ordinal"] != 1:
                _fail("pre-formal predecessor chain root is absent")
            chain = _create_directory_at(
                parent_fd, chain_name, label="pre-formal chain root"
            )
        fcntl.flock(chain.descriptor, fcntl.LOCK_EX)
        expected_prior_names = [
            f"{transport.PREFORMAL_LOCAL_ORDINAL_SLOT_PREFIX}{ordinal:08d}"
            for ordinal in range(1, plan["preformal_upload_ordinal"])
        ]
        current_name = _basename_at_parent(
            plan["local_ordinal_slot"],
            Path(plan["local_chain_root"]),
            label="pre-formal ordinal slot",
        )
        observed_chain = sorted(os.listdir(chain.descriptor))
        absent_inventory = sorted(expected_prior_names)
        present_inventory = sorted([*expected_prior_names, current_name])
        if observed_chain != absent_inventory and observed_chain != present_inventory:
            _fail("pre-formal local chain inventory is not contiguous and exact")
        for ordinal, row in enumerate(predecessor_chain, start=1):
            slot_name = expected_prior_names[ordinal - 1]
            directory = _open_directory_at(
                chain.descriptor,
                slot_name,
                label=f"pre-formal ordinal {ordinal} slot",
            )
            try:
                pinned_slot = _pin_slot_exact(
                    directory,
                    _expected_predecessor_publications(row),
                    label=f"pre-formal predecessor ordinal {ordinal}",
                )
            except BaseException:
                os.close(directory.descriptor)
                raise
            predecessor_slots.append(pinned_slot)
        if observed_chain == absent_inventory:
            if not create_current_if_absent:
                _fail("pre-formal current ordinal slot is absent")
            _durable_verify_predecessors_before_successor_birth(
                path_components=path_components,
                parent_fd=parent_fd,
                chain=chain,
                predecessor_slots=predecessor_slots,
                expected_prior_names=expected_prior_names,
            )
            current_directory = _create_directory_at(
                chain.descriptor,
                current_name,
                label="pre-formal current ordinal slot",
            )
        else:
            current_directory = _open_directory_at(
                chain.descriptor,
                current_name,
                label="pre-formal current ordinal slot",
            )
        snapshot = _Snapshot(
            root_fd=root_fd,
            path_components=path_components,
            parent_path=parent_path,
            parent_fd=parent_fd,
            chain=chain,
            predecessor_slots=predecessor_slots,
            current_slot=_SlotPin(directory=current_directory),
            expected_chain_names=[*expected_prior_names, current_name],
        )
        _verify_snapshot_structure(snapshot)
        return snapshot
    except BaseException:
        for slot in predecessor_slots:
            for pin in slot.files.values():
                os.close(pin.descriptor)
            os.close(slot.directory.descriptor)
        if current_directory is not None:
            os.close(current_directory.descriptor)
        if chain is not None:
            try:
                fcntl.flock(chain.descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(chain.descriptor)
        for pin in reversed(path_components):
            os.close(pin.descriptor)
        os.close(root_fd)
        raise


def _contextual_documents(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, dict[str, Any]]],
]:
    caller_chain = [] if predecessor_chain is None else predecessor_chain
    # Detach the effectful snapshot from caller-owned mutable containers before
    # the first contextual verification.  Every later verifier and dirfd pin
    # consumes this one canonical value graph.
    chain = loads_canonical_json(canonical_json_bytes(caller_chain))
    if type(chain) is not list:
        _fail("pre-formal predecessor chain changed type")
    plan = transport.verify_preformal_upload_plan_against_controls_v42r1(
        plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=chain,
    )
    attempt = transport.verify_preformal_upload_attempt_against_controls_v42r1(
        attempt,
        plan=plan,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=chain,
    )
    header = transport.build_preformal_upload_stream_header_v42r1(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=chain,
    )
    return plan, attempt, header, chain


@dataclass
class HeldNetworkStartBoundaryV42r1:
    """Hold the exact journal snapshot through marker publication and exec."""

    _snapshot: _Snapshot
    _start: dict[str, Any]
    _marker_raw: bytes
    _closed: bool = False
    marker_effect_may_have_started: bool = False
    marker_published: bool = False

    def __enter__(self) -> "HeldNetworkStartBoundaryV42r1":
        if self._closed:
            _fail("pre-formal held network boundary was already closed")
        return self

    def __exit__(
        self,
        _exception_type: object,
        _exception: object,
        _traceback: object,
    ) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._snapshot.close()

    def verify_exact(self, *, durable: bool = False) -> None:
        if self._closed:
            _fail("pre-formal held network boundary is closed")
        if durable:
            _durable_verify(self._snapshot)
        else:
            _verify_snapshot(self._snapshot)

    def publish_once(self) -> dict[str, Any]:
        if self._closed:
            _fail("pre-formal held network boundary is closed")
        if self.marker_effect_may_have_started or self.marker_published:
            _fail("pre-formal held network marker replay was attempted")
        self.verify_exact()
        self.marker_effect_may_have_started = True
        marker_pin = _write_once_at(
            self._snapshot.current_slot.directory.descriptor,
            transport.PREFORMAL_NETWORK_START_NAME,
            self._marker_raw,
            label=transport.PREFORMAL_NETWORK_START_NAME,
        )
        self._snapshot.current_slot.files[
            transport.PREFORMAL_NETWORK_START_NAME
        ] = marker_pin
        self.marker_published = True
        self.verify_exact(durable=True)
        return loads_canonical_json(canonical_json_bytes(self._start))


@dataclass(frozen=True)
class PreformalJournalInspectionV42r1:
    state: str
    pre_network_prefix_length: int
    receipt: dict[str, Any] | None
    outcome: dict[str, Any] | None


def _pin_bounded_unknown_file_at(
    directory_fd: int,
    name: str,
    *,
    maximum_byte_count: int,
    label: str,
) -> tuple[_FilePin, bytes]:
    descriptor = -1
    try:
        descriptor = os.open(
            _basename(name, label=label),
            os.O_RDONLY
            | os.O_NONBLOCK
            | os.O_NOCTTY
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )
        before = os.fstat(descriptor)
        if not 0 < before.st_size <= maximum_byte_count:
            _fail(f"{label} persisted size exceeds its recovery cap")
        _file_fact(before, byte_count=before.st_size, label=label)
        named_before = _named_stat(directory_fd, name, label=label)
        if (named_before.st_dev, named_before.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            _fail(f"{label} opened and named identities differ")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                _fail(f"{label} persisted bytes ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1) != b"":
            _fail(f"{label} persisted bytes exceed stat size")
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        named_after = _named_stat(directory_fd, name, label=label)
        if (
            _file_state(after) != _file_state(before)
            or (named_after.st_dev, named_after.st_ino)
            != (after.st_dev, after.st_ino)
        ):
            _fail(f"{label} changed during bounded recovery read")
        return (
            _FilePin(
                directory_fd=directory_fd,
                name=name,
                descriptor=descriptor,
                expected_raw=raw,
                state=_file_state(after),
                label=label,
            ),
            raw,
        )
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def inspect_preformal_upload_journal_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> PreformalJournalInspectionV42r1:
    plan, attempt, header, chain = _contextual_documents(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    base = _base_publications(plan=plan, attempt=attempt, header=header)
    marker = (
        transport.PREFORMAL_NETWORK_START_NAME,
        canonical_json_bytes(
            transport.build_preformal_network_start_v42r1(
                plan=plan,
                attempt=attempt,
                control_raw_by_name=control_raw_by_name,
                loader_source_raw=loader_source_raw,
                receiver_source_raw=receiver_source_raw,
                predecessor_chain=chain,
            )
        ),
    )
    snapshot = _open_snapshot(
        plan=plan,
        predecessor_chain=chain,
        create_current_if_absent=False,
    )
    try:
        observed = set(os.listdir(snapshot.current_slot.directory.descriptor))
        base_names = [name for name, _raw in base]
        prefix_length = next(
            (
                length
                for length in range(len(base_names) + 1)
                if observed == set(base_names[:length])
            ),
            None,
        )
        receipt_present = transport.PREFORMAL_RECEIPT_NAME in observed
        outcome_present = transport.PREFORMAL_OUTCOME_NAME in observed
        marker_present = transport.PREFORMAL_NETWORK_START_NAME in observed
        allowed_full = {
            frozenset(base_names),
            frozenset([*base_names, marker[0]]),
            frozenset([*base_names, transport.PREFORMAL_OUTCOME_NAME]),
            frozenset(
                [*base_names, marker[0], transport.PREFORMAL_OUTCOME_NAME]
            ),
            frozenset(
                [*base_names, marker[0], transport.PREFORMAL_RECEIPT_NAME]
            ),
            frozenset(
                [
                    *base_names,
                    marker[0],
                    transport.PREFORMAL_RECEIPT_NAME,
                    transport.PREFORMAL_OUTCOME_NAME,
                ]
            ),
        }
        if prefix_length is None and frozenset(observed) not in allowed_full:
            _fail("pre-formal journal recovery inventory is not exact")
        known_publications = base[: prefix_length if prefix_length is not None else len(base)]
        for name, raw in known_publications:
            snapshot.current_slot.files[name] = _pin_file_at(
                snapshot.current_slot.directory.descriptor,
                name,
                raw,
                label=f"pre-formal recovery {name}",
            )
        if marker_present:
            snapshot.current_slot.files[marker[0]] = _pin_file_at(
                snapshot.current_slot.directory.descriptor,
                marker[0],
                marker[1],
                label="pre-formal recovery network marker",
            )
        receipt: dict[str, Any] | None = None
        if receipt_present:
            receipt_pin, receipt_raw = _pin_bounded_unknown_file_at(
                snapshot.current_slot.directory.descriptor,
                transport.PREFORMAL_RECEIPT_NAME,
                maximum_byte_count=transport.MAXIMUM_RECEIPT_STDOUT_BYTES,
                label="pre-formal recovery receipt",
            )
            snapshot.current_slot.files[transport.PREFORMAL_RECEIPT_NAME] = receipt_pin
            parsed_receipt = loads_canonical_json(receipt_raw)
            if type(parsed_receipt) is not dict:
                _fail("pre-formal recovery receipt changed type")
            receipt = transport.verify_preformal_upload_receipt_against_controls_v42r1(
                parsed_receipt,
                plan=plan,
                attempt=attempt,
                control_raw_by_name=control_raw_by_name,
                loader_source_raw=loader_source_raw,
                receiver_source_raw=receiver_source_raw,
                predecessor_chain=chain,
            )
        outcome: dict[str, Any] | None = None
        if outcome_present:
            outcome_pin, outcome_raw = _pin_bounded_unknown_file_at(
                snapshot.current_slot.directory.descriptor,
                transport.PREFORMAL_OUTCOME_NAME,
                maximum_byte_count=transport.MAXIMUM_RECEIPT_STDOUT_BYTES,
                label="pre-formal recovery outcome",
            )
            snapshot.current_slot.files[transport.PREFORMAL_OUTCOME_NAME] = outcome_pin
            parsed_outcome = loads_canonical_json(outcome_raw)
            if type(parsed_outcome) is not dict:
                _fail("pre-formal recovery outcome changed type")
            outcome = transport.verify_preformal_upload_outcome_v42r1(
                parsed_outcome,
                plan=plan,
                attempt=attempt,
                receipt=receipt,
            )
            outcome_class = outcome["outcome_class"]
            if outcome_class == transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE:
                expected_marker_and_receipt = (False, False)
            elif outcome_class == transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS:
                expected_marker_and_receipt = (True, False)
            elif outcome_class == transport.PREFORMAL_OUTCOME_COMPLETE:
                expected_marker_and_receipt = (True, True)
            else:
                _fail("pre-formal recovery outcome class is unreachable")
            if (marker_present, receipt_present) != expected_marker_and_receipt:
                _fail(
                    "pre-formal recovery outcome disagrees with marker/receipt inventory"
                )
        elif receipt_present and not marker_present:
            _fail("pre-formal recovery receipt exists without its network marker")
        _durable_verify(snapshot)
        if prefix_length is not None:
            state = (
                "PRE_NETWORK_BASE"
                if prefix_length == len(base_names)
                else "PRE_NETWORK_PREFIX"
            )
        elif outcome is not None:
            state = "TERMINAL"
        elif receipt is not None:
            state = "COMPLETE_RECEIPT_PENDING_OUTCOME"
        elif marker_present:
            state = "POSTNETWORK_UNRESOLVED"
        else:
            _fail("pre-formal journal recovery state is unreachable")
        return PreformalJournalInspectionV42r1(
            state=state,
            pre_network_prefix_length=(
                len(base_names) if prefix_length is None else prefix_length
            ),
            receipt=(
                None
                if receipt is None
                else loads_canonical_json(canonical_json_bytes(receipt))
            ),
            outcome=(
                None
                if outcome is None
                else loads_canonical_json(canonical_json_bytes(outcome))
            ),
        )
    finally:
        snapshot.close()


def hold_network_start_boundary_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> HeldNetworkStartBoundaryV42r1:
    plan, attempt, header, chain = _contextual_documents(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    start = transport.build_preformal_network_start_v42r1(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=chain,
    )
    base = _base_publications(plan=plan, attempt=attempt, header=header)
    snapshot = _open_snapshot(
        plan=plan,
        predecessor_chain=chain,
        create_current_if_absent=False,
    )
    try:
        prefix_length = _pin_slot_prefix(
            snapshot.current_slot,
            base,
            label="pre-formal current ordinal slot",
        )
        if prefix_length != len(base):
            _fail("pre-formal held network boundary is not at the exact base")
        _durable_verify(snapshot)
        return HeldNetworkStartBoundaryV42r1(
            _snapshot=snapshot,
            _start=start,
            _marker_raw=canonical_json_bytes(start),
        )
    except BaseException:
        snapshot.close()
        raise


def publish_pre_network_journal_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan, attempt, header, chain = _contextual_documents(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    publications = _base_publications(plan=plan, attempt=attempt, header=header)
    snapshot = _open_snapshot(
        plan=plan,
        predecessor_chain=chain,
        create_current_if_absent=True,
    )
    try:
        prefix_length = _pin_slot_prefix(
            snapshot.current_slot,
            publications,
            label="pre-formal current ordinal slot",
        )
        _durable_verify(snapshot)
        for name, raw in publications[prefix_length:]:
            snapshot.current_slot.files[name] = _write_once_at(
                snapshot.current_slot.directory.descriptor,
                name,
                raw,
                label=name,
            )
            _durable_verify(snapshot)
        _durable_verify(snapshot)
        return plan, attempt
    finally:
        snapshot.close()


def publish_network_start_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    with hold_network_start_boundary_v42r1(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    ) as boundary:
        return boundary.publish_once()


def publish_outcome_v42r1(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    outcome: dict[str, Any],
    control_raw_by_name: dict[str, bytes],
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
    receipt: dict[str, Any] | None = None,
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    plan, attempt, header, chain = _contextual_documents(
        plan=plan,
        attempt=attempt,
        control_raw_by_name=control_raw_by_name,
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
        predecessor_chain=predecessor_chain,
    )
    if receipt is not None:
        receipt = transport.verify_preformal_upload_receipt_against_controls_v42r1(
            receipt,
            plan=plan,
            attempt=attempt,
            control_raw_by_name=control_raw_by_name,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
            predecessor_chain=chain,
        )
    outcome = transport.verify_preformal_upload_outcome_v42r1(
        outcome, plan=plan, attempt=attempt, receipt=receipt
    )
    publications = _base_publications(plan=plan, attempt=attempt, header=header)
    if outcome["abandonment_reason_code"] != (
        transport.PREFORMAL_ABANDONMENT_REASON_LOCAL
    ):
        publications.append(
            (
                transport.PREFORMAL_NETWORK_START_NAME,
                canonical_json_bytes(
                    transport._network_start_from_verified_documents(  # noqa: SLF001
                        plan=plan, attempt=attempt
                    )
                ),
            )
        )
    outcome_boundary = len(publications)
    if receipt is not None:
        publications.append(
            (
                transport.PREFORMAL_RECEIPT_NAME,
                canonical_json_bytes(receipt),
            )
        )
    publications.append(
        (transport.PREFORMAL_OUTCOME_NAME, canonical_json_bytes(outcome))
    )
    snapshot = _open_snapshot(
        plan=plan,
        predecessor_chain=chain,
        create_current_if_absent=False,
    )
    try:
        prefix_length = _pin_slot_prefix(
            snapshot.current_slot,
            publications,
            label="pre-formal current ordinal slot",
        )
        if prefix_length < outcome_boundary:
            _fail("pre-formal slot is not at the exact outcome boundary")
        _durable_verify(snapshot)
        for name, raw in publications[prefix_length:]:
            snapshot.current_slot.files[name] = _write_once_at(
                snapshot.current_slot.directory.descriptor,
                name,
                raw,
                label=name,
            )
            _durable_verify(snapshot)
        _durable_verify(snapshot)
        return outcome
    finally:
        snapshot.close()


__all__ = [
    "HeldNetworkStartBoundaryV42r1",
    "PreformalJournalInspectionV42r1",
    "V42PreformalJournalError",
    "hold_network_start_boundary_v42r1",
    "inspect_preformal_upload_journal_v42r1",
    "publish_network_start_v42r1",
    "publish_outcome_v42r1",
    "publish_pre_network_journal_v42r1",
]
