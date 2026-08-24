"""Outcome-free authorization for one fresh V180r7r1 fallback occurrence."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains
from acfqp import (
    construction_k7_full_ground_fallback_execution_protocol_v180r7r1
    as protocol,
)
from acfqp import (
    construction_k7_full_ground_fallback_materialized_source_evidence_freeze_v180r7r1
    as materialization,
)
from acfqp import (
    construction_k7_recovery_eligible_source_closure_successor_v180r7r1
    as selector,
)
from acfqp import phase3e_sealed_executor_v1 as sealed_runtime
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = (
    "44c19c059e229b6d45b1a9cf4591bf5ee5a53a68ca33ba54b5f5b6ae1b115f6b"
)
EXPECTED_CANONICAL_BYTE_COUNT = 32_413
EXPECTED_CANONICAL_SHA256 = (
    "b22709dddd2d2354812d064086cb7f0a9edcffb215b4788015e39bea1f40bb3e"
)
EXPECTED_PROTOCOL_ID = protocol.EXPECTED_PROTOCOL_ID
EXPECTED_PRODUCTION_EXECUTION_SLOT_ID = (
    protocol.EXPECTED_PRODUCTION_EXECUTION_SLOT_ID
)

PRESERVED_V180R7_AUTHORIZATION_ID = (
    "445851c4b3ceb25be1858e0c4c07e436631486efe12853db8fef4fdf9c5573e9"
)
PRESERVED_V180R7_FAILURE_ID = (
    "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
)
SOURCE_CATALOG_MANIFEST_ID = (
    "92e4f36212d957d3701591ee689a23e4446d942c4c3e3b562049290c19ad50d0"
)
SOURCE_CLOSURE_REPAIR_ID = (
    "feb8f6034ef1da9050242fe4e112edb285b77bd63a87642196f8fbc7995544c8"
)
MATERIALIZATION_MANIFEST_ID = (
    "1480c3e0a5bcfe7e88f9cbd6a346efd500c17a1826ca656aa527567a0c8ae7f3"
)
MATERIALIZED_SOURCE_TREE_ID = (
    "5cc30a0a9eea4caa239953af930c8382d3194b2f2ad82847eb9c0ba79b7a2993"
)
SOURCE_CLOSURE_ID = (
    "ac3f10ef4eea5c0ecc740d9cecc1991e851a65af198e6696f32bde1965feeb4b"
)
LOGICAL_OCCURRENCE_ID = (
    "293485bc465428ff5b3f923b6d261153a272d30253644076f7dbf19c39cfc3aa"
)
QUERY_ORDINAL = 7

EXPECTED_BINDING_BYTE_COUNT = 4_405
EXPECTED_BINDING_SHA256 = (
    "bf5d7f5292a4b38136b141745b9349bc4e86c2ab7e67592e8d25c19b5daa527f"
)
EXPECTED_SNAPSHOT_BYTE_COUNT = 388_638
EXPECTED_SNAPSHOT_SHA256 = (
    "18056b6f1aba853cb3b705041be93bce31700c79d45fa894fd956b144f0e7823"
)
EXPECTED_TRANSITION_BYTE_COUNT = 859_154
EXPECTED_TRANSITION_SHA256 = (
    "e2278f8b499b13f45ab1c8fcba29be9665d472d4cd9ab65e1ee124187bfbbe30"
)

WORKER_PROCESS_COUNT = 1
TIMEOUT_SECONDS = 7_200
ADDRESS_SPACE_HARD_CAP_BYTES = 24 * 1024 * 1024 * 1024

_ROOT = Path(__file__).resolve().parents[2]
_AUTHORIZATION_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_full_ground_fallback_execution_authorization_v180r7r1.py"
)
_AUTHORIZATION_EVIDENCE_RELATIVE_PATH = (
    "src/acfqp/construction_k7_full_ground_fallback_execution_"
    "authorization_evidence_freeze_v180r7r1.py"
)
_SOURCE_FACT_EXCLUSIONS = tuple(
    sorted(
        (
            _AUTHORIZATION_RELATIVE_PATH,
            _AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
        )
    )
)
_PRODUCTION_SOURCE_ROOTS = (
    "scripts/run_v180r7r1_full_ground_fallback_occurrence.py",
    (
        "src/acfqp/construction_k7_full_ground_fallback_"
        "production_terminal_finalizer_v180r7r1.py"
    ),
)
_VERIFICATION_SOURCE_ROOTS = (
    "scripts/verify_v180r7r1_full_ground_fallback_occurrence.py",
    (
        "src/acfqp/construction_k7_full_ground_fallback_"
        "production_terminal_independent_verifier_v180r7r1.py"
    ),
)
_CONTRACT_SOURCE_ROOTS = (
    (
        "src/acfqp/construction_k7_full_ground_fallback_"
        "source_catalog_evidence_freeze_v180r7r1.py"
    ),
    (
        "src/acfqp/construction_k7_full_ground_fallback_"
        "source_inventory_preregistration_v180r7r1.py"
    ),
)
_INPUT_SPECS = (
    (
        ".tmp/recovery-eligible-retained-v1/PROOF_DEPENDENCY_TRANSITION.json",
        EXPECTED_TRANSITION_BYTE_COUNT,
        EXPECTED_TRANSITION_SHA256,
    ),
    (
        ".tmp/recovery-eligible-retained-v1/REUSABLE_RAPM_SNAPSHOT.json",
        EXPECTED_SNAPSHOT_BYTE_COUNT,
        EXPECTED_SNAPSHOT_SHA256,
    ),
    (
        ".tmp/recovery-eligible-retained-v1/SOURCE_BUNDLE_BINDING.json",
        EXPECTED_BINDING_BYTE_COUNT,
        EXPECTED_BINDING_SHA256,
    ),
)


class FullGroundFallbackExecutionAuthorizationV180r7r1Error(ValueError):
    """The fresh protocol, sources, inputs, or finite caps changed."""


def _fail(message: str) -> None:
    raise FullGroundFallbackExecutionAuthorizationV180r7r1Error(message)


def _read_regular_symlink_free(path: Path) -> bytes:
    try:
        return source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise FullGroundFallbackExecutionAuthorizationV180r7r1Error(
            "authorization-bound path is absent, linked, or nonregular"
        ) from error


def _module_name(relative_path: str) -> str:
    path = Path(relative_path)
    if not (
        relative_path.startswith("src/acfqp/")
        and relative_path.endswith(".py")
    ):
        _fail("authorization catalogue path is outside src/acfqp")
    parts = list(path.relative_to("src").with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    name = ".".join(parts)
    if not source_runtime_v2._valid_module_name(name):  # noqa: SLF001
        _fail("authorization catalogue module name is invalid")
    return name


def _module_catalogue() -> dict[str, tuple[str, Path, bool]]:
    rows: dict[str, tuple[str, Path, bool]] = {}
    for path in sorted((_ROOT / "src" / "acfqp").rglob("*.py")):
        relative_path = path.relative_to(_ROOT).as_posix()
        name = _module_name(relative_path)
        if name in rows:
            _fail("authorization module catalogue is duplicated")
        rows[name] = (relative_path, path, path.name == "__init__.py")
    if not (
        0 < len(rows) <= selector.MAX_CANDIDATE_CATALOG_MODULES
        and tuple(rows) == tuple(sorted(rows))
    ):
        _fail("authorization module catalogue exceeds its finite cap")
    return rows


def _script_import_roots(
    relative_path: str,
    available_names: frozenset[str],
) -> tuple[str, ...]:
    raw = _read_regular_symlink_free(_ROOT / relative_path)
    try:
        tree = ast.parse(raw, filename=relative_path)
    except (SyntaxError, ValueError) as error:
        raise FullGroundFallbackExecutionAuthorizationV180r7r1Error(
            "authorization script root is not static Python source"
        ) from error
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in available_names:
                    roots.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module
            if type(module) is not str or not module.startswith("acfqp"):
                continue
            if module in available_names:
                roots.add(module)
            for alias in node.names:
                candidate = f"{module}.{alias.name}"
                if candidate in available_names:
                    roots.add(candidate)
    return tuple(sorted(roots))


def _static_source_closure_relative_paths() -> tuple[str, ...]:
    catalogue = _module_catalogue()
    available = frozenset(catalogue)
    script_roots = tuple(
        relative_path
        for relative_path in (*_PRODUCTION_SOURCE_ROOTS, *_VERIFICATION_SOURCE_ROOTS)
        if relative_path.startswith("scripts/")
    )
    all_roots = (
        *_PRODUCTION_SOURCE_ROOTS,
        *_VERIFICATION_SOURCE_ROOTS,
        *_CONTRACT_SOURCE_ROOTS,
    )
    explicit_modules = {
        _module_name(relative_path)
        for relative_path in all_roots
        if relative_path.startswith("src/acfqp/")
    }
    for relative_path in script_roots:
        explicit_modules.update(_script_import_roots(relative_path, available))
    if not explicit_modules <= available:
        _fail("authorization static-import root is absent")

    pending = list(reversed(tuple(sorted(explicit_modules))))
    included: set[str] = set()
    while pending:
        name = pending.pop()
        if name in included:
            continue
        if len(included) >= selector.MAX_CANDIDATE_CATALOG_MODULES:
            _fail("authorization static source closure exceeds its module cap")
        included.add(name)
        relative_path, path, is_package = catalogue[name]
        raw = _read_regular_symlink_free(path)
        try:
            imports = source_runtime_v2._local_imports_from_raw(  # noqa: SLF001
                module_name=name,
                is_package=is_package,
                raw=raw,
                available_names=available,
            )
        except (
            source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation
        ) as error:
            raise FullGroundFallbackExecutionAuthorizationV180r7r1Error(
                f"authorization static-import traversal failed: {relative_path}"
            ) from error
        pending.extend(
            reversed(tuple(item for item in imports if item not in included))
        )
        components = name.split(".")
        for end in range(1, len(components)):
            parent = ".".join(components[:end])
            if parent not in catalogue:
                _fail("authorization static closure omitted a parent package")
            if parent not in included:
                pending.append(parent)
    paths = {
        catalogue[name][0]
        for name in included
        if catalogue[name][0] not in _SOURCE_FACT_EXCLUSIONS
    }
    paths.update(script_roots)
    result = tuple(sorted(paths))
    if (
        set(_SOURCE_FACT_EXCLUSIONS) & set(result)
        or not set(all_roots) <= set(result)
    ):
        _fail("authorization self-exclusion or static roots changed")
    return result


def _source_facts() -> list[dict[str, Any]]:
    rows = []
    for relative_path in _static_source_closure_relative_paths():
        raw = _read_regular_symlink_free(_ROOT / relative_path)
        rows.append(
            {
                "relative_path": relative_path,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    if [row["relative_path"] for row in rows] != sorted(
        {row["relative_path"] for row in rows}
    ):
        _fail("authorization source facts are unsorted or duplicated")
    return rows


def replay_authorization_source_facts_v180r7r1(
    document: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    observed = _source_facts()
    if not (
        type(document) is dict
        and document.get("source_facts") == observed
        and document.get("source_fact_file_count") == len(observed)
        and document.get("source_fact_byte_count")
        == sum(row["byte_count"] for row in observed)
        and document.get("source_facts_sha256")
        == hashlib.sha256(canonical_json_bytes(observed)).hexdigest()
        and document.get("source_fact_exclusions")
        == list(_SOURCE_FACT_EXCLUSIONS)
    ):
        _fail("authorization-bound static source closure changed")
    return tuple(observed)


def _retained_input_facts() -> list[dict[str, Any]]:
    rows = []
    for relative_path, expected_bytes, expected_sha256 in _INPUT_SPECS:
        raw = _read_regular_symlink_free(_ROOT / relative_path)
        document = loads_canonical_json(raw)
        fact = {
            "relative_path": relative_path,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        if not (
            type(document) is dict
            and canonical_json_bytes(document) == raw
            and fact["byte_count"] == expected_bytes
            and fact["sha256"] == expected_sha256
        ):
            _fail("retained predecessor input changed")
        rows.append(fact)
    return rows


def _resource_caps() -> dict[str, Any]:
    caps = {
        "worker_process_count": WORKER_PROCESS_COUNT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "candidate_catalog_module_cap": selector.MAX_CANDIDATE_CATALOG_MODULES,
        "candidate_catalog_source_byte_cap": (
            selector.MAX_CANDIDATE_CATALOG_SOURCE_BYTES
        ),
        "reachable_source_module_cap": source_runtime_v2.MAX_MODULES,
        "reachable_source_byte_cap": selector.MAX_RECOVERY_RUNTIME_SOURCE_BYTES,
        "source_bytes_per_module_cap": (
            source_runtime_v2.MAX_SOURCE_BYTES_PER_MODULE
        ),
        "runtime_manifest_file_cap": sealed_runtime.RUNTIME_MANIFEST_MAX_FILE_COUNT,
        "runtime_manifest_total_byte_cap": (
            sealed_runtime.RUNTIME_MANIFEST_MAX_TOTAL_BYTES
        ),
        "runtime_manifest_document_byte_cap": (
            sealed_runtime.RUNTIME_MANIFEST_MAX_DOCUMENT_BYTES
        ),
        "runtime_manifest_path_byte_cap": (
            sealed_runtime.RUNTIME_MANIFEST_MAX_PATH_BYTES
        ),
        "materialized_source_module_count": 307,
        "materialized_source_byte_count": 15_129_926,
    }
    if caps != {
        "worker_process_count": 1,
        "timeout_seconds": 7_200,
        "address_space_hard_cap_bytes": 25_769_803_776,
        "candidate_catalog_module_cap": 4_096,
        "candidate_catalog_source_byte_cap": 67_108_864,
        "reachable_source_module_cap": 1_024,
        "reachable_source_byte_cap": 16_777_216,
        "source_bytes_per_module_cap": 16_777_216,
        "runtime_manifest_file_cap": 512,
        "runtime_manifest_total_byte_cap": 16_777_216,
        "runtime_manifest_document_byte_cap": 1_048_576,
        "runtime_manifest_path_byte_cap": 512,
        "materialized_source_module_count": 307,
        "materialized_source_byte_count": 15_129_926,
    }:
        _fail("inherited finite execution caps changed")
    return caps


def build_full_ground_fallback_execution_authorization_v180r7r1(
) -> dict[str, Any]:
    frozen_protocol = (
        protocol.freeze_full_ground_fallback_execution_protocol_v180r7r1()
    )
    protocol_document = frozen_protocol.to_document()
    slot = protocol_document["production_execution_slot"]
    staged = (
        materialization.load_frozen_full_ground_fallback_materialized_source_v180r7r1()
    )
    staged_document = staged.to_document()
    if not (
        frozen_protocol.protocol_id == protocol.EXPECTED_PROTOCOL_ID
        and slot["logical_occurrence_id"] == LOGICAL_OCCURRENCE_ID
        and slot["query_ordinal"] == QUERY_ORDINAL
        and slot["preserved_v180r7_failure_id"] == PRESERVED_V180R7_FAILURE_ID
        and slot["source_closure_repair_id"] == SOURCE_CLOSURE_REPAIR_ID
        and slot["materialization_manifest_id"] == MATERIALIZATION_MANIFEST_ID
        and staged.materialization_manifest_id == MATERIALIZATION_MANIFEST_ID
        and staged.materialized_source_tree_id == MATERIALIZED_SOURCE_TREE_ID
        and staged.source_closure_id == SOURCE_CLOSURE_ID
        and staged_document["source_catalog_manifest_id"]
        == SOURCE_CATALOG_MANIFEST_ID
        and staged_document["source_closure_repair_id"]
        == SOURCE_CLOSURE_REPAIR_ID
    ):
        _fail("fresh protocol or materialized-source identity changed")
    source_facts = _source_facts()
    payload = {
        "schema": "acfqp.full_ground_fallback_execution_authorization.v180r7r1",
        "fallback_execution_protocol_id": frozen_protocol.protocol_id,
        "production_execution_slot": slot,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "query_ordinal": QUERY_ORDINAL,
        "preserved_v180r7_authorization_id": PRESERVED_V180R7_AUTHORIZATION_ID,
        "preserved_v180r7_failure_id": PRESERVED_V180R7_FAILURE_ID,
        "failed_v180r7_authorization_reused": False,
        "same_failed_authorization_rerun_forbidden": True,
        "source_catalog_manifest_id": SOURCE_CATALOG_MANIFEST_ID,
        "source_closure_repair_id": SOURCE_CLOSURE_REPAIR_ID,
        "materialization_manifest_id": MATERIALIZATION_MANIFEST_ID,
        "materialized_source_tree_id": MATERIALIZED_SOURCE_TREE_ID,
        "unchanged_v2_source_closure_id": SOURCE_CLOSURE_ID,
        "source_facts": source_facts,
        "source_fact_file_count": len(source_facts),
        "source_fact_byte_count": sum(row["byte_count"] for row in source_facts),
        "source_facts_sha256": hashlib.sha256(
            canonical_json_bytes(source_facts)
        ).hexdigest(),
        "source_fact_closure_rule": (
            "RECURSIVE_STATIC_LOCAL_ACFQP_IMPORTS_FROM_PRODUCTION_AND_"
            "VERIFICATION_ROOTS"
        ),
        "production_source_fact_static_import_roots": list(
            _PRODUCTION_SOURCE_ROOTS
        ),
        "verification_source_fact_static_import_roots": list(
            _VERIFICATION_SOURCE_ROOTS
        ),
        "contract_source_fact_static_import_roots": list(_CONTRACT_SOURCE_ROOTS),
        "source_fact_exclusions": list(_SOURCE_FACT_EXCLUSIONS),
        "authorization_self_source_bound_by_post_prereg_freeze": False,
        "self_identity_cycle_avoided": True,
        "post_prereg_authorization_evidence_freeze_required": True,
        "retained_predecessor_input_facts": _retained_input_facts(),
        "resource_caps": _resource_caps(),
        "entrypoint": (
            "acfqp.construction_k7_full_ground_fallback_"
            "production_terminal_finalizer_v180r7r1:"
            "run_full_ground_fallback_production_occurrence_v180r7r1"
        ),
        "runner_relative_path": (
            "scripts/run_v180r7r1_full_ground_fallback_occurrence.py"
        ),
        "runtime_cas_root_relative_path": (
            ".tmp/exact-freeze/v180r7r1_full_ground_fallback_cas"
        ),
        "output_root_relative_path": (
            ".tmp/exact-freeze/v180r7r1_full_ground_fallback_output"
        ),
        "terminal_relative_path": (
            ".tmp/exact-freeze/"
            "v180r7r1_full_ground_fallback_terminal_bundle.json"
        ),
        "failure_relative_path": (
            ".tmp/exact-freeze/v180r7r1_full_ground_fallback_failure.json"
        ),
        "verification_relative_path": (
            ".tmp/exact-freeze/v180r7r1_full_ground_fallback_verification.json"
        ),
        "one_worker_process_required": True,
        "one_isolated_worker_no_concurrent_campaign": True,
        "concurrent_workspace_mutation_during_one_shot_occurrence_out_of_scope": (
            True
        ),
        "timeout_seconds": TIMEOUT_SECONDS,
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "runtime_cas_root_must_be_absent": True,
        "output_root_must_be_absent": True,
        "terminal_must_be_written_once": True,
        "failure_must_be_written_once": True,
        "same_authorization_rerun_after_progress_or_terminal_forbidden": True,
        "independent_verification_required_after_success": True,
        "three_route_family_vectors_must_remain_separate": True,
        "registered_record_to_record_v6_to_v9_lift_required": True,
        "historical_summary_to_counter_translation_forbidden": True,
        "materialized_construction_work_charged_to_route_vectors": False,
        "fresh_fallback_execution_started": False,
        "production_outcome_accessed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
    }
    return {
        **payload,
        "fallback_execution_authorization_id": domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_AUTHORIZATION_V180R7R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FullGroundFallbackExecutionAuthorizationV180r7r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and document.get("fallback_execution_authorization_id")
            == self.authorization_id
        ):
            _fail("V180r7r1 authorization is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@lru_cache(maxsize=1)
def freeze_full_ground_fallback_execution_authorization_v180r7r1(
) -> FullGroundFallbackExecutionAuthorizationV180r7r1:
    document = build_full_ground_fallback_execution_authorization_v180r7r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["fallback_execution_authorization_id"]
        == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V180r7r1 frozen execution authorization identity changed")
    return FullGroundFallbackExecutionAuthorizationV180r7r1(
        _ISSUER,
        raw,
        document["fallback_execution_authorization_id"],
    )


__all__ = (
    "ADDRESS_SPACE_HARD_CAP_BYTES",
    "EXPECTED_AUTHORIZATION_ID",
    "EXPECTED_BINDING_BYTE_COUNT",
    "EXPECTED_BINDING_SHA256",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_SNAPSHOT_BYTE_COUNT",
    "EXPECTED_SNAPSHOT_SHA256",
    "EXPECTED_TRANSITION_BYTE_COUNT",
    "EXPECTED_TRANSITION_SHA256",
    "EXPECTED_PROTOCOL_ID",
    "EXPECTED_PRODUCTION_EXECUTION_SLOT_ID",
    "FullGroundFallbackExecutionAuthorizationV180r7r1",
    "FullGroundFallbackExecutionAuthorizationV180r7r1Error",
    "PRESERVED_V180R7_AUTHORIZATION_ID",
    "PRESERVED_V180R7_FAILURE_ID",
    "TIMEOUT_SECONDS",
    "WORKER_PROCESS_COUNT",
    "build_full_ground_fallback_execution_authorization_v180r7r1",
    "freeze_full_ground_fallback_execution_authorization_v180r7r1",
    "replay_authorization_source_facts_v180r7r1",
)
