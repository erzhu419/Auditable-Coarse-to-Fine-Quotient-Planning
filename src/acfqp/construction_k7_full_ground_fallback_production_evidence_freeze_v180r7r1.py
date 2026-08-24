"""Freeze and producer-free replay the successful V180r7r1 fallback path.

The retained terminal and verification are outcome evidence.  This module does
not import the occurrence producer or terminal finalizer: it pins the exact
eight-role output inventory and delegates semantic reconstruction to the
independently implemented producer-free verifier.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import (
    construction_k7_full_ground_fallback_execution_authorization_evidence_freeze_v180r7r1
    as authorization_evidence,
)
from acfqp import (
    construction_k7_full_ground_fallback_execution_authorization_v180r7r1
    as authorization,
)
from acfqp import (
    construction_k7_full_ground_fallback_execution_failure_freeze_v180r7
    as predecessor_failure,
)
from acfqp import (
    construction_k7_full_ground_fallback_execution_protocol_v180r7r1
    as protocol,
)
from acfqp import (
    construction_k7_full_ground_fallback_materialized_source_evidence_freeze_v180r7r1
    as materialization,
)
from acfqp import (
    construction_k7_full_ground_fallback_production_terminal_independent_verifier_v180r7r1
    as verifier,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_TERMINAL_BUNDLE_ID = (
    "24f72f86b3c27ef47c8126335557e9f45cff84ac9a9737481a50575bbdeae4ef"
)
EXPECTED_TERMINAL_BYTE_COUNT = 1_921_872
EXPECTED_TERMINAL_SHA256 = (
    "e44f26f95056d3815160c8c6bcc2b86a22326c356422c04cf36e8e7af79d3d5c"
)
EXPECTED_VERIFICATION_ID = (
    "552a8104201426f3a696a4ee846922eb42c9148c59c5ce7921f1a865b4c94921"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 2_187
EXPECTED_VERIFICATION_SHA256 = (
    "4a3e711e5c6fa14c873adbcc8023612e1a390db1336f8c3a6b75d51267c25c85"
)

EXPECTED_AUTHORIZATION_ID = (
    "44c19c059e229b6d45b1a9cf4591bf5ee5a53a68ca33ba54b5f5b6ae1b115f6b"
)
EXPECTED_AUTHORIZATION_EVIDENCE_ID = (
    "1a9ed5c0fa2bb07550e78d0c104eadbbd2ffe1442091f41b0244f6b4eca36667"
)
EXPECTED_PROTOCOL_ID = (
    "0d037ddaa78b4f6fceca4409db55eeb0acb93d8c1d64953430debd108ef31889"
)
EXPECTED_MATERIALIZATION_MANIFEST_ID = (
    "1480c3e0a5bcfe7e88f9cbd6a346efd500c17a1826ca656aa527567a0c8ae7f3"
)
EXPECTED_MATERIALIZED_SOURCE_TREE_ID = (
    "5cc30a0a9eea4caa239953af930c8382d3194b2f2ad82847eb9c0ba79b7a2993"
)
EXPECTED_SOURCE_CLOSURE_ID = (
    "ac3f10ef4eea5c0ecc740d9cecc1991e851a65af198e6696f32bde1965feeb4b"
)
EXPECTED_PRESERVED_V180R7_FAILURE_ID = (
    "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
)
EXPECTED_SOURCE_OCCURRENCE_ACCOUNTING_BUNDLE_ID = (
    "872e66735998023ce5e155f9d172d88252efa6407bcc8bb452896924ab0b227b"
)

# role, retained filename, exact canonical byte count, exact SHA-256
EXPECTED_OUTPUT_ROLE_FACTS = (
    (
        "ACTUAL_PROJECTION_PROOF",
        "ACTUAL_PROJECTION_PROOF.json",
        2_405,
        "de6f51521d6d54ee9292a6c1a06ba83390e72cd7ec2c01aaef35d059da60c0e6",
    ),
    (
        "BUSINESS_RESULT",
        "BUSINESS_RESULT.json",
        320_374,
        "879ca8484f25f690ea3ded94ecb81f3a22624157d7a9b90de1838bdac3ad4aed",
    ),
    (
        "COMPARISON_VECTOR",
        "COMPARISON_VECTOR.json",
        2_950,
        "15645a86edf63e7ab1bc1d2552f2673f99932deaa06e50da911ac18c45e77d87",
    ),
    (
        "COUNTER_RECORD_SET",
        "COUNTER_RECORD_SET.json",
        564_689,
        "7e26bb0474503e98da2d83167b3e8bb2d6cd947cf903a387d6fe10deb1be053f",
    ),
    (
        "OPERATIONAL_TRACE",
        "OPERATIONAL_TRACE.json",
        760_280,
        "24374ee88eff66fbd6d4aa712a08180089639985dfa03afa1c7fd0df9327a6a8",
    ),
    (
        "OUTPUT_MANIFEST",
        "OUTPUT_MANIFEST.json",
        1_565,
        "dc19f0e43712a4ac250eb581a651592f07350071e7fafbfabd7036cc58f56223",
    ),
    (
        "TERMINAL_ARTIFACT",
        "TERMINAL_ARTIFACT.json",
        1_500,
        "d1f95ba89576a4842bda3f9c8e955daa000a7cad46bbc8366aed39c7f3042136",
    ),
    (
        "WORK_VECTOR",
        "WORK_VECTOR.json",
        403_389,
        "a40cab4aca9e22056c99e3284ecd626119472a1930384329cf4a11e85936c6ae",
    ),
)
EXPECTED_SOURCE_OUTPUT_BYTE_COUNT = 2_057_152

_ROOT = Path(__file__).resolve().parents[2]
_BASE = _ROOT / ".tmp" / "exact-freeze"
_OUTPUT_DIRECTORY_NAME = "v180r7r1_full_ground_fallback_output"
_TERMINAL_NAME = "v180r7r1_full_ground_fallback_terminal_bundle.json"
_VERIFICATION_NAME = "v180r7r1_full_ground_fallback_verification.json"
_FAILURE_NAMES = (
    "v180r7r1_full_ground_fallback_failure.json",
    "v180r7r1_full_ground_fallback_verification_failure.json",
)


class FullGroundFallbackProductionEvidenceFreezeV180r7r1Error(ValueError):
    """The retained successful occurrence or its independent replay changed."""


def _fail(message: str) -> NoReturn:
    raise FullGroundFallbackProductionEvidenceFreezeV180r7r1Error(message)


def _read_regular_symlink_free(path: Path) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise FullGroundFallbackProductionEvidenceFreezeV180r7r1Error(
            f"retained evidence is absent, linked, or unreadable: {path.name}"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"retained evidence is not a regular file: {path.name}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        if not (
            (
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            == (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            and len(raw) == after.st_size
        ):
            _fail(f"retained evidence changed during read: {path.name}")
        return raw
    finally:
        os.close(descriptor)


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise FullGroundFallbackProductionEvidenceFreezeV180r7r1Error(
            f"{label} is not one canonical document"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical document")
    return document


def _claim_locks(document: dict[str, Any], label: str) -> None:
    if not (
        document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("official_execution_allowed") is False
    ):
        _fail(f"{label} accounting or official gate changed")


def _expected_output_inventory() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": filename,
            "canonical_byte_count": byte_count,
            "canonical_sha256": sha256,
        }
        for _role, filename, byte_count, sha256 in EXPECTED_OUTPUT_ROLE_FACTS
    ]


def _verify_output_inventory(output_root: Path) -> list[dict[str, Any]]:
    try:
        root_info = os.lstat(output_root)
    except OSError as error:
        raise FullGroundFallbackProductionEvidenceFreezeV180r7r1Error(
            "retained eight-role output directory is absent"
        ) from error
    if not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode):
        _fail("retained eight-role output root is linked or nondirectory")
    expected_names = {row[1] for row in EXPECTED_OUTPUT_ROLE_FACTS}
    actual_names = {entry.name for entry in output_root.iterdir()}
    if actual_names != expected_names:
        _fail("retained eight-role output inventory changed")
    actual: list[dict[str, Any]] = []
    for role, filename, byte_count, sha256 in EXPECTED_OUTPUT_ROLE_FACTS:
        raw = _read_regular_symlink_free(output_root / filename)
        _canonical_document(raw, role)
        if not (
            len(raw) == byte_count
            and hashlib.sha256(raw).hexdigest() == sha256
        ):
            _fail(f"retained {role} exact bytes changed")
        actual.append(
            {
                "relative_path": filename,
                "canonical_byte_count": len(raw),
                "canonical_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if not (
        actual == _expected_output_inventory()
        and sum(row["canonical_byte_count"] for row in actual)
        == EXPECTED_SOURCE_OUTPUT_BYTE_COUNT
    ):
        _fail("retained eight-role output denominator changed")
    return actual


@dataclass(frozen=True, slots=True)
class FrozenFullGroundFallbackProductionEvidenceV180r7r1:
    terminal_bytes: bytes
    verification_bytes: bytes
    terminal_bundle_id: str
    verification_id: str
    output_root: Path
    output_inventory: tuple[tuple[str, str, int, str], ...]

    def terminal_document(self) -> dict[str, Any]:
        return _canonical_document(self.terminal_bytes, "V180r7r1 terminal")

    def verification_document(self) -> dict[str, Any]:
        return _canonical_document(
            self.verification_bytes,
            "V180r7r1 verification",
        )


def load_frozen_full_ground_fallback_production_evidence_v180r7r1(
    base: Path = _BASE,
) -> FrozenFullGroundFallbackProductionEvidenceV180r7r1:
    """Verify retained bytes, lineage, claim locks, and producer-free replay."""

    if not isinstance(base, Path):
        _fail("retained evidence base is not a Path")
    for failure_name in _FAILURE_NAMES:
        if os.path.lexists(base / failure_name):
            _fail("V180r7r1 success and failure evidence coexist")

    output_root = base / _OUTPUT_DIRECTORY_NAME
    terminal_bytes = _read_regular_symlink_free(base / _TERMINAL_NAME)
    verification_bytes = _read_regular_symlink_free(base / _VERIFICATION_NAME)
    if not (
        len(terminal_bytes) == EXPECTED_TERMINAL_BYTE_COUNT
        and hashlib.sha256(terminal_bytes).hexdigest()
        == EXPECTED_TERMINAL_SHA256
        and len(verification_bytes) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(verification_bytes).hexdigest()
        == EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V180r7r1 retained terminal or verification bytes changed")

    terminal = _canonical_document(terminal_bytes, "V180r7r1 terminal")
    retained_verification = _canonical_document(
        verification_bytes,
        "V180r7r1 verification",
    )
    inventory = _verify_output_inventory(output_root)

    frozen_protocol = (
        protocol.freeze_full_ground_fallback_execution_protocol_v180r7r1()
    )
    protocol_document = frozen_protocol.to_document()
    frozen_authorization = (
        authorization.freeze_full_ground_fallback_execution_authorization_v180r7r1()
    )
    authorization_document = frozen_authorization.to_document()
    frozen_authorization_evidence = (
        authorization_evidence.
        freeze_full_ground_fallback_execution_authorization_evidence_v180r7r1()
    )
    authorization_evidence_document = frozen_authorization_evidence.to_document()
    frozen_materialization = (
        materialization.load_frozen_full_ground_fallback_materialized_source_v180r7r1()
    )
    materialization_document = frozen_materialization.to_document()
    frozen_predecessor_failure = (
        predecessor_failure.load_frozen_full_ground_fallback_execution_failure_v180r7()
    )

    slot = terminal.get("production_execution_slot")
    reference = terminal.get("materialized_source_reference")
    if not (
        frozen_protocol.protocol_id == EXPECTED_PROTOCOL_ID
        and protocol.EXPECTED_PROTOCOL_ID == EXPECTED_PROTOCOL_ID
        and protocol_document.get("fallback_execution_protocol_id")
        == EXPECTED_PROTOCOL_ID
        and type(slot) is dict
        and protocol_document.get("production_execution_slot") == slot
        and frozen_authorization.authorization_id == EXPECTED_AUTHORIZATION_ID
        and authorization.EXPECTED_AUTHORIZATION_ID == EXPECTED_AUTHORIZATION_ID
        and authorization_document.get("fallback_execution_protocol_id")
        == EXPECTED_PROTOCOL_ID
        and frozen_authorization_evidence.authorization_evidence_id
        == EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and frozen_authorization_evidence.authorization_id
        == EXPECTED_AUTHORIZATION_ID
        and authorization_evidence_document.get(
            "fallback_execution_protocol_id"
        )
        == EXPECTED_PROTOCOL_ID
        and frozen_materialization.materialization_manifest_id
        == EXPECTED_MATERIALIZATION_MANIFEST_ID
        and frozen_materialization.materialized_source_tree_id
        == EXPECTED_MATERIALIZED_SOURCE_TREE_ID
        and frozen_materialization.source_closure_id == EXPECTED_SOURCE_CLOSURE_ID
        and materialization_document.get("materialization_manifest_id")
        == EXPECTED_MATERIALIZATION_MANIFEST_ID
        and frozen_predecessor_failure.failure_id
        == EXPECTED_PRESERVED_V180R7_FAILURE_ID
        and slot.get("preserved_v180r7_failure_id")
        == EXPECTED_PRESERVED_V180R7_FAILURE_ID
        and slot.get("materialization_manifest_id")
        == EXPECTED_MATERIALIZATION_MANIFEST_ID
        and type(reference) is dict
        and reference.get("materialization_manifest_id")
        == EXPECTED_MATERIALIZATION_MANIFEST_ID
        and reference.get("materialized_source_tree_id")
        == EXPECTED_MATERIALIZED_SOURCE_TREE_ID
        and reference.get("source_closure_id") == EXPECTED_SOURCE_CLOSURE_ID
    ):
        _fail("V180r7r1 protocol, authorization, materialization, or predecessor changed")

    if not (
        terminal.get("production_terminal_bundle_id")
        == EXPECTED_TERMINAL_BUNDLE_ID
        and terminal.get("source_occurrence_accounting_bundle", {}).get(
            "occurrence_accounting_bundle_id"
        )
        == EXPECTED_SOURCE_OCCURRENCE_ACCOUNTING_BUNDLE_ID
        and terminal.get("source_output_inventory") == inventory
        and terminal.get("source_output_bytes") == EXPECTED_SOURCE_OUTPUT_BYTE_COUNT
        and terminal.get("finalizer_output_bytes") == EXPECTED_TERMINAL_BYTE_COUNT
        and terminal.get("output_bytes_fixed_point")
        == EXPECTED_SOURCE_OUTPUT_BYTE_COUNT + EXPECTED_TERMINAL_BYTE_COUNT
        and terminal.get("fresh_v180r7r1_observed_occurrence_present") is True
        and terminal.get("materialization_work_charged_to_any_route_component")
        is False
        and terminal.get("official_scalar_cost") is None
        and terminal.get("official_N_break_even") is None
    ):
        _fail("V180r7r1 terminal identity, inventory, or claim boundary changed")
    _claim_locks(terminal, "V180r7r1 terminal")

    replayed = (
        verifier.verify_full_ground_fallback_terminal_independently_v180r7r1(
            terminal_bytes,
            output_root,
        )
    )
    replayed_bytes = canonical_json_bytes(replayed)
    if not (
        replayed_bytes == verification_bytes
        and retained_verification == replayed
        and replayed.get("verification_id") == EXPECTED_VERIFICATION_ID
        and replayed.get("production_terminal_bundle_id")
        == EXPECTED_TERMINAL_BUNDLE_ID
        and replayed.get("fallback_execution_authorization_id")
        == EXPECTED_AUTHORIZATION_ID
        and replayed.get("fallback_execution_protocol_id")
        == EXPECTED_PROTOCOL_ID
        and replayed.get("materialization_manifest_id")
        == EXPECTED_MATERIALIZATION_MANIFEST_ID
        and replayed.get("materialized_source_tree_id")
        == EXPECTED_MATERIALIZED_SOURCE_TREE_ID
        and replayed.get("unchanged_v2_source_closure_id")
        == EXPECTED_SOURCE_CLOSURE_ID
        and replayed.get("retained_output_file_count") == 8
        and replayed.get("retained_source_output_bytes_replayed_without_producer_import")
        is True
        and replayed.get("three_source_v6_route_chains_reconstructed") is True
        and replayed.get("registered_v6_to_v9_counter_lift_reconstructed") is True
        and replayed.get("terminal_output_fixed_point_replayed") is True
        and replayed.get("fresh_single_path_verified") is True
        and replayed.get("all_ten_paths_verified") is False
    ):
        _fail("V180r7r1 retained producer-free verification changed")
    _claim_locks(replayed, "V180r7r1 verification")
    for document, label in (
        (protocol_document, "V180r7r1 protocol"),
        (authorization_document, "V180r7r1 authorization"),
        (authorization_evidence_document, "V180r7r1 authorization evidence"),
        (materialization_document, "V180r7r1 materialization"),
    ):
        _claim_locks(document, label)
        if not (
            document.get("official_scalar_cost") is None
            and document.get("official_N_break_even") is None
        ):
            _fail(f"{label} scalar or break-even claim changed")

    return FrozenFullGroundFallbackProductionEvidenceV180r7r1(
        terminal_bytes,
        verification_bytes,
        EXPECTED_TERMINAL_BUNDLE_ID,
        EXPECTED_VERIFICATION_ID,
        output_root,
        EXPECTED_OUTPUT_ROLE_FACTS,
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_MATERIALIZATION_MANIFEST_ID",
    "EXPECTED_MATERIALIZED_SOURCE_TREE_ID",
    "EXPECTED_OUTPUT_ROLE_FACTS",
    "EXPECTED_PRESERVED_V180R7_FAILURE_ID",
    "EXPECTED_PROTOCOL_ID",
    "EXPECTED_SOURCE_CLOSURE_ID",
    "EXPECTED_SOURCE_OCCURRENCE_ACCOUNTING_BUNDLE_ID",
    "EXPECTED_SOURCE_OUTPUT_BYTE_COUNT",
    "EXPECTED_TERMINAL_BUNDLE_ID",
    "EXPECTED_TERMINAL_BYTE_COUNT",
    "EXPECTED_TERMINAL_SHA256",
    "EXPECTED_VERIFICATION_BYTE_COUNT",
    "EXPECTED_VERIFICATION_ID",
    "EXPECTED_VERIFICATION_SHA256",
    "FrozenFullGroundFallbackProductionEvidenceV180r7r1",
    "FullGroundFallbackProductionEvidenceFreezeV180r7r1Error",
    "load_frozen_full_ground_fallback_production_evidence_v180r7r1",
)
