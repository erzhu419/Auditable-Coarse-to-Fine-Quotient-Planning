"""Freeze the successful V180r12r2 aggregate and producer-free replay.

This post-outcome layer consumes only retained bytes.  It does not import the
aggregation producer, finalizer, independent verifier, runner, materializer,
or launcher.  Static replay here means canonical parsing, content-ID
rederivation, exact cross-file joins, and equality of the independently
produced retained verification and replay; no scientific computation runs.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r2e as subdomains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AGGREGATION_PROTOCOL_ID = (
    "d15ec6d29ffbb4908e20cabfbbc98f3aa53ec4ad38d1d4681930c3306737c965"
)
EXPECTED_EXECUTION_AUTHORIZATION_ID = (
    "4a1424a1d27e97139acd10a50cac79ab012b8459be79b884d9adc3fd4b39e3a9"
)
EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "19836faa57f88a429f321720108724e2deebe0b9b7aa8c3742dc0f97930c5319"
)
EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID = (
    "aba966326ff9e245d1758c65d8c3103614dd1a5a7be96b86e5eb2306bade15f0"
)
EXPECTED_VERIFICATION_ID = (
    "551881bb9bc6baa8dfaa112228f9160986b8106572d6f3f6c85af49434ec14ee"
)
EXPECTED_LAUNCH_RULE_ID = (
    "57e88919b379a3fc2150dcefea46d30488b128832601e31269d225c4de37480b"
)
EXPECTED_MATERIALIZATION_RULE_ID = (
    "79513bd291443fa661c05bc1ff91b6c8f3b8f51dda9aac01073ffec5376abf3d"
)
EXPECTED_SOURCE_CLOSURE_RULE_ID = (
    "fe5036863176827c036ab5aef487b8e920896455dc684e44ae7791438dbb408c"
)
EXPECTED_MATERIALIZATION_TERMINAL_ID = (
    "f21196bf4ac1852d16ea3fb06f7e9042dabd5670ef8dda8ab2e66d2c481fa400"
)
EXPECTED_PRODUCTION_LAUNCH_ATTEMPT_ID = (
    "7cd346fef020527d2eaf594e8fb3553b2489f7cac17f5dccd229c9b9ec25d024"
)
EXPECTED_PRODUCTION_LAUNCH_RECEIPT_ID = (
    "d8a006e9d26fb96c8de5042e7b5624ec6b4fbd5b4e89bcc62efd65fbdc18bbad"
)
EXPECTED_VERIFICATION_LAUNCH_ATTEMPT_ID = (
    "6aaa5a5cda30ef8736365a721a2e7ea60238ea39d8a53ecd2bb13e01398e44e5"
)
EXPECTED_VERIFICATION_LAUNCH_RECEIPT_ID = (
    "dc907dcc728987168012d40c9e84bcb723c52d6a27229f9be43b1e1f4dbfc304"
)
EXPECTED_C_PRE_COMMIT_ID = "807c8c4444b639703739cbd30677b0eff213f03d"
EXPECTED_C_PRE_TREE_ID = "f12326d3b404c5ef07f65423747ec9112eb7be78"
EXPECTED_EMPTY_BRIDGE_COMMIT_ID = "2b608877829f75930c7d2eb5994353e95ccdf12f"
EXPECTED_LITERAL_COMMIT_ID = "6b5beb4fe6093499c00ad89786a00371f5076310"

# role, path below .tmp/exact-freeze, identity field, exact identity,
# canonical byte count, SHA-256 of exact retained bytes
EXPECTED_RETAINED_FILE_FACTS = (
    (
        "TERMINAL",
        "v180r12r2_ten_terminal_aggregation/TERMINAL.json",
        "production_aggregation_bundle_id",
        EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID,
        199_755,
        "11c4431eb5aef1fa6d6805e38755d48ea252e7d3f26ba28f6bf9f4780029e6bf",
    ),
    (
        "VERIFICATION",
        "v180r12r2_ten_terminal_aggregation_verification.json",
        "verification_id",
        EXPECTED_VERIFICATION_ID,
        2_752,
        "95ef7a8b98ddf2ff8214c0eafef00d250430b19951184feb87b302c62dcd2c05",
    ),
    (
        "REPLAY",
        "v180r12r2_ten_terminal_aggregation_verification_replay.json",
        "verification_id",
        EXPECTED_VERIFICATION_ID,
        2_752,
        "95ef7a8b98ddf2ff8214c0eafef00d250430b19951184feb87b302c62dcd2c05",
    ),
    (
        "PRODUCTION_LAUNCH_ATTEMPT",
        "v180r12r2_ten_terminal_aggregation_prelaunch/PRODUCTION_LAUNCH_ATTEMPT.json",
        "launch_attempt_id",
        EXPECTED_PRODUCTION_LAUNCH_ATTEMPT_ID,
        1_751,
        "c3f0a084d02fa9f9390fd5eb581c2850ea1a95ad5005ddfa637f6bb4095ea8b0",
    ),
    (
        "PRODUCTION_LAUNCH_RECEIPT",
        "v180r12r2_ten_terminal_aggregation_prelaunch/PRODUCTION_LAUNCH_RECEIPT.json",
        "launch_receipt_id",
        EXPECTED_PRODUCTION_LAUNCH_RECEIPT_ID,
        2_796,
        "9dbd89154a8878e1fac4b82457143183ff7c0742e387aeaa65a49877a50fcc6c",
    ),
    (
        "VERIFICATION_LAUNCH_ATTEMPT",
        "v180r12r2_ten_terminal_aggregation_prelaunch/VERIFICATION_LAUNCH_ATTEMPT.json",
        "launch_attempt_id",
        EXPECTED_VERIFICATION_LAUNCH_ATTEMPT_ID,
        1_755,
        "e5850fcab92e63f5bfc37fe8e91333aabe32eb168cd7f4deb31c5ad140aa0b3d",
    ),
    (
        "VERIFICATION_LAUNCH_RECEIPT",
        "v180r12r2_ten_terminal_aggregation_prelaunch/VERIFICATION_LAUNCH_RECEIPT.json",
        "launch_receipt_id",
        EXPECTED_VERIFICATION_LAUNCH_RECEIPT_ID,
        2_878,
        "b3463bed230e8eb9b2eed7690121e35fc0b96c8810a49a5e0e1c5cbf5d8bdcdd",
    ),
    (
        "MATERIALIZATION_TERMINAL",
        "v180r12r2_ten_terminal_aggregation_prelaunch/MATERIALIZATION_TERMINAL.json",
        "materialization_terminal_id",
        EXPECTED_MATERIALIZATION_TERMINAL_ID,
        5_296,
        "6f7a29091b09be7213aefa6b4ac307fbb3802f862bcfdc6dc48d6501fcc419c9",
    ),
    (
        "LAUNCH_MANIFEST",
        "v180r12r2_ten_terminal_aggregation_prelaunch/launch_manifest.json",
        None,
        None,
        147_801,
        "375e3db038242a59d3d2cfa2a1383bcce05743e74ef5115a185f4a6816aca735",
    ),
    (
        "EXTERNAL_ROOT",
        "v180r12r2_ten_terminal_aggregation_prelaunch_external_root.json",
        None,
        None,
        1_627,
        "8e456d808970e6c17b8ed7a884b9c03c4963cdffeb7184b6640d7ceefd4a5752",
    ),
)

EXPECTED_ABSENT_RELATIVE_PATHS = (
    "v180r12r2_ten_terminal_aggregation_prelaunch_failure.json",
    "v180r12r2_ten_terminal_aggregation_prelaunch_production_launch_failure.json",
    "v180r12r2_ten_terminal_aggregation_prelaunch_verification_launch_failure.json",
    "v180r12r2_ten_terminal_aggregation_failure.json",
    "v180r12r2_ten_terminal_aggregation_verification_failure.json",
    "v180r12r2_ten_terminal_aggregation_cas",
)

EXPECTED_RETAINED_DIRECTORY_MODES = (
    ("v180r12r2_ten_terminal_aggregation", 0o700),
    ("v180r12r2_ten_terminal_aggregation_prelaunch", 0o700),
)
EXPECTED_RETAINED_FILE_MODE = 0o400
EXPECTED_INNER_CONTENT_ID_COUNT = 129

_ROOT = Path(__file__).resolve().parents[2]
_BASE = _ROOT / ".tmp" / "exact-freeze"
_FACT_BY_ROLE = {row[0]: row for row in EXPECTED_RETAINED_FILE_FACTS}
_GATES = (
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
)


class TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(ValueError):
    """The retained successful V180r12r2 evidence or replay changed."""


def _fail(message: str) -> NoReturn:
    raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(message)


def _parts(relative_path: str) -> tuple[str, ...]:
    candidate = PurePosixPath(relative_path)
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or candidate.as_posix() != relative_path
    ):
        _fail("retained evidence relative path is not normalized")
    return candidate.parts


def _open_base(base: Path) -> int:
    if not isinstance(base, Path):
        _fail("retained evidence base is not a Path")
    absolute = base.absolute()
    try:
        directory_fd = os.open(
            absolute.anchor,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
    except OSError as error:
        raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
            "retained evidence filesystem root is unreadable"
        ) from error
    try:
        for part in absolute.parts[1:]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        return directory_fd
    except OSError as error:
        os.close(directory_fd)
        raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
            "retained evidence base has an absent, linked, or unreadable component"
        ) from error


def _assert_success_exclusive(base_fd: int) -> None:
    _assert_retained_directory_modes(base_fd)
    if any(
        _exists_no_follow(base_fd, relative_path)
        for relative_path in EXPECTED_ABSENT_RELATIVE_PATHS
    ):
        _fail("V180r12r2 success and failure or runtime-CAS evidence coexist")


def _open_parent(base_fd: int, relative_path: str) -> tuple[int, str]:
    parts = _parts(relative_path)
    directory_fd = os.dup(base_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        return directory_fd, parts[-1]
    except OSError as error:
        os.close(directory_fd)
        raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
            f"retained evidence ancestor is absent, linked, or unreadable: {relative_path}"
        ) from error


def _read_regular_stable(base_fd: int, relative_path: str, byte_count: int) -> bytes:
    parent_fd, name = _open_parent(base_fd, relative_path)
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except OSError as error:
        os.close(parent_fd)
        raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
            f"retained evidence is absent, linked, or unreadable: {relative_path}"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not (
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and before.st_size == byte_count
            and stat.S_IMODE(before.st_mode) == EXPECTED_RETAINED_FILE_MODE
        ):
            _fail(
                "retained evidence type, mode, link count, or size changed: "
                f"{relative_path}"
            )
        chunks: list[bytes] = []
        remaining = byte_count
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                _fail(f"retained evidence ended early: {relative_path}")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail(f"retained evidence exceeded its exact byte count: {relative_path}")
        after = os.fstat(descriptor)
        raw = b"".join(chunks)
        facts = lambda row: (  # noqa: E731
            row.st_dev,
            row.st_ino,
            row.st_mode,
            row.st_nlink,
            row.st_size,
            row.st_mtime_ns,
            row.st_ctime_ns,
        )
        if facts(before) != facts(after) or len(raw) != byte_count:
            _fail(f"retained evidence changed during read: {relative_path}")
        return raw
    finally:
        os.close(descriptor)
        os.close(parent_fd)


def _exists_no_follow(base_fd: int, relative_path: str) -> bool:
    parts = _parts(relative_path)
    parent_fd = os.dup(base_fd)
    try:
        for part in parts[:-1]:
            try:
                next_fd = os.open(
                    part,
                    os.O_RDONLY
                    | os.O_DIRECTORY
                    | os.O_CLOEXEC
                    | os.O_NOFOLLOW,
                    dir_fd=parent_fd,
                )
            except FileNotFoundError:
                return False
            except OSError as error:
                raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
                    f"retained absence ancestor is linked or unreadable: {relative_path}"
                ) from error
            os.close(parent_fd)
            parent_fd = next_fd
        try:
            os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        except OSError as error:
            raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
                f"retained absence state is unreadable: {relative_path}"
            ) from error
        return True
    finally:
        os.close(parent_fd)


def _assert_retained_directory_modes(base_fd: int) -> None:
    for relative_path, expected_mode in EXPECTED_RETAINED_DIRECTORY_MODES:
        parts = _parts(relative_path)
        directory_fd = os.dup(base_fd)
        try:
            for part in parts:
                next_fd = os.open(
                    part,
                    os.O_RDONLY
                    | os.O_DIRECTORY
                    | os.O_CLOEXEC
                    | os.O_NOFOLLOW,
                    dir_fd=directory_fd,
                )
                os.close(directory_fd)
                directory_fd = next_fd
            metadata = os.fstat(directory_fd)
            if not (
                stat.S_ISDIR(metadata.st_mode)
                and metadata.st_nlink >= 2
                and stat.S_IMODE(metadata.st_mode) == expected_mode
            ):
                _fail(f"retained evidence directory mode changed: {relative_path}")
        except OSError as error:
            raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
                f"retained evidence directory is absent, linked, or unreadable: {relative_path}"
            ) from error
        finally:
            os.close(directory_fd)


def _document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
            f"{label} is not one canonical document"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical document")
    return value


def _launch_stream_bytes(value: Any, label: str) -> bytes:
    if not (
        type(value) is dict
        and set(value)
        == {"byte_count", "retained_prefix_hex", "retained_prefix_truncated", "sha256"}
        and type(value.get("byte_count")) is int
        and value["byte_count"] >= 0
        and type(value.get("retained_prefix_hex")) is str
        and value.get("retained_prefix_truncated") is False
        and type(value.get("sha256")) is str
    ):
        _fail(f"{label} stream receipt changed")
    try:
        raw = bytes.fromhex(value["retained_prefix_hex"])
    except ValueError as error:
        raise TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error(
            f"{label} stream hex is invalid"
        ) from error
    if not (
        len(raw) == value["byte_count"]
        and hashlib.sha256(raw).hexdigest() == value["sha256"]
    ):
        _fail(f"{label} stream bytes changed")
    return raw


def _launch_stdout_document(receipt: dict[str, Any], label: str) -> dict[str, Any]:
    stdout = _launch_stream_bytes(receipt.get("child_stdout"), f"{label} stdout")
    stderr = _launch_stream_bytes(receipt.get("child_stderr"), f"{label} stderr")
    if stderr != b"":
        _fail(f"{label} child stderr is not empty")
    if not stdout.endswith(b"\n") or stdout[:-1].endswith(b"\n"):
        _fail(f"{label} child stdout framing changed")
    return _document(stdout[:-1], f"{label} child stdout")


def _plain_payload_id(document: dict[str, Any], identity_field: str) -> str:
    payload = dict(document)
    identity = payload.pop(identity_field, None)
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    if identity != digest:
        _fail(f"{identity_field} is not the content ID of its exact payload")
    return digest


def _domain_payload_id(
    document: dict[str, Any], identity_field: str, domain: str
) -> str:
    payload = dict(document)
    identity = payload.pop(identity_field, None)
    digest = domains.extension_content_id_v180r12r2(domain, payload)
    if identity != digest:
        _fail(f"{identity_field} is not the registered content ID")
    return digest


def _subrecord_payload_id(
    document: dict[str, Any], identity_field: str, domain: str
) -> str:
    if type(document) is not dict:
        _fail(f"{identity_field} container is not an exact object")
    payload = dict(document)
    identity = payload.pop(identity_field, None)
    digest = subdomains.extension_content_id_v180r12r2e(domain, payload)
    if identity != digest:
        _fail(f"{identity_field} is not the registered content ID")
    return digest


def _assert_all_inner_content_ids(terminal: dict[str, Any]) -> None:
    rows = (
        (
            terminal.get("source_verification_receipts"),
            5,
            "source_receipt_id",
            subdomains.CONSTRUCTION_K7_SOURCE_RECEIPT_V180R12R2E_DOMAIN,
        ),
        (
            terminal.get("route_component_chain_receipts"),
            12,
            "route_component_chain_receipt_id",
            subdomains.CONSTRUCTION_K7_ROUTE_COMPONENT_CHAIN_RECEIPT_V180R12R2E_DOMAIN,
        ),
        (
            terminal.get("terminal_receipts"),
            10,
            "terminal_chain_receipt_id",
            subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_V180R12R2E_DOMAIN,
        ),
    )
    identities: list[str] = []
    for population, expected_count, identity_field, domain in rows:
        if type(population) is not list or len(population) != expected_count:
            _fail(f"{identity_field} population changed")
        identities.extend(
            _subrecord_payload_id(row, identity_field, domain) for row in population
        )

    shared_sets = terminal.get("terminal_shared_resource_receipt_sets")
    if type(shared_sets) is not list or len(shared_sets) != 10:
        _fail("terminal shared-resource receipt-set population changed")
    for receipt_set in shared_sets:
        receipts = receipt_set.get("receipts") if type(receipt_set) is dict else None
        if type(receipts) is not list or len(receipts) != 9:
            _fail("terminal shared-resource receipt population changed")
        receipt_ids = [
            _subrecord_payload_id(
                receipt,
                "terminal_shared_resource_receipt_id",
                subdomains.CONSTRUCTION_K7_TERMINAL_SHARED_RECEIPT_V180R12R2E_DOMAIN,
            )
            for receipt in receipts
        ]
        if receipt_set.get("terminal_shared_resource_receipt_ids") != receipt_ids:
            _fail("terminal shared-resource receipt ordering or join changed")
        identities.extend(receipt_ids)
        identities.append(
            _subrecord_payload_id(
                receipt_set,
                "terminal_shared_resource_receipt_set_id",
                subdomains.CONSTRUCTION_K7_TERMINAL_RECEIPT_SET_V180R12R2E_DOMAIN,
            )
        )

    identities.append(
        _subrecord_payload_id(
            terminal.get("v180r7r1_construction_axis_receipt"),
            "v180r7r1_construction_axis_receipt_id",
            subdomains.CONSTRUCTION_K7_V180R7R1_CONSTRUCTION_AXIS_RECEIPT_V180R12R2E_DOMAIN,
        )
    )
    identities.append(
        _subrecord_payload_id(
            terminal.get("campaign_scope_structural_boundary"),
            "campaign_scope_structural_boundary_id",
            subdomains.CONSTRUCTION_K7_CAMPAIGN_STRUCTURAL_BOUNDARY_V180R12R2E_DOMAIN,
        )
    )
    if len(identities) != EXPECTED_INNER_CONTENT_ID_COUNT or len(set(identities)) != len(
        identities
    ):
        _fail("V180r12r2 inner registered content-ID denominator or uniqueness changed")


def _claim_locks(document: dict[str, Any], label: str) -> None:
    if not (
        document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and all(
            gate not in document or document.get(gate) == "NOT_RUN"
            for gate in _GATES[2:]
        )
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
    ):
        _fail(f"{label} official claim boundary changed")


def _assert_aggregate_boundary(
    terminal: dict[str, Any], verification: dict[str, Any]
) -> None:
    common = {
        "source_group_count": 5,
        "source_verification_receipt_count": 5,
        "terminal_code_count": 10,
        "terminal_receipt_count": 10,
        "route_component_chain_receipt_count": 12,
        "ten_terminal_representative_counter_record_count": 2_690,
        "route_component_counter_record_count": 3_228,
        "v180r7r1_additional_counter_record_count": 538,
        "occurrence_shared_resource_receipt_count": 90,
        "campaign_scope_structural_obligation_count": 9,
        "campaign_scope_actual_counter_record_count": 0,
        "campaign_scope_actual_shared_resource_receipt_count": 0,
        "campaign_scope_actual_work_vector_count": 0,
        "campaign_scope_actual_comparison_vector_count": 0,
        "campaign_scope_actual_projection_proof_count": 0,
        "campaign_scope_actual_native_zero_attestation_count": 0,
        "campaign_scope_authoritative_receipt_count": 0,
        "total_authoritative_shared_resource_receipt_count": 90,
        "v180r7r1_construction_axis_receipt_count": 1,
    }
    for label, document in (("terminal", terminal), ("verification", verification)):
        if not (
            document.get("aggregation_protocol_id")
            == EXPECTED_AGGREGATION_PROTOCOL_ID
            and document.get("execution_authorization_id")
            == EXPECTED_EXECUTION_AUTHORIZATION_ID
            and document.get("production_aggregation_bundle_id")
            == EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID
            and all(document.get(key) == value for key, value in common.items())
            and document.get("COUNTER_COMPLETENESS_BLOCKER")
            == "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
            and document.get("historical_summary_translation_used") is False
            and document.get("v180r7r1_construction_work_charged_to_route_components")
            is False
        ):
            _fail(f"V180r12r2 {label} denominator or lineage changed")
        _claim_locks(document, f"V180r12r2 {label}")

    chains = terminal.get("route_component_chain_receipts")
    shared_sets = terminal.get("terminal_shared_resource_receipt_sets")
    construction = terminal.get("v180r7r1_construction_axis_receipt")
    structural = terminal.get("campaign_scope_structural_boundary")
    if not (
        type(chains) is list
        and len(chains) == 12
        and len({row.get("route_component_chain_receipt_id") for row in chains}) == 12
        and len({(row.get("terminal_code"), row.get("route_kind")) for row in chains})
        == 12
        and all(
            type(row) is dict
            and row.get("counter_record_count") == 269
            and row.get(
                "counter_record_to_work_vector_to_comparison_vector_replayed"
            )
            is True
            and row.get("independent_route_component") is True
            for row in chains
        )
        and type(shared_sets) is list
        and len(shared_sets) == 10
        and sum(row.get("receipt_count", -1) for row in shared_sets) == 90
        and all(
            type(row) is dict
            and row.get("receipt_count") == 9
            and row.get("all_nine_paths_present") is True
            and row.get("missing_path_inferred_zero") is False
            for row in shared_sets
        )
        and type(construction) is dict
        and construction.get("one_time_construction_axis") is True
        and construction.get("construction_axis_replayed_separately") is True
        and construction.get("charged_to_any_route_component") is False
        and construction.get("occurrence_route_counter_record_count") == 0
        and type(structural) is dict
        and structural.get("structural_declaration_count") == 9
        and structural.get("actual_counter_record_count") == 0
        and structural.get("actual_work_vector_present") is False
        and structural.get("actual_comparison_vector_present") is False
        and structural.get("actual_projection_proof_present") is False
        and structural.get("actual_native_zero_attestation_present") is False
        and structural.get("authoritative_receipt_total") == 90
        and structural.get("campaign_scope_authoritative_receipt_count") == 0
        and structural.get("structural_boundary_only") is True
        and structural.get("scientific_success_claimed") is False
    ):
        _fail("V180r12r2 route, receipt, campaign, or construction boundary changed")
    _claim_locks(structural, "V180r12r2 campaign structural boundary")

    if not (
        terminal.get("route_component_counter_closure_status")
        == "PENDING_INDEPENDENT_REPLAY"
        and verification.get("route_component_counter_closure_status") == "PASS"
        and verification.get("aggregation_byte_count") == _FACT_BY_ROLE["TERMINAL"][4]
        and verification.get("aggregation_sha256") == _FACT_BY_ROLE["TERMINAL"][5]
        and verification.get("campaign_scope_actual_measurement_ledger_present")
        is False
        and verification.get("v180r12r3_actual_campaign_measurement_ledger_required")
        is True
        and verification.get("producer_module_imported") is False
        and verification.get("producer_aggregate_exact_bytes_reconstructed") is True
        and all(
            verification.get(key) is True
            for key in (
                "all_five_source_independent_verifiers_replayed",
                "all_twelve_route_component_chains_replayed",
                "all_ten_terminal_receipts_replayed",
                "all_ninety_terminal_shared_resource_receipts_replayed",
                "all_route_component_counter_records_replayed",
                "all_route_component_work_vectors_replayed",
                "all_route_component_comparison_vectors_rederived",
                "all_route_component_actual_projection_proofs_replayed",
                "all_route_component_native_zero_attestations_replayed",
                "terminal_receipt_denominators_replayed",
                "campaign_scope_structural_boundary_replayed",
                "campaign_scope_has_no_route_kind",
                "v180r7r1_construction_axis_replayed_separately",
            )
        )
    ):
        _fail("V180r12r2 producer-free route closure or open-world boundary changed")


def _assert_launch_and_materialization_joins(documents: dict[str, dict[str, Any]]) -> None:
    materialization = documents["MATERIALIZATION_TERMINAL"]
    manifest = documents["LAUNCH_MANIFEST"]
    external = documents["EXTERNAL_ROOT"]
    production_attempt = documents["PRODUCTION_LAUNCH_ATTEMPT"]
    production_receipt = documents["PRODUCTION_LAUNCH_RECEIPT"]
    verification_attempt = documents["VERIFICATION_LAUNCH_ATTEMPT"]
    verification_receipt = documents["VERIFICATION_LAUNCH_RECEIPT"]
    terminal_fact = _FACT_BY_ROLE["TERMINAL"]
    verification_fact = _FACT_BY_ROLE["VERIFICATION"]
    attempt_facts = {
        "production": _FACT_BY_ROLE["PRODUCTION_LAUNCH_ATTEMPT"],
        "verification": _FACT_BY_ROLE["VERIFICATION_LAUNCH_ATTEMPT"],
    }

    for document, identity_field in (
        (materialization, "materialization_terminal_id"),
        (production_attempt, "launch_attempt_id"),
        (production_receipt, "launch_receipt_id"),
        (verification_attempt, "launch_attempt_id"),
        (verification_receipt, "launch_receipt_id"),
    ):
        _plain_payload_id(document, identity_field)

    topology = materialization.get("git_topology")
    if not (
        materialization.get("materialization_rule_id")
        == EXPECTED_MATERIALIZATION_RULE_ID
        and materialization.get("source_closure_rule_id")
        == EXPECTED_SOURCE_CLOSURE_RULE_ID
        and materialization.get("success") is True
        and materialization.get("construction_only") is True
        and materialization.get("scientific_occurrence_executed") is False
        and materialization.get("v180r12r2_outcome_bytes_accessed") is False
        and materialization.get("counter_records_issued") is False
        and materialization.get("work_vectors_issued") is False
        and materialization.get("comparison_vectors_issued") is False
        and materialization.get("launch_manifest", {}).get("byte_count")
        == _FACT_BY_ROLE["LAUNCH_MANIFEST"][4]
        and materialization.get("launch_manifest", {}).get("sha256")
        == _FACT_BY_ROLE["LAUNCH_MANIFEST"][5]
        and materialization.get("external_root", {}).get("byte_count")
        == _FACT_BY_ROLE["EXTERNAL_ROOT"][4]
        and materialization.get("external_root", {}).get("sha256")
        == _FACT_BY_ROLE["EXTERNAL_ROOT"][5]
        and type(topology) is dict
        and topology.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and topology.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and topology.get("empty_bridge_commit_id") == EXPECTED_EMPTY_BRIDGE_COMMIT_ID
        and topology.get("literal_commit_id") == EXPECTED_LITERAL_COMMIT_ID
        and manifest.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and external.get("c_pre_commit_id") == EXPECTED_C_PRE_COMMIT_ID
        and external.get("c_pre_tree_id") == EXPECTED_C_PRE_TREE_ID
        and external.get("materialization_rule_id")
        == EXPECTED_MATERIALIZATION_RULE_ID
        and external.get("source_closure_rule_id") == EXPECTED_SOURCE_CLOSURE_RULE_ID
        and external.get("created_before_v180r12r2_authorized_production_execution")
        is True
        and external.get("v180r12r2_outcome_bytes_accessed") is False
    ):
        _fail("V180r12r2 materialization, manifest, or external-root join changed")
    _claim_locks(materialization, "V180r12r2 materialization terminal")

    for target, attempt, receipt, expected_attempt_id, expected_receipt_id in (
        (
            "production",
            production_attempt,
            production_receipt,
            EXPECTED_PRODUCTION_LAUNCH_ATTEMPT_ID,
            EXPECTED_PRODUCTION_LAUNCH_RECEIPT_ID,
        ),
        (
            "verification",
            verification_attempt,
            verification_receipt,
            EXPECTED_VERIFICATION_LAUNCH_ATTEMPT_ID,
            EXPECTED_VERIFICATION_LAUNCH_RECEIPT_ID,
        ),
    ):
        if not (
            attempt.get("target") == target
            and receipt.get("target") == target
            and attempt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
            and receipt.get("launch_rule_id") == EXPECTED_LAUNCH_RULE_ID
            and attempt.get("launch_attempt_id") == expected_attempt_id
            and receipt.get("launch_attempt_id") == expected_attempt_id
            and receipt.get("launch_receipt_id") == expected_receipt_id
            and attempt.get("materialization_terminal_id")
            == EXPECTED_MATERIALIZATION_TERMINAL_ID
            and attempt.get("materialization_terminal_byte_count")
            == _FACT_BY_ROLE["MATERIALIZATION_TERMINAL"][4]
            and attempt.get("materialization_terminal_sha256")
            == _FACT_BY_ROLE["MATERIALIZATION_TERMINAL"][5]
            and attempt.get("launch_manifest_sha256")
            == _FACT_BY_ROLE["LAUNCH_MANIFEST"][5]
            and receipt.get("success") is True
            and receipt.get("return_code") == 0
            and receipt.get("timed_out") is False
            and receipt.get("failure_type") is None
            and receipt.get("failure_message") is None
            and receipt.get("campaign_actual_measurement") is False
        ):
            _fail(f"V180r12r2 {target} launch chain changed")
        _claim_locks(receipt, f"V180r12r2 {target} launch receipt")
        stdout_document = _launch_stdout_document(
            receipt, f"V180r12r2 {target} launch receipt"
        )
        expected_stdout = (
            {
                "aggregation_protocol_id": EXPECTED_AGGREGATION_PROTOCOL_ID,
                "authorization_evidence_id": EXPECTED_AUTHORIZATION_EVIDENCE_ID,
                "execution_authorization_id": EXPECTED_EXECUTION_AUTHORIZATION_ID,
                "production_aggregation_bundle_id": EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID,
                "terminal_byte_count": terminal_fact[4],
                "terminal_sha256": terminal_fact[5],
            }
            if target == "production"
            else {
                "execution_authorization_id": EXPECTED_EXECUTION_AUTHORIZATION_ID,
                "production_aggregation_sha256": terminal_fact[5],
                "retained_replay_exact": True,
                "verification_byte_count": verification_fact[4],
                "verification_id": EXPECTED_VERIFICATION_ID,
                "verification_sha256": verification_fact[5],
            }
        )
        if stdout_document != expected_stdout:
            _fail(f"V180r12r2 {target} launch stdout join changed")
        progress = receipt.get("progress_observations")
        attempt_fact = attempt_facts[target]
        if not (
            type(progress) is dict
            and progress.get("attempt", {}).get("byte_count") == attempt_fact[4]
            and progress.get("attempt", {}).get("sha256") == attempt_fact[5]
            and progress.get("terminal", {}).get("byte_count") == terminal_fact[4]
            and progress.get("terminal", {}).get("sha256") == terminal_fact[5]
            and progress.get("runtime_cas", {}).get("presence") == "ABSENT"
            and progress.get("production_failure", {}).get("presence") == "ABSENT"
            and progress.get("verification_failure", {}).get("presence") == "ABSENT"
            and progress.get("launch_failure", {}).get("presence") == "ABSENT"
        ):
            _fail(f"V180r12r2 {target} launch progress join changed")
        if target == "verification" and not (
            progress.get("verification", {}).get("byte_count")
            == verification_fact[4]
            and progress.get("verification", {}).get("sha256")
            == verification_fact[5]
            and progress.get("retained_replay", {}).get("byte_count")
            == verification_fact[4]
            and progress.get("retained_replay", {}).get("sha256")
            == verification_fact[5]
        ):
            _fail("V180r12r2 verification launch output join changed")


@dataclass(frozen=True, slots=True)
class FrozenTenTerminalAggregationProductionEvidenceV180r12r2:
    terminal_bytes: bytes
    verification_bytes: bytes
    replay_bytes: bytes
    production_aggregation_bundle_id: str
    verification_id: str
    retained_file_facts: tuple[tuple[str, str, str | None, str | None, int, str], ...]

    def terminal_document(self) -> dict[str, Any]:
        return _document(self.terminal_bytes, "V180r12r2 terminal")

    def verification_document(self) -> dict[str, Any]:
        return _document(self.verification_bytes, "V180r12r2 verification")


def load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
    base: Path = _BASE,
) -> FrozenTenTerminalAggregationProductionEvidenceV180r12r2:
    """Load exact retained success evidence and statically replay its joins."""

    base_fd = _open_base(base)
    try:
        _assert_success_exclusive(base_fd)
        raw_by_role: dict[str, bytes] = {}
        document_by_role: dict[str, dict[str, Any]] = {}
        for role, relative_path, identity_field, identity, byte_count, sha256 in (
            EXPECTED_RETAINED_FILE_FACTS
        ):
            raw = _read_regular_stable(base_fd, relative_path, byte_count)
            if hashlib.sha256(raw).hexdigest() != sha256:
                _fail(f"V180r12r2 retained {role} exact bytes changed")
            document = _document(raw, f"V180r12r2 {role}")
            if identity_field is not None and document.get(identity_field) != identity:
                _fail(f"V180r12r2 retained {role} content identity changed")
            raw_by_role[role] = raw
            document_by_role[role] = document
        _assert_success_exclusive(base_fd)
    finally:
        os.close(base_fd)

    terminal = document_by_role["TERMINAL"]
    retained_verification = document_by_role["VERIFICATION"]
    if not (
        raw_by_role["VERIFICATION"] == raw_by_role["REPLAY"]
        and retained_verification == document_by_role["REPLAY"]
    ):
        _fail("V180r12r2 verification and retained replay differ")

    _domain_payload_id(
        terminal,
        "production_aggregation_bundle_id",
        domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R2_DOMAIN,
    )
    _assert_all_inner_content_ids(terminal)
    for role in ("VERIFICATION", "REPLAY"):
        _domain_payload_id(
            document_by_role[role],
            "verification_id",
            domains.CONSTRUCTION_K7_VERIFICATION_V180R12R2_DOMAIN,
        )
    _assert_aggregate_boundary(terminal, retained_verification)
    _assert_launch_and_materialization_joins(document_by_role)

    return FrozenTenTerminalAggregationProductionEvidenceV180r12r2(
        raw_by_role["TERMINAL"],
        raw_by_role["VERIFICATION"],
        raw_by_role["REPLAY"],
        EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID,
        EXPECTED_VERIFICATION_ID,
        EXPECTED_RETAINED_FILE_FACTS,
    )


def freeze_ten_terminal_aggregation_production_evidence_v180r12r2(
    base: Path = _BASE,
) -> FrozenTenTerminalAggregationProductionEvidenceV180r12r2:
    """Alias with an issuance-oriented name for the frozen result surface."""

    return load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2(
        base,
    )


__all__ = (
    "EXPECTED_ABSENT_RELATIVE_PATHS",
    "EXPECTED_AGGREGATION_PROTOCOL_ID",
    "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
    "EXPECTED_EXECUTION_AUTHORIZATION_ID",
    "EXPECTED_LAUNCH_RULE_ID",
    "EXPECTED_INNER_CONTENT_ID_COUNT",
    "EXPECTED_MATERIALIZATION_TERMINAL_ID",
    "EXPECTED_PRODUCTION_AGGREGATION_BUNDLE_ID",
    "EXPECTED_PRODUCTION_LAUNCH_ATTEMPT_ID",
    "EXPECTED_PRODUCTION_LAUNCH_RECEIPT_ID",
    "EXPECTED_RETAINED_FILE_FACTS",
    "EXPECTED_RETAINED_FILE_MODE",
    "EXPECTED_RETAINED_DIRECTORY_MODES",
    "EXPECTED_VERIFICATION_ID",
    "EXPECTED_VERIFICATION_LAUNCH_ATTEMPT_ID",
    "EXPECTED_VERIFICATION_LAUNCH_RECEIPT_ID",
    "FrozenTenTerminalAggregationProductionEvidenceV180r12r2",
    "TenTerminalAggregationProductionEvidenceFreezeV180r12r2Error",
    "freeze_ten_terminal_aggregation_production_evidence_v180r12r2",
    "load_frozen_ten_terminal_aggregation_production_evidence_v180r12r2",
)
