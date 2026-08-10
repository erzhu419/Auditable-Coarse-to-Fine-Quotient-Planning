"""Replayable current-state matrix for all ten K7 terminal accounting paths.

The matrix answers a deliberately narrower question than an official Gate:
which FQ9 terminal codes currently have a terminal-specific production V6
``CounterRecord -> WorkVector -> ComparisonVector`` implementation, which
have only a registered fixture or replayable blocker, and which have no
terminal-specific formal implementation at all.

This module never upgrades a source capability into an observed occurrence.
In particular, a complete implementation row is not campaign evidence.  The
matrix keeps both official Gates locked and exists to make the remaining work
set exact, exhaustive, and independently rebuildable from the current source
tree.
"""

from __future__ import annotations

import ast
from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_all_path_accounting_profile_v1 as profile_v1
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as boundary_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_MATRIX_V1_DOMAIN,
    CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_SOURCE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.64"
PROFILE_KEY = "construction_k7_terminal_accounting_coverage_matrix_v1"

EXPECTED_TERMINAL_CODE_COUNT = 10
EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_SOURCE_MEMBER_COUNT = 11
EXPECTED_FORMAL_IMPLEMENTATION_COUNT = 3
EXPECTED_PRODUCTION_SITE_IMPLEMENTATION_COUNT = 2
EXPECTED_FIXTURE_ONLY_IMPLEMENTATION_COUNT = 1
EXPECTED_PARTIAL_OR_READINESS_COUNT = 2
EXPECTED_MISSING_IMPLEMENTATION_COUNT = 5

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

SOURCE_DOMAIN = CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_SOURCE_V1_DOMAIN
ROW_DOMAIN = CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_ROW_V1_DOMAIN
MATRIX_DOMAIN = CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_MATRIX_V1_DOMAIN
REPLAY_DOMAIN = CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_REPLAY_V1_DOMAIN

LOCAL_DOMAINS = frozenset({SOURCE_DOMAIN, ROW_DOMAIN, MATRIX_DOMAIN, REPLAY_DOMAIN})
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS.issubset(  # pragma: no cover
    PHASE3E_DOMAIN_TAGS
):
    raise RuntimeError("terminal-accounting coverage domains are not central")

_SOURCE_ISSUER = object()
_ROW_ISSUER = object()
_MATRIX_ISSUER = object()
_REPLAY_ISSUER = object()


class ConstructionK7TerminalAccountingCoverageMatrixV1Error(ValueError):
    """The terminal inventory, its source basis, or a coverage row changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TerminalAccountingCoverageMatrixV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7TerminalAccountingCoverageMatrixV1Error(
            f"{label} must be one exact content ID"
        ) from error


class TerminalAccountingCoverageStateV1(str, Enum):
    PRODUCTION_SITE_FORMAL_IMPLEMENTATION = "PRODUCTION_SITE_FORMAL_IMPLEMENTATION"
    REGISTERED_FIXTURE_FORMAL_IMPLEMENTATION_ONLY = (
        "REGISTERED_FIXTURE_FORMAL_IMPLEMENTATION_ONLY"
    )
    REPLAYABLE_PARTIAL_COVERAGE_ONLY = "REPLAYABLE_PARTIAL_COVERAGE_ONLY"
    REPLAYABLE_READINESS_BLOCKER_ONLY = "REPLAYABLE_READINESS_BLOCKER_ONLY"
    TERMINAL_SPECIFIC_FORMAL_IMPLEMENTATION_MISSING = (
        "TERMINAL_SPECIFIC_FORMAL_IMPLEMENTATION_MISSING"
    )


@dataclass(frozen=True, slots=True)
class _SourceSpecV1:
    module_name: str
    filename: str
    profile_key: str
    required_public_symbols: tuple[str, ...]


_SOURCE_SPECS = (
    _SourceSpecV1(
        "acfqp.construction_k7_all_path_accounting_profile_v1",
        "construction_k7_all_path_accounting_profile_v1.py",
        "construction_k7_all_path_accounting_profile_v1",
        (
            "freeze_construction_k7_all_path_accounting_profile_v1",
            "verify_construction_k7_all_path_accounting_profile_document_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_all_path_operation_boundary_manifest_v1",
        "construction_k7_all_path_operation_boundary_manifest_v1.py",
        "construction_k7_all_path_operation_boundary_manifest_v1",
        (
            "freeze_construction_k7_all_path_operation_boundary_manifest_v1",
            "verify_construction_k7_all_path_operation_boundary_manifest_document_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_abstract_certified_native_zero_closure_v1",
        "construction_k7_abstract_certified_native_zero_closure_v1.py",
        "construction_k7_abstract_certified_native_zero_closure_v1",
        (
            "close_abstract_certified_zero_value_subset_v1",
            "verify_abstract_certified_zero_value_closure_document_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_abstract_certified_query_owner_authority_v1",
        "construction_k7_abstract_certified_query_owner_authority_v1.py",
        "construction_k7_abstract_certified_query_owner_authority_v1",
        (
            "issue_abstract_certified_query_owner_authority_v1",
            "verify_abstract_certified_query_owner_authority_bytes_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_direct_fallback_exact_infeasibility_readiness_v1",
        "construction_k7_direct_fallback_exact_infeasibility_readiness_v1.py",
        "construction_k7_direct_fallback_exact_infeasibility_readiness_v1",
        (
            "assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1",
            "verify_construction_k7_direct_fallback_exact_infeasibility_readiness_document_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_integrity_failure_authority_v1",
        "construction_k7_integrity_failure_authority_v1.py",
        "construction_k7_integrity_failure_authority_v1",
        (
            "issue_k7_integrity_failure_bundle_v1",
            "verify_k7_integrity_failure_bundle_bytes_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_protocol_failure_authority_v1",
        "construction_k7_protocol_failure_authority_v1.py",
        "construction_k7_protocol_failure_authority_v1",
        (
            "issue_canonical_k7_protocol_failure_bundle_v1",
            "verify_k7_protocol_failure_bundle_bytes_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_root_cap_terminal_authority_v1",
        "construction_k7_root_cap_terminal_authority_v1.py",
        "construction_k7_root_cap_terminal_authority_v1",
        (
            "issue_k7_root_cap_terminal_accounting_bundle_v1",
            "verify_k7_root_cap_terminal_accounting_bundle_bytes_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_formal_accounting_materializer_v1",
        "construction_k7_formal_accounting_materializer_v1.py",
        "construction_k7_formal_accounting_materializer_v1",
        (
            "materialize_k7_formal_accounting_v1",
            "verify_k7_formal_accounting_materialization_bytes_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_production_accounting_pipeline_v1",
        "construction_k7_production_accounting_pipeline_v1.py",
        "construction_k7_production_accounting_pipeline_v1",
        (
            "run_k7_production_accounting_pipeline_v1",
            "replay_k7_production_accounting_pipeline_v1",
        ),
    ),
    _SourceSpecV1(
        "acfqp.construction_k7_campaign_closure_v1",
        "construction_k7_campaign_closure_v1.py",
        "construction_k7_campaign_closure_v1",
        (
            "run_k7_production_accounting_campaign_v1",
            "replay_k7_production_accounting_campaign_v1",
        ),
    ),
)


def _profile_key_from_tree(tree: ast.Module, label: str) -> str:
    matches: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "PROFILE_KEY" for target in targets):
            continue
        value = node.value
        if isinstance(value, ast.Constant) and type(value.value) is str:
            matches.append(value.value)
    if len(matches) != 1:
        _fail(f"{label} lacks one literal PROFILE_KEY")
    return matches[0]


@dataclass(frozen=True, slots=True)
class K7TerminalAccountingCoverageSourceV1:
    _issuer: InitVar[object]
    module_name: str
    filename: str
    profile_key: str
    source_sha256: str
    source_byte_count: int
    required_public_symbols: tuple[str, ...]
    _source_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_ISSUER:
            _fail("terminal coverage source is caller-minted")
        if (
            type(self.module_name) is not str
            or not self.module_name.startswith("acfqp.")
            or type(self.filename) is not str
            or not self.filename.endswith(".py")
            or type(self.profile_key) is not str
            or not self.profile_key
            or type(self.source_sha256) is not str
            or len(self.source_sha256) != 64
            or type(self.source_byte_count) is not int
            or self.source_byte_count <= 0
            or type(self.required_public_symbols) is not tuple
            or not self.required_public_symbols
            or tuple(sorted(self.required_public_symbols)) != self.required_public_symbols
            or len(set(self.required_public_symbols)) != len(self.required_public_symbols)
        ):
            _fail("terminal coverage source fact is incomplete")
        object.__setattr__(self, "_source_id", content_id(SOURCE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_terminal_accounting_coverage_source.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "module_name": self.module_name,
            "filename": self.filename,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "source_profile_key": self.profile_key,
            "required_public_symbols": list(self.required_public_symbols),
            "complete_source_bytes_examined": True,
        }

    @property
    def source_id(self) -> str:
        expected = content_id(SOURCE_DOMAIN, self._payload())
        if expected != self._source_id:
            _fail("terminal coverage source changed after issuance")
        return self._source_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "terminal_accounting_coverage_source_id": self.source_id}


@dataclass(frozen=True, slots=True)
class _RowSpecV1:
    terminal_code: TerminalCode
    state: TerminalAccountingCoverageStateV1
    source_module: str
    closed_required_path_count: int
    complete_formal_chain_present: bool
    terminal_specific_verifier_present: bool
    production_site_implementation_present: bool
    blocker_code: str | None


_ROW_SPECS = (
    _RowSpecV1(
        TerminalCode.ABSTRACT_CERTIFIED,
        TerminalAccountingCoverageStateV1.REPLAYABLE_PARTIAL_COVERAGE_ONLY,
        "acfqp.construction_k7_abstract_certified_query_owner_authority_v1",
        28,
        False,
        False,
        False,
        "ABSTRACT_CERTIFIED_REQUIRES_174_ADDITIONAL_V6_PATH_AUTHORITIES",
    ),
    _RowSpecV1(
        TerminalCode.LOCAL_GROUND_RECOVERY,
        TerminalAccountingCoverageStateV1.TERMINAL_SPECIFIC_FORMAL_IMPLEMENTATION_MISSING,
        "acfqp.construction_k7_all_path_accounting_profile_v1",
        0,
        False,
        False,
        False,
        "LOCAL_GROUND_RECOVERY_FORMAL_IMPLEMENTATION_MISSING",
    ),
    _RowSpecV1(
        TerminalCode.FULL_GROUND_FALLBACK,
        TerminalAccountingCoverageStateV1.TERMINAL_SPECIFIC_FORMAL_IMPLEMENTATION_MISSING,
        "acfqp.construction_k7_all_path_accounting_profile_v1",
        0,
        False,
        False,
        False,
        "FULL_GROUND_FALLBACK_FORMAL_IMPLEMENTATION_MISSING",
    ),
    _RowSpecV1(
        TerminalCode.CACHED_EXACT_INFEASIBLE,
        TerminalAccountingCoverageStateV1.TERMINAL_SPECIFIC_FORMAL_IMPLEMENTATION_MISSING,
        "acfqp.construction_k7_all_path_accounting_profile_v1",
        0,
        False,
        False,
        False,
        "CACHED_EXACT_INFEASIBLE_FORMAL_IMPLEMENTATION_MISSING",
    ),
    _RowSpecV1(
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE,
        TerminalAccountingCoverageStateV1.REPLAYABLE_READINESS_BLOCKER_ONLY,
        "acfqp.construction_k7_direct_fallback_exact_infeasibility_readiness_v1",
        0,
        False,
        False,
        False,
        "LEGACY_42_ROW_VECTOR_IS_NOT_A_202_ROW_V6_CHAIN",
    ),
    _RowSpecV1(
        TerminalCode.INTEGRITY_FAILURE,
        TerminalAccountingCoverageStateV1.PRODUCTION_SITE_FORMAL_IMPLEMENTATION,
        "acfqp.construction_k7_integrity_failure_authority_v1",
        202,
        True,
        True,
        True,
        None,
    ),
    _RowSpecV1(
        TerminalCode.PROTOCOL_FAILURE,
        TerminalAccountingCoverageStateV1.REGISTERED_FIXTURE_FORMAL_IMPLEMENTATION_ONLY,
        "acfqp.construction_k7_protocol_failure_authority_v1",
        202,
        True,
        True,
        False,
        "PRODUCTION_PROTOCOL_SITE_AUTHORITY_NOT_BOUND",
    ),
    _RowSpecV1(
        TerminalCode.REBUILD_REQUIRED,
        TerminalAccountingCoverageStateV1.TERMINAL_SPECIFIC_FORMAL_IMPLEMENTATION_MISSING,
        "acfqp.construction_k7_all_path_accounting_profile_v1",
        0,
        False,
        False,
        False,
        "REBUILD_REQUIRED_FORMAL_IMPLEMENTATION_MISSING",
    ),
    _RowSpecV1(
        TerminalCode.FALLBACK_CAP_EXHAUSTED,
        TerminalAccountingCoverageStateV1.TERMINAL_SPECIFIC_FORMAL_IMPLEMENTATION_MISSING,
        "acfqp.construction_k7_all_path_accounting_profile_v1",
        0,
        False,
        False,
        False,
        "FALLBACK_CAP_EXHAUSTED_FORMAL_IMPLEMENTATION_MISSING",
    ),
    _RowSpecV1(
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
        TerminalAccountingCoverageStateV1.PRODUCTION_SITE_FORMAL_IMPLEMENTATION,
        "acfqp.construction_k7_root_cap_terminal_authority_v1",
        202,
        True,
        True,
        True,
        None,
    ),
)


@dataclass(frozen=True, slots=True)
class K7TerminalAccountingCoverageRowV1:
    _issuer: InitVar[object]
    terminal_code: TerminalCode
    terminal_class: str
    state: TerminalAccountingCoverageStateV1
    evidence_source_id: str
    evidence_module: str
    closed_required_path_count: int
    complete_formal_chain_present: bool
    terminal_specific_verifier_present: bool
    production_site_implementation_present: bool
    blocker_code: str | None
    _row_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROW_ISSUER:
            _fail("terminal coverage row is caller-minted")
        try:
            code = TerminalCode(self.terminal_code)
            state = TerminalAccountingCoverageStateV1(self.state)
        except (TypeError, ValueError) as error:
            raise ConstructionK7TerminalAccountingCoverageMatrixV1Error(
                "terminal coverage row enum changed"
            ) from error
        object.__setattr__(self, "terminal_code", code)
        object.__setattr__(self, "state", state)
        _cid(self.evidence_source_id, "terminal coverage source")
        if (
            type(self.terminal_class) is not str
            or not self.terminal_class
            or type(self.evidence_module) is not str
            or not self.evidence_module.startswith("acfqp.")
            or type(self.closed_required_path_count) is not int
            or not 0 <= self.closed_required_path_count <= EXPECTED_REQUIRED_PATH_COUNT
            or type(self.complete_formal_chain_present) is not bool
            or type(self.terminal_specific_verifier_present) is not bool
            or type(self.production_site_implementation_present) is not bool
            or (self.blocker_code is not None and (type(self.blocker_code) is not str or not self.blocker_code))
        ):
            _fail("terminal coverage row is incomplete")
        object.__setattr__(self, "_row_id", content_id(ROW_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_terminal_accounting_coverage_row.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_code": self.terminal_code.value,
            "terminal_class": self.terminal_class,
            "coverage_state": self.state.value,
            "evidence_source_id": self.evidence_source_id,
            "evidence_module": self.evidence_module,
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "closed_required_path_count": self.closed_required_path_count,
            "open_required_path_count": EXPECTED_REQUIRED_PATH_COUNT - self.closed_required_path_count,
            "complete_202_counter_record_to_work_vector_to_comparison_vector_present": self.complete_formal_chain_present,
            "terminal_specific_portable_verifier_present": self.terminal_specific_verifier_present,
            "production_site_implementation_present": self.production_site_implementation_present,
            "observed_campaign_occurrence_bound_by_this_matrix": False,
            "blocker_code": self.blocker_code,
        }

    @property
    def row_id(self) -> str:
        expected = content_id(ROW_DOMAIN, self._payload())
        if expected != self._row_id:
            _fail("terminal coverage row changed after issuance")
        return self._row_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "terminal_accounting_coverage_row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class K7TerminalAccountingCoverageMatrixV1:
    _issuer: InitVar[object]
    all_path_accounting_profile_id: str
    operation_boundary_manifest_id: str
    sources: tuple[K7TerminalAccountingCoverageSourceV1, ...]
    rows: tuple[K7TerminalAccountingCoverageRowV1, ...]
    _matrix_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _MATRIX_ISSUER:
            _fail("terminal coverage matrix is caller-minted")
        _cid(self.all_path_accounting_profile_id, "all-path profile")
        _cid(self.operation_boundary_manifest_id, "operation-boundary manifest")
        if (
            type(self.sources) is not tuple
            or len(self.sources) != EXPECTED_SOURCE_MEMBER_COUNT
            or any(type(row) is not K7TerminalAccountingCoverageSourceV1 for row in self.sources)
            or len({row.module_name for row in self.sources}) != len(self.sources)
            or type(self.rows) is not tuple
            or len(self.rows) != EXPECTED_TERMINAL_CODE_COUNT
            or any(type(row) is not K7TerminalAccountingCoverageRowV1 for row in self.rows)
            or tuple(row.terminal_code for row in self.rows) != tuple(TerminalCode)
        ):
            _fail("terminal coverage matrix cardinality or order changed")
        source_ids = {row.source_id for row in self.sources}
        if any(row.evidence_source_id not in source_ids for row in self.rows):
            _fail("terminal coverage row references a foreign source")
        object.__setattr__(self, "_matrix_id", content_id(MATRIX_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        formal_count = sum(row.complete_formal_chain_present for row in self.rows)
        production_count = sum(row.production_site_implementation_present for row in self.rows)
        fixture_count = sum(
            row.state is TerminalAccountingCoverageStateV1.REGISTERED_FIXTURE_FORMAL_IMPLEMENTATION_ONLY
            for row in self.rows
        )
        partial_count = sum(
            row.state in {
                TerminalAccountingCoverageStateV1.REPLAYABLE_PARTIAL_COVERAGE_ONLY,
                TerminalAccountingCoverageStateV1.REPLAYABLE_READINESS_BLOCKER_ONLY,
            }
            for row in self.rows
        )
        missing_count = sum(
            row.state is TerminalAccountingCoverageStateV1.TERMINAL_SPECIFIC_FORMAL_IMPLEMENTATION_MISSING
            for row in self.rows
        )
        if (
            formal_count != EXPECTED_FORMAL_IMPLEMENTATION_COUNT
            or production_count != EXPECTED_PRODUCTION_SITE_IMPLEMENTATION_COUNT
            or fixture_count != EXPECTED_FIXTURE_ONLY_IMPLEMENTATION_COUNT
            or partial_count != EXPECTED_PARTIAL_OR_READINESS_COUNT
            or missing_count != EXPECTED_MISSING_IMPLEMENTATION_COUNT
        ):
            _fail("terminal coverage summary no longer matches its exact rows")
        return {
            "schema": "acfqp.construction_k7_terminal_accounting_coverage_matrix.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "all_path_accounting_profile_id": self.all_path_accounting_profile_id,
            "operation_boundary_manifest_id": self.operation_boundary_manifest_id,
            "source_member_count": len(self.sources),
            "sources": [row.to_document() for row in self.sources],
            "terminal_code_count": len(self.rows),
            "rows": [row.to_document() for row in self.rows],
            "formal_202_path_implementation_count": formal_count,
            "production_site_formal_implementation_count": production_count,
            "registered_fixture_formal_implementation_only_count": fixture_count,
            "partial_or_readiness_only_count": partial_count,
            "missing_terminal_specific_formal_implementation_count": missing_count,
            "all_terminal_codes_assessed_exactly_once": True,
            "capability_inventory_is_not_observed_campaign_evidence": True,
            "all_path_native_accounting_complete": False,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def matrix_id(self) -> str:
        expected = content_id(MATRIX_DOMAIN, self._payload())
        if expected != self._matrix_id:
            _fail("terminal coverage matrix changed after issuance")
        return self._matrix_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "terminal_accounting_coverage_matrix_id": self.matrix_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _freeze_sources() -> tuple[K7TerminalAccountingCoverageSourceV1, ...]:
    base = Path(__file__).resolve().parent
    rows: list[K7TerminalAccountingCoverageSourceV1] = []
    for spec in _SOURCE_SPECS:
        raw = (base / spec.filename).read_bytes()
        try:
            tree = ast.parse(raw.decode("utf-8", errors="strict"), filename=spec.filename)
        except (UnicodeDecodeError, SyntaxError) as error:
            raise ConstructionK7TerminalAccountingCoverageMatrixV1Error(
                f"{spec.module_name} source is not valid UTF-8 Python"
            ) from error
        symbols = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        if not set(spec.required_public_symbols).issubset(symbols):
            _fail(f"{spec.module_name} public coverage surface changed")
        if _profile_key_from_tree(tree, spec.module_name) != spec.profile_key:
            _fail(f"{spec.module_name} profile key changed")
        rows.append(
            K7TerminalAccountingCoverageSourceV1(
                _SOURCE_ISSUER,
                spec.module_name,
                spec.filename,
                spec.profile_key,
                hashlib.sha256(raw).hexdigest(),
                len(raw),
                tuple(sorted(spec.required_public_symbols)),
            )
        )
    return tuple(rows)


def freeze_k7_terminal_accounting_coverage_matrix_v1() -> K7TerminalAccountingCoverageMatrixV1:
    """Rebuild the exhaustive ten-code capability and gap matrix."""

    profile = profile_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    boundary = boundary_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1()
    sources = _freeze_sources()
    sources_by_module = {row.module_name: row for row in sources}
    rules = profile.terminal_path_rule_by_code
    rows = tuple(
        K7TerminalAccountingCoverageRowV1(
            _ROW_ISSUER,
            spec.terminal_code,
            rules[spec.terminal_code].terminal_class.value,
            spec.state,
            sources_by_module[spec.source_module].source_id,
            spec.source_module,
            spec.closed_required_path_count,
            spec.complete_formal_chain_present,
            spec.terminal_specific_verifier_present,
            spec.production_site_implementation_present,
            spec.blocker_code,
        )
        for spec in _ROW_SPECS
    )
    return K7TerminalAccountingCoverageMatrixV1(
        _MATRIX_ISSUER,
        profile.profile_id,
        boundary.manifest_id,
        sources,
        rows,
    )


@dataclass(frozen=True, slots=True)
class K7TerminalAccountingCoverageReplayV1:
    _issuer: InitVar[object]
    matrix_id: str
    source_ids: tuple[str, ...]
    terminal_code_count: int
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            _fail("terminal coverage replay is caller-minted")
        _cid(self.matrix_id, "terminal coverage matrix")
        if (
            type(self.source_ids) is not tuple
            or len(self.source_ids) != EXPECTED_SOURCE_MEMBER_COUNT
            or len(set(self.source_ids)) != len(self.source_ids)
            or any(_cid(value, "terminal coverage source") != value for value in self.source_ids)
            or self.terminal_code_count != EXPECTED_TERMINAL_CODE_COUNT
        ):
            _fail("terminal coverage replay is incomplete")
        object.__setattr__(self, "_replay_id", content_id(REPLAY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_terminal_accounting_coverage_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_accounting_coverage_matrix_id": self.matrix_id,
            "source_ids": list(self.source_ids),
            "terminal_code_count": self.terminal_code_count,
            "exact_current_source_replay_passed": True,
            "all_path_native_accounting_complete": False,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "official_execution_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        expected = content_id(REPLAY_DOMAIN, self._payload())
        if expected != self._replay_id:
            _fail("terminal coverage replay changed after issuance")
        return self._replay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "terminal_accounting_coverage_replay_id": self.replay_id}


def verify_k7_terminal_accounting_coverage_matrix_bytes_v1(
    raw: bytes,
) -> K7TerminalAccountingCoverageReplayV1:
    """Rebuild current sources and require exact canonical matrix bytes."""

    if type(raw) is not bytes or not raw:
        _fail("terminal coverage matrix bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7TerminalAccountingCoverageMatrixV1Error(
            "terminal coverage matrix bytes are noncanonical"
        ) from error
    expected = freeze_k7_terminal_accounting_coverage_matrix_v1()
    if type(document) is not dict or raw != expected.canonical_bytes:
        _fail("terminal coverage matrix differs from current exact sources")
    return K7TerminalAccountingCoverageReplayV1(
        _REPLAY_ISSUER,
        expected.matrix_id,
        tuple(row.source_id for row in expected.sources),
        len(expected.rows),
    )


__all__ = (
    "ConstructionK7TerminalAccountingCoverageMatrixV1Error",
    "K7TerminalAccountingCoverageMatrixV1",
    "K7TerminalAccountingCoverageReplayV1",
    "K7TerminalAccountingCoverageRowV1",
    "K7TerminalAccountingCoverageSourceV1",
    "TerminalAccountingCoverageStateV1",
    "freeze_k7_terminal_accounting_coverage_matrix_v1",
    "verify_k7_terminal_accounting_coverage_matrix_bytes_v1",
)
