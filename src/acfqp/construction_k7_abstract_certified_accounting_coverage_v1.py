"""Fail-closed K7 accounting coverage audit for ``ABSTRACT_CERTIFIED``.

Contract 2.0.38 asks whether the existing model-only V1 executor and abstract
PASS closure can be promoted to the production V6/K7 accounting chain.  The
answer for the frozen sources is **no**.  This module makes that negative
result exact and replayable instead of translating absent instrumentation into
zeros.

The audit binds one live executor-minted PASS to:

* the exact 202 required V6 leaves and the Contract-2.0.33 terminal recipe;
* the Contract-2.0.36 source-bound operation catalogue;
* seven complete source files plus their selected AST call inventories; and
* every legacy V1 CounterRecord/value actually retained by the execution.

The 202 leaves are partitioned exactly once: 160 have no V1 leaf, 15 have a
positive V1 record but no production occurrence/stage/cutoff evidence, and 27
have only a V1 zero without a V6 profile-native-zero proof.  The report also
records the missing nine shared-resource receipts and eight derived
reconciliation proofs.  It issues no CounterRecord, WorkVector, Comparison
Vector, terminal, certificate, or campaign closure.

The content domains are local to this proposed contract because its caller
explicitly owns the later central-domain registration step.  Consequently the
report keeps the central-registration and all official Gates locked.
"""

from __future__ import annotations

import ast
from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.accounting_v1 import official_counter_registry_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_all_path_accounting_profile_v1 as profile_v1
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as boundary_v1
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp import construction_k7_derived_reconciliation_v2 as derived_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COVERAGE_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COVERAGE_REPORT_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_PATH_GAP_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_SOURCE_ARCHIVE_V1_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_SOURCE_BLOCKER_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    parse_content_id,
)
from acfqp.phase3e_abstract_pass_closure_v1 import (
    verify_model_only_operational_execution_v1,
)
from acfqp.phase3e_model_only_executor_v1 import ModelOnlyQueryExecutionV1
from acfqp.phase3e_model_only_v1 import ModelOnlyOutcome
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.38"
PROFILE_KEY = "construction_k7_abstract_certified_accounting_coverage_v1"

EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_NO_V1_PATH_COUNT = 160
EXPECTED_POSITIVE_V1_PATH_COUNT = 15
EXPECTED_ZERO_ONLY_V1_PATH_COUNT = 27
EXPECTED_SHARED_PATH_COUNT = 9
EXPECTED_DERIVED_PATH_COUNT = 8
EXPECTED_SOURCE_MEMBER_COUNT = 7

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

SOURCE_ARCHIVE_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_SOURCE_ARCHIVE_V1_DOMAIN
PATH_GAP_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_PATH_GAP_V1_DOMAIN
COVERAGE_REPORT_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COVERAGE_REPORT_V1_DOMAIN
)
SOURCE_BLOCKER_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_CERTIFIED_SOURCE_BLOCKER_V1_DOMAIN
)
REPLAY_DOMAIN = CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COVERAGE_REPLAY_V1_DOMAIN

_LOCAL_DOMAINS = frozenset(
    {
        SOURCE_ARCHIVE_DOMAIN,
        PATH_GAP_DOMAIN,
        COVERAGE_REPORT_DOMAIN,
        SOURCE_BLOCKER_DOMAIN,
        REPLAY_DOMAIN,
    }
)
if len(_LOCAL_DOMAINS) != 5 or not _LOCAL_DOMAINS.issubset(  # pragma: no cover
    PHASE3E_DOMAIN_TAGS
):
    raise RuntimeError(
        "K7 abstract-certified coverage domains must be centrally registered"
    )

_REPORT_ISSUER = object()
_PATH_ISSUER = object()


class ConstructionK7AbstractCertifiedAccountingCoverageV1Error(ValueError):
    """A PASS execution, source archive, or frozen coverage partition changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AbstractCertifiedAccountingCoverageV1Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in _LOCAL_DOMAINS:
        _fail("abstract-certified coverage used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AbstractCertifiedAccountingCoverageV1Error(
            f"{label} must be one exact content ID"
        ) from error


class PathGapCodeV1(str, Enum):
    NO_V1_COUNTER_LEAF_OR_EMISSION = "NO_V1_COUNTER_LEAF_OR_EMISSION"
    POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE = (
        "POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE"
    )
    ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE = (
        "ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE"
    )


class SourceBlockerCodeV1(str, Enum):
    SOURCE_MEMBER_SET_CHANGED = "SOURCE_MEMBER_SET_CHANGED"
    SOURCE_MEMBER_NOT_BYTES = "SOURCE_MEMBER_NOT_BYTES"
    SOURCE_BYTES_CHANGED = "SOURCE_BYTES_CHANGED"
    SOURCE_SYNTAX_INVALID = "SOURCE_SYNTAX_INVALID"
    SOURCE_HOOK_INVENTORY_CHANGED = "SOURCE_HOOK_INVENTORY_CHANGED"
    REPORT_DOCUMENT_CHANGED = "REPORT_DOCUMENT_CHANGED"


class ReplayOutcomeV1(str, Enum):
    ACCOUNTING_BLOCKED = "ACCOUNTING_BLOCKED"
    SOURCE_BLOCKED = "SOURCE_BLOCKED"
    DOCUMENT_BLOCKED = "DOCUMENT_BLOCKED"


class EvidenceCoverageStatusV1(str, Enum):
    PASS_VALUE_PRESENT_BUT_NO_PRODUCTION_TYPED_ATTESTATION = (
        "PASS_VALUE_PRESENT_BUT_NO_PRODUCTION_TYPED_ATTESTATION"
    )
    MISSING_COMPLETE_V6_COUNTER_RECORD_SET = "MISSING_COMPLETE_V6_COUNTER_RECORD_SET"
    LEGACY_V1_VECTOR_NOT_V6 = "LEGACY_V1_VECTOR_NOT_V6"
    MISSING_EXACT_NINE_PATH_RECEIPT_SET = "MISSING_EXACT_NINE_PATH_RECEIPT_SET"
    MISSING_EXACT_EIGHT_PATH_RECONCILIATION = (
        "MISSING_EXACT_EIGHT_PATH_RECONCILIATION"
    )
    FORBIDDEN_UNTIL_V6_ACCOUNTING_CLOSES = "FORBIDDEN_UNTIL_V6_ACCOUNTING_CLOSES"


@dataclass(frozen=True, slots=True)
class _SourceSpecV1:
    module_name: str
    relative_path: str
    source_byte_count: int
    source_sha256: str


_SOURCE_SPECS_V1 = (
    _SourceSpecV1(
        "acfqp.phase3e_abstract_pass_closure_v1",
        "phase3e_abstract_pass_closure_v1.py",
        40335,
        "80cc53faa2f887672831ac0c3ed414845112f69d176ac72e9032c09e8d7d3df7",
    ),
    _SourceSpecV1(
        "acfqp.phase3e_model_only_executor_v1",
        "phase3e_model_only_executor_v1.py",
        49369,
        "72316906c0e89b7d18daef2f4e1d4dde5b97c26a0babbc68092053b8a98d8f75",
    ),
    _SourceSpecV1(
        "acfqp.phase3e_model_only_runtime_v1",
        "phase3e_model_only_runtime_v1.py",
        5485,
        "ea99fb5467d86ff84a092eab1ca02567be8050bcc1dddc3b14b68a61dc737de9",
    ),
    _SourceSpecV1(
        "acfqp.phase3e_model_only_v1",
        "phase3e_model_only_v1.py",
        27460,
        "00af2fd30f9666afe31d2af80846288ca7daadab622183493a2170bf36d81084",
    ),
    _SourceSpecV1(
        "acfqp.phase3e_rapm_consumer_v1",
        "phase3e_rapm_consumer_v1.py",
        46760,
        "3e7c979a49a61c517fef3379220496af232fe76964dd41995012aa09fbbb6d42",
    ),
    _SourceSpecV1(
        "acfqp.portable_planner",
        "portable_planner.py",
        37861,
        "4eafd44be1830004a4726ff481d5a5a6ce5f67f720e63210af165fcea7f05054",
    ),
    _SourceSpecV1(
        "acfqp.portable_sound_audit_v1",
        "portable_sound_audit_v1.py",
        33592,
        "4dfe0a078670052e1c5f94578edbb25f2cf0dd98596df407490b78d64b147a8a",
    ),
)


@dataclass(frozen=True, slots=True)
class _HookSpecV1:
    module_name: str
    symbol_qualname: str
    call_target: str
    expected_count: int


_HOOK_SPECS_V1 = (
    _HookSpecV1("acfqp.phase3e_model_only_runtime_v1", "main", "count", 7),
    _HookSpecV1(
        "acfqp.phase3e_model_only_runtime_v1",
        "main",
        "run_phase3e_model_only_from_source_v1",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_executor_v1",
        "execute_model_only_query_v1",
        "subprocess.run",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_executor_v1",
        "execute_model_only_query_v1",
        "recorder.add",
        7,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_executor_v1",
        "execute_model_only_query_v1",
        "recorder.observe_peak",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_executor_v1",
        "execute_model_only_query_v1",
        "recorder.record_process_completion",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_executor_v1",
        "execute_model_only_query_v1",
        "recorder.record_solver_completion",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_executor_v1",
        "execute_model_only_query_v1",
        "recorder.record_route_completion",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_v1",
        "run_phase3e_model_only_from_source_v1",
        "select_contingent_plan_v1",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_v1",
        "run_phase3e_model_only_from_source_v1",
        "build_portable_sound_audit_v1",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_model_only_v1",
        "run_phase3e_model_only_from_source_v1",
        "verify_portable_sound_audit_v1",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_rapm_consumer_v1",
        "select_contingent_plan_v1",
        "solve_portable_pareto",
        1,
    ),
    _HookSpecV1(
        "acfqp.portable_planner", "solve_portable_pareto", "operation_counter", 1
    ),
    _HookSpecV1(
        "acfqp.portable_sound_audit_v1", "_build_proof", "operation_counter", 5
    ),
    _HookSpecV1(
        "acfqp.portable_sound_audit_v1",
        "build_portable_sound_audit_v1",
        "operation_counter",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_abstract_pass_closure_v1",
        "close_model_only_abstract_pass_v1",
        "TerminalArtifactV1",
        1,
    ),
    _HookSpecV1(
        "acfqp.phase3e_abstract_pass_closure_v1",
        "close_model_only_abstract_pass_v1",
        "CampaignOccurrenceClosureV1.close",
        1,
    ),
)


_POSITIVE_V1_PATHS = frozenset(
    {
        "common.abstract_audit_obligations",
        "common.abstract_bellman_backups",
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "memory.working_bytes_peak",
        "process.exit_successes",
        "process.launches",
        "route.attempts",
        "route.successes",
        "solver.attempts",
        "solver.successes",
    }
)


def load_official_abstract_certified_source_archive_v1() -> dict[str, bytes]:
    root = Path(__file__).resolve().parent
    return {
        spec.module_name: (root / spec.relative_path).read_bytes()
        for spec in _SOURCE_SPECS_V1
    }


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return None


def _qualified_symbols(tree: ast.Module) -> dict[str, tuple[ast.AST, ...]]:
    found: dict[str, list[ast.AST]] = {}

    def visit(body: Sequence[ast.stmt], prefix: str = "") -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}.{node.name}" if prefix else node.name
                found.setdefault(name, []).append(node)
                visit(node.body, name)

    visit(tree.body)
    return {key: tuple(value) for key, value in found.items()}


@dataclass(frozen=True, slots=True, order=True)
class SourceReplayBlockerV1:
    module_name: str
    code: SourceBlockerCodeV1
    detail: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "code", SourceBlockerCodeV1(self.code))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedAccountingCoverageV1Error(
                "source blocker code is invalid"
            ) from error
        if not self.module_name or not self.detail:
            _fail("source replay blocker is incomplete")

    @property
    def blocker_id(self) -> str:
        return _content_id(SOURCE_BLOCKER_DOMAIN, self._payload())

    def _payload(self) -> dict[str, str]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_source_blocker.v1",
            "schema_version": SCHEMA_VERSION,
            "module_name": self.module_name,
            "code": self.code.value,
            "detail": self.detail,
        }

    def to_document(self) -> dict[str, str]:
        return {**self._payload(), "source_blocker_id": self.blocker_id}


def _source_replay(
    source_archive: Mapping[str, bytes],
) -> tuple[str | None, tuple[dict[str, Any], ...], tuple[SourceReplayBlockerV1, ...]]:
    if not isinstance(source_archive, Mapping):
        _fail("source archive must be one module-to-bytes mapping")
    expected = {row.module_name: row for row in _SOURCE_SPECS_V1}
    blockers: list[SourceReplayBlockerV1] = []
    supplied_keys = {key for key in source_archive if type(key) is str}
    if supplied_keys != set(expected):
        blockers.append(
            SourceReplayBlockerV1(
                "acfqp.*",
                SourceBlockerCodeV1.SOURCE_MEMBER_SET_CHANGED,
                "source archive member set differs from the seven frozen modules",
            )
        )
    trees: dict[str, ast.Module] = {}
    members: list[dict[str, Any]] = []
    for module, spec in sorted(expected.items()):
        raw = source_archive.get(module)
        if type(raw) is not bytes:
            blockers.append(
                SourceReplayBlockerV1(
                    module,
                    SourceBlockerCodeV1.SOURCE_MEMBER_NOT_BYTES,
                    "source archive member is absent or not exact bytes",
                )
            )
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if len(raw) != spec.source_byte_count or digest != spec.source_sha256:
            blockers.append(
                SourceReplayBlockerV1(
                    module,
                    SourceBlockerCodeV1.SOURCE_BYTES_CHANGED,
                    "complete source bytes differ from the frozen count or SHA-256",
                )
            )
            continue
        try:
            trees[module] = ast.parse(raw, filename=spec.relative_path)
        except (SyntaxError, ValueError, TypeError):
            blockers.append(
                SourceReplayBlockerV1(
                    module,
                    SourceBlockerCodeV1.SOURCE_SYNTAX_INVALID,
                    "frozen source bytes do not parse as Python",
                )
            )
            continue
        members.append(
            {
                "module_name": module,
                "relative_path": spec.relative_path,
                "source_byte_count": len(raw),
                "source_sha256": digest,
            }
        )

    hook_rows: list[dict[str, Any]] = []
    if not blockers:
        symbols = {module: _qualified_symbols(tree) for module, tree in trees.items()}
        for spec in _HOOK_SPECS_V1:
            selected = symbols[spec.module_name].get(spec.symbol_qualname, ())
            if len(selected) != 1:
                blockers.append(
                    SourceReplayBlockerV1(
                        spec.module_name,
                        SourceBlockerCodeV1.SOURCE_HOOK_INVENTORY_CHANGED,
                        f"symbol {spec.symbol_qualname} is missing or ambiguous",
                    )
                )
                continue
            count = sum(
                1
                for node in ast.walk(selected[0])
                if isinstance(node, ast.Call)
                and _call_name(node.func) == spec.call_target
            )
            if count != spec.expected_count:
                blockers.append(
                    SourceReplayBlockerV1(
                        spec.module_name,
                        SourceBlockerCodeV1.SOURCE_HOOK_INVENTORY_CHANGED,
                        (
                            f"{spec.symbol_qualname}:{spec.call_target} has {count} "
                            f"calls, expected {spec.expected_count}"
                        ),
                    )
                )
                continue
            hook_rows.append(
                {
                    "module_name": spec.module_name,
                    "symbol_qualname": spec.symbol_qualname,
                    "call_target": spec.call_target,
                    "call_count": count,
                }
            )
    if blockers:
        return None, (), tuple(sorted(set(blockers)))
    payload = {
        "schema": "acfqp.construction_k7_abstract_certified_source_archive.v1",
        "schema_version": SCHEMA_VERSION,
        "members": members,
        "selected_hook_inventory": hook_rows,
        "complete_member_bytes_replayed": True,
        "selected_ast_call_inventory_replayed": True,
    }
    return _content_id(SOURCE_ARCHIVE_DOMAIN, payload), tuple(members), ()


@dataclass(frozen=True, slots=True, order=True)
class RequiredPathCoverageGapV1:
    _issuer: InitVar[object]
    path: str
    semantics_id: str
    owner: str
    lane: str
    scope: str
    reducer: str
    comparison_axis: str | None
    stage_contexts: tuple[tuple[str, str], ...]
    code: PathGapCodeV1
    legacy_v1_record_id: str | None
    legacy_v1_value: int | None
    _gap_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PATH_ISSUER:
            _fail("required-path coverage gap is caller-minted")
        try:
            object.__setattr__(self, "code", PathGapCodeV1(self.code))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedAccountingCoverageV1Error(
                "required-path gap code is invalid"
            ) from error
        if (
            not self.path
            or not self.semantics_id
            or not self.owner
            or not self.lane
            or not self.scope
            or not self.reducer
            or not self.stage_contexts
            or tuple(sorted(self.stage_contexts)) != self.stage_contexts
            or len(set(self.stage_contexts)) != len(self.stage_contexts)
        ):
            _fail("required-path coverage gap is incomplete")
        if self.legacy_v1_record_id is None:
            if self.legacy_v1_value is not None or self.code is not (
                PathGapCodeV1.NO_V1_COUNTER_LEAF_OR_EMISSION
            ):
                _fail("path without a V1 record has inconsistent evidence")
        else:
            _cid(self.legacy_v1_record_id, "legacy V1 counter record")
            if type(self.legacy_v1_value) is not int or self.legacy_v1_value < 0:
                _fail("legacy V1 value must be nonnegative")
            expected = (
                PathGapCodeV1
                .POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
                if self.legacy_v1_value > 0
                else PathGapCodeV1
                .ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE
            )
            if self.code is not expected:
                _fail("legacy V1 value and gap code disagree")
        object.__setattr__(self, "_gap_id", _content_id(PATH_GAP_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_path_gap.v1",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "lane": self.lane,
            "scope": self.scope,
            "reducer": self.reducer,
            "comparison_axis": self.comparison_axis,
            "stage_contexts": [
                {"stage_kind": stage, "abstract_certified_disposition": disposition}
                for stage, disposition in self.stage_contexts
            ],
            "gap_code": self.code.value,
            "legacy_v1_record_id": self.legacy_v1_record_id,
            "legacy_v1_value": self.legacy_v1_value,
            "missing_event_inferred_zero": False,
            "v6_counter_record_authorized": False,
        }

    @property
    def gap_id(self) -> str:
        if _content_id(PATH_GAP_DOMAIN, self._payload()) != self._gap_id:
            _fail("required-path coverage gap changed after issuance")
        return self._gap_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "path_gap_id": self.gap_id}


@dataclass(frozen=True, slots=True, order=True)
class EvidenceCoverageRowV1:
    role: str
    required_outcome: str
    profile_authority_state: str
    coverage_status: EvidenceCoverageStatusV1

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self, "coverage_status", EvidenceCoverageStatusV1(self.coverage_status)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedAccountingCoverageV1Error(
                "evidence coverage status is invalid"
            ) from error
        if not self.role or not self.required_outcome or not self.profile_authority_state:
            _fail("evidence coverage row is incomplete")

    def to_document(self) -> dict[str, str]:
        return {
            "role": self.role,
            "required_outcome": self.required_outcome,
            "profile_authority_state": self.profile_authority_state,
            "coverage_status": self.coverage_status.value,
        }


@dataclass(frozen=True, slots=True)
class AbstractCertifiedAccountingCoverageReportV1:
    _issuer: InitVar[object]
    source_archive_id: str
    source_members: tuple[dict[str, Any], ...]
    all_path_accounting_profile_id: str
    operation_boundary_manifest_id: str
    v6_counter_registry_id: str
    v6_stage_profile_id: str
    legacy_v1_counter_registry_id: str
    operational_execution_id: str
    model_only_result_id: str
    abstract_audit_id: str
    legacy_v1_work_vector_id: str
    legacy_v1_comparison_vector_id: str
    path_gaps: tuple[RequiredPathCoverageGapV1, ...]
    evidence_coverage: tuple[EvidenceCoverageRowV1, ...]
    _report_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPORT_ISSUER:
            _fail("abstract-certified coverage report is caller-minted")
        for value, label in (
            (self.source_archive_id, "source archive"),
            (self.all_path_accounting_profile_id, "all-path accounting profile"),
            (self.operation_boundary_manifest_id, "operation-boundary manifest"),
            (self.v6_counter_registry_id, "V6 counter registry"),
            (self.v6_stage_profile_id, "V6 stage profile"),
            (self.legacy_v1_counter_registry_id, "legacy V1 counter registry"),
            (self.operational_execution_id, "operational execution"),
            (self.model_only_result_id, "model-only result"),
            (self.abstract_audit_id, "abstract audit"),
            (self.legacy_v1_work_vector_id, "legacy V1 work vector"),
            (self.legacy_v1_comparison_vector_id, "legacy V1 comparison vector"),
        ):
            _cid(value, label)
        if (
            len(self.source_members) != EXPECTED_SOURCE_MEMBER_COUNT
            or len(self.path_gaps) != EXPECTED_REQUIRED_PATH_COUNT
            or tuple(row.path for row in self.path_gaps)
            != tuple(sorted(row.path for row in self.path_gaps))
            or len({row.path for row in self.path_gaps}) != len(self.path_gaps)
            or tuple(sorted(self.evidence_coverage)) != self.evidence_coverage
        ):
            _fail("abstract-certified coverage cardinality or ordering changed")
        counts = {code: 0 for code in PathGapCodeV1}
        for row in self.path_gaps:
            counts[row.code] += 1
        if counts != {
            PathGapCodeV1.NO_V1_COUNTER_LEAF_OR_EMISSION: EXPECTED_NO_V1_PATH_COUNT,
            PathGapCodeV1.POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE: EXPECTED_POSITIVE_V1_PATH_COUNT,
            PathGapCodeV1.ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE: EXPECTED_ZERO_ONLY_V1_PATH_COUNT,
        }:
            _fail("abstract-certified exact 160/15/27 partition changed")
        object.__setattr__(
            self, "_report_id", _content_id(COVERAGE_REPORT_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_accounting_coverage_report.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_code_assessed": TerminalCode.ABSTRACT_CERTIFIED.value,
            "source_archive_id": self.source_archive_id,
            "source_members": list(self.source_members),
            "all_path_accounting_profile_id": self.all_path_accounting_profile_id,
            "operation_boundary_manifest_id": self.operation_boundary_manifest_id,
            "v6_counter_registry_id": self.v6_counter_registry_id,
            "v6_stage_profile_id": self.v6_stage_profile_id,
            "legacy_v1_counter_registry_id": self.legacy_v1_counter_registry_id,
            "operational_execution_id": self.operational_execution_id,
            "model_only_result_id": self.model_only_result_id,
            "abstract_audit_id": self.abstract_audit_id,
            "legacy_v1_work_vector_id": self.legacy_v1_work_vector_id,
            "legacy_v1_comparison_vector_id": self.legacy_v1_comparison_vector_id,
            "path_gaps": [row.to_document() for row in self.path_gaps],
            "evidence_coverage": [row.to_document() for row in self.evidence_coverage],
            "existing_selected_hook_sites": [
                {
                    "module_name": row.module_name,
                    "symbol_qualname": row.symbol_qualname,
                    "call_target": row.call_target,
                    "call_count": row.expected_count,
                }
                for row in _HOOK_SPECS_V1
            ],
            "minimum_missing_runtime_hook_paths": [
                row.path
                for row in self.path_gaps
                if row.code is PathGapCodeV1.NO_V1_COUNTER_LEAF_OR_EMISSION
            ],
            "minimum_v6_occurrence_stage_cutoff_upgrade_paths": [
                row.path
                for row in self.path_gaps
                if row.code
                is PathGapCodeV1.POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
            ],
            "minimum_v6_profile_native_zero_proof_paths": [
                row.path
                for row in self.path_gaps
                if row.code
                is PathGapCodeV1.ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE
            ],
            "required_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "no_v1_path_count": EXPECTED_NO_V1_PATH_COUNT,
            "positive_v1_path_without_v6_evidence_count": EXPECTED_POSITIVE_V1_PATH_COUNT,
            "zero_v1_path_without_v6_zero_proof_count": EXPECTED_ZERO_ONLY_V1_PATH_COUNT,
            "missing_shared_resource_paths": list(shared_v1.SHARED_RESOURCE_PATHS),
            "missing_derived_reconciliation_paths": list(derived_v2.V1_BASE_PATHS + derived_v2.ROUTE_PATHS),
            "shared_resource_path_count": EXPECTED_SHARED_PATH_COUNT,
            "derived_reconciliation_path_count": EXPECTED_DERIVED_PATH_COUNT,
            "source_and_selected_ast_hooks_replayed": True,
            "host_full_planner_replay_performed": False,
            "ground_access_performed": False,
            "missing_instrumentation_interpreted_as_zero": False,
            "legacy_terminal_promoted": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "terminal_artifact_id": None,
            "campaign_occurrence_closure_id": None,
            "certificate_issued": False,
            "production_completion_status": "BLOCKED_INCOMPLETE_V6_SOURCE_EVIDENCE",
            "central_domain_registration_pending": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    @property
    def report_id(self) -> str:
        if _content_id(COVERAGE_REPORT_DOMAIN, self._payload()) != self._report_id:
            _fail("abstract-certified coverage report changed after issuance")
        return self._report_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "coverage_report_id": self.report_id}


def _evidence_coverage(
    rule: profile_v1.TerminalPathRuleV1,
) -> tuple[EvidenceCoverageRowV1, ...]:
    status = {
        "ABSTRACT_AUDIT": EvidenceCoverageStatusV1.PASS_VALUE_PRESENT_BUT_NO_PRODUCTION_TYPED_ATTESTATION,
        "COUNTER_RECORD_SET": EvidenceCoverageStatusV1.MISSING_COMPLETE_V6_COUNTER_RECORD_SET,
        "WORK_VECTOR": EvidenceCoverageStatusV1.LEGACY_V1_VECTOR_NOT_V6,
        "ACTUAL_PROJECTION": EvidenceCoverageStatusV1.LEGACY_V1_VECTOR_NOT_V6,
        "SHARED_RESOURCE_RECEIPT_SET": EvidenceCoverageStatusV1.MISSING_EXACT_NINE_PATH_RECEIPT_SET,
        "DERIVED_RECONCILIATION": EvidenceCoverageStatusV1.MISSING_EXACT_EIGHT_PATH_RECONCILIATION,
        "TERMINAL_CLASSIFICATION": EvidenceCoverageStatusV1.FORBIDDEN_UNTIL_V6_ACCOUNTING_CLOSES,
        "OCCURRENCE_TERMINAL": EvidenceCoverageStatusV1.FORBIDDEN_UNTIL_V6_ACCOUNTING_CLOSES,
    }
    if set(status) != {row.role for row in rule.required_evidence_roles}:
        _fail("ABSTRACT_CERTIFIED evidence-role inventory changed")
    return tuple(
        sorted(
            EvidenceCoverageRowV1(
                row.role,
                row.required_outcome,
                row.authority_state.value,
                status[row.role],
            )
            for row in rule.required_evidence_roles
        )
    )


def audit_abstract_certified_accounting_coverage_v1(
    execution: ModelOnlyQueryExecutionV1,
    *,
    source_archive: Mapping[str, bytes] | None = None,
) -> AbstractCertifiedAccountingCoverageReportV1:
    """Return the exact nonterminal blocker for one live model-only PASS."""

    retained = verify_model_only_operational_execution_v1(execution)
    result = retained.model_only_result
    if result.outcome is not ModelOnlyOutcome.PASS or result.ground_binding_required:
        _fail("ABSTRACT_CERTIFIED coverage audit requires one retained PASS")

    archive = (
        load_official_abstract_certified_source_archive_v1()
        if source_archive is None
        else source_archive
    )
    source_archive_id, source_members, source_blockers = _source_replay(archive)
    if source_blockers or source_archive_id is None:
        error = ConstructionK7AbstractCertifiedAccountingCoverageV1Error(
            "abstract-certified source replay is blocked"
        )
        error.blockers = source_blockers  # type: ignore[attr-defined]
        raise error

    all_path = profile_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    boundary = boundary_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1()
    rule = all_path.terminal_path_rule_by_code[TerminalCode.ABSTRACT_CERTIFIED]
    v6 = registry_v6.official_counter_registry_v6()
    v6.validate_official_catalogue()
    stages = registry_v6.official_stage_profile_v6(v6)
    stages.validate(v6)
    v1 = official_counter_registry_v1()
    v1.validate_official_catalogue()

    v1_paths = set(v1.by_path)
    v6_paths = set(v6.required_paths)
    overlap = v1_paths & v6_paths
    if (
        len(overlap) != EXPECTED_POSITIVE_V1_PATH_COUNT + EXPECTED_ZERO_ONLY_V1_PATH_COUNT
        or v6_paths - v1_paths != set(v6.required_paths) - overlap
        or len(v6_paths - v1_paths) != EXPECTED_NO_V1_PATH_COUNT
        or not _POSITIVE_V1_PATHS <= overlap
        or any(v1.by_path[path].to_dict() != v6.by_path[path].to_dict() for path in overlap)
    ):
        _fail("V1/V6 exact leaf overlap changed")

    vector = retained.recorded_work.work_vector
    records = {row.path: row for row in vector.records}
    observed_positive = {path for path in overlap if vector.value(path) > 0}
    if observed_positive != _POSITIVE_V1_PATHS:
        _fail("model-only PASS positive V1 path set changed")

    stage_disposition = {row.stage_kind: row.disposition for row in rule.stage_plan}
    path_gaps: list[RequiredPathCoverageGapV1] = []
    for path in v6.required_paths:
        leaf = v6.by_path[path]
        contexts = tuple(
            sorted(
                (
                    stage_rule.stage_kind.value,
                    stage_disposition[stage_rule.stage_kind].value,
                )
                for stage_rule in stages.rules
                if path in stage_rule.allowed_nonzero_paths
            )
        )
        if not contexts:
            _fail(f"required V6 path {path} has no stage context")
        if path not in overlap:
            code = PathGapCodeV1.NO_V1_COUNTER_LEAF_OR_EMISSION
            record_id = None
            value = None
        else:
            record = records[path]
            record_id = record.record_id
            value = record.value
            code = (
                PathGapCodeV1
                .POSITIVE_V1_RECORD_LACKS_V6_OCCURRENCE_STAGE_CUTOFF_EVIDENCE
                if value > 0
                else PathGapCodeV1
                .ZERO_V1_RECORD_LACKS_V6_PROFILE_NATIVE_ZERO_EVIDENCE
            )
        path_gaps.append(
            RequiredPathCoverageGapV1(
                _PATH_ISSUER,
                path,
                leaf.semantics_id,
                leaf.owner,
                leaf.lane.value,
                leaf.scope,
                leaf.reducer.value,
                leaf.comparison_axis,
                contexts,
                code,
                record_id,
                value,
            )
        )

    return AbstractCertifiedAccountingCoverageReportV1(
        _REPORT_ISSUER,
        source_archive_id,
        source_members,
        all_path.profile_id,
        boundary.manifest_id,
        v6.registry_id,
        stages.stage_profile_id,
        v1.registry_id,
        retained.operational_execution_id,
        result.result_id,
        result.audit.audit_id,
        vector.work_vector_id,
        retained.recorded_work.comparison_vector.comparison_vector_id,
        tuple(sorted(path_gaps, key=lambda row: row.path)),
        _evidence_coverage(rule),
    )


@dataclass(frozen=True, slots=True)
class AbstractCertifiedCoverageReplayV1:
    outcome: ReplayOutcomeV1
    execution_id: str
    report: AbstractCertifiedAccountingCoverageReportV1 | None
    blockers: tuple[SourceReplayBlockerV1, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "outcome", ReplayOutcomeV1(self.outcome))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AbstractCertifiedAccountingCoverageV1Error(
                "coverage replay outcome is invalid"
            ) from error
        _cid(self.execution_id, "coverage replay execution")
        if (
            (self.outcome is ReplayOutcomeV1.ACCOUNTING_BLOCKED)
            != (self.report is not None and not self.blockers)
            or (self.outcome in {ReplayOutcomeV1.SOURCE_BLOCKED, ReplayOutcomeV1.DOCUMENT_BLOCKED})
            != (self.report is None and bool(self.blockers))
            or tuple(sorted(self.blockers)) != self.blockers
        ):
            _fail("coverage replay outcome is inconsistent")

    @property
    def replay_id(self) -> str:
        return _content_id(
            REPLAY_DOMAIN,
            {
                "schema": "acfqp.construction_k7_abstract_certified_coverage_replay.v1",
                "schema_version": SCHEMA_VERSION,
                "outcome": self.outcome.value,
                "execution_id": self.execution_id,
                "coverage_report_id": None if self.report is None else self.report.report_id,
                "blocker_ids": [row.blocker_id for row in self.blockers],
                "terminal_issued": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_abstract_certified_coverage_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "outcome": self.outcome.value,
            "execution_id": self.execution_id,
            "coverage_report_id": None if self.report is None else self.report.report_id,
            "blockers": [row.to_document() for row in self.blockers],
            "terminal_issued": False,
            "replay_id": self.replay_id,
        }


def replay_abstract_certified_accounting_coverage_v1(
    execution: ModelOnlyQueryExecutionV1,
    *,
    source_archive: Mapping[str, bytes] | None = None,
) -> AbstractCertifiedCoverageReplayV1:
    """Replay source/accounting coverage without ever terminalizing the PASS."""

    retained = verify_model_only_operational_execution_v1(execution)
    archive = (
        load_official_abstract_certified_source_archive_v1()
        if source_archive is None
        else source_archive
    )
    _archive_id, _members, blockers = _source_replay(archive)
    if blockers:
        return AbstractCertifiedCoverageReplayV1(
            ReplayOutcomeV1.SOURCE_BLOCKED,
            retained.operational_execution_id,
            None,
            blockers,
        )
    report = audit_abstract_certified_accounting_coverage_v1(
        retained, source_archive=archive
    )
    return AbstractCertifiedCoverageReplayV1(
        ReplayOutcomeV1.ACCOUNTING_BLOCKED,
        retained.operational_execution_id,
        report,
        (),
    )


def verify_abstract_certified_accounting_coverage_document_v1(
    document: Mapping[str, Any],
    execution: ModelOnlyQueryExecutionV1,
    *,
    source_archive: Mapping[str, bytes] | None = None,
) -> AbstractCertifiedCoverageReplayV1:
    """Independently rebuild and byte-compare one proposed coverage report."""

    replay = replay_abstract_certified_accounting_coverage_v1(
        execution, source_archive=source_archive
    )
    if replay.outcome is not ReplayOutcomeV1.ACCOUNTING_BLOCKED:
        return replay
    assert replay.report is not None
    if type(document) is not dict or canonical_json_bytes(document) != canonical_json_bytes(
        replay.report.to_document()
    ):
        blocker = SourceReplayBlockerV1(
            "acfqp.construction_k7_abstract_certified_accounting_coverage_v1",
            SourceBlockerCodeV1.REPORT_DOCUMENT_CHANGED,
            "supplied report differs from the independently rebuilt blocker",
        )
        return AbstractCertifiedCoverageReplayV1(
            ReplayOutcomeV1.DOCUMENT_BLOCKED,
            replay.execution_id,
            None,
            (blocker,),
        )
    return replay


__all__ = [
    "AbstractCertifiedAccountingCoverageReportV1",
    "AbstractCertifiedCoverageReplayV1",
    "ConstructionK7AbstractCertifiedAccountingCoverageV1Error",
    "EvidenceCoverageStatusV1",
    "PathGapCodeV1",
    "ReplayOutcomeV1",
    "RequiredPathCoverageGapV1",
    "SourceBlockerCodeV1",
    "SourceReplayBlockerV1",
    "audit_abstract_certified_accounting_coverage_v1",
    "load_official_abstract_certified_source_archive_v1",
    "replay_abstract_certified_accounting_coverage_v1",
    "verify_abstract_certified_accounting_coverage_document_v1",
]
