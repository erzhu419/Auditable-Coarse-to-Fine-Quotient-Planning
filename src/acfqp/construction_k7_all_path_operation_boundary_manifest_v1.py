"""Exact source-bound operation catalogue for K7 all-path accounting.

Contract 2.0.36 closes a narrower question than native accounting: it records
where the already-existing PREOPEN, ABSTRACT, LOCAL, FALLBACK, REBUILD and
terminal-verification control seams actually live.  A catalogue entry is
accepted only when the complete archived module bytes, the enclosing AST
symbol and the selected call expression all match the frozen source.

This module never executes any of those sites and never fabricates an event,
counter, zero, WorkVector or terminal.  Missing or changed source is returned
as a typed blocker.  Consequently this catalogue can be used to place future
accounting hooks, but cannot itself satisfy an accounting obligation.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.accounting_v1 import RouteKindEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_all_path_accounting_profile_v1 as profile_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_BLOCKER_V1_DOMAIN,
    CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_MANIFEST_V1_DOMAIN,
    CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_REPLAY_V1_DOMAIN,
    CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_SITE_V1_DOMAIN,
    CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_SOURCE_ARCHIVE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    parse_content_id,
)
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.36"
PROFILE_KEY = "construction_k7_all_path_operation_boundary_manifest_v1"

MANIFEST_DOMAIN = CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_MANIFEST_V1_DOMAIN
SOURCE_ARCHIVE_DOMAIN = (
    CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_SOURCE_ARCHIVE_V1_DOMAIN
)
SITE_DOMAIN = CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_SITE_V1_DOMAIN
REPLAY_DOMAIN = CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_REPLAY_V1_DOMAIN
BLOCKER_DOMAIN = CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_BLOCKER_V1_DOMAIN

_LOCAL_DOMAINS = frozenset(
    {
        MANIFEST_DOMAIN,
        SOURCE_ARCHIVE_DOMAIN,
        SITE_DOMAIN,
        REPLAY_DOMAIN,
        BLOCKER_DOMAIN,
    }
)
if len(_LOCAL_DOMAINS) != 5 or not _LOCAL_DOMAINS.issubset(  # pragma: no cover
    PHASE3E_DOMAIN_TAGS
):
    raise RuntimeError(
        "K7 operation-boundary domains must be unique and centrally registered"
    )

EXPECTED_BOUNDARY_FAMILY_COUNT = 6
EXPECTED_SITE_COUNT = 10
EXPECTED_SOURCE_MEMBER_COUNT = 6

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

_ISSUER = object()


class ConstructionK7AllPathOperationBoundaryManifestV1Error(ValueError):
    """A caller tried to mint or mutate the frozen operation catalogue."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AllPathOperationBoundaryManifestV1Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class BoundaryFamilyV1(str, Enum):
    PREOPEN_COMMON = "PREOPEN_COMMON"
    ABSTRACT = "ABSTRACT"
    LOCAL = "LOCAL"
    FALLBACK = "FALLBACK"
    REBUILD = "REBUILD"
    VERIFICATION_TERMINAL = "VERIFICATION_TERMINAL"


class BoundaryReplayOutcomeV1(str, Enum):
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"


class BoundaryBlockerCodeV1(str, Enum):
    PROFILE_ID_CHANGED = "PROFILE_ID_CHANGED"
    SOURCE_MEMBER_SET_CHANGED = "SOURCE_MEMBER_SET_CHANGED"
    SOURCE_MEMBER_MISSING = "SOURCE_MEMBER_MISSING"
    SOURCE_MEMBER_NOT_BYTES = "SOURCE_MEMBER_NOT_BYTES"
    SOURCE_BYTES_CHANGED = "SOURCE_BYTES_CHANGED"
    SOURCE_SYNTAX_INVALID = "SOURCE_SYNTAX_INVALID"
    AST_SYMBOL_MISSING = "AST_SYMBOL_MISSING"
    AST_SYMBOL_AMBIGUOUS = "AST_SYMBOL_AMBIGUOUS"
    SYMBOL_AST_CHANGED = "SYMBOL_AST_CHANGED"
    CALL_SITE_MISSING = "CALL_SITE_MISSING"
    CALL_SITE_CARDINALITY_CHANGED = "CALL_SITE_CARDINALITY_CHANGED"
    CALL_SITE_LOCATION_CHANGED = "CALL_SITE_LOCATION_CHANGED"
    CALL_SITE_AST_CHANGED = "CALL_SITE_AST_CHANGED"
    MANIFEST_DOCUMENT_CHANGED = "MANIFEST_DOCUMENT_CHANGED"


@dataclass(frozen=True, slots=True, order=True)
class BoundaryBlockerV1:
    family: BoundaryFamilyV1
    site_key: str
    code: BoundaryBlockerCodeV1
    module_name: str
    symbol_qualname: str
    detail: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "family", BoundaryFamilyV1(self.family))
            object.__setattr__(self, "code", BoundaryBlockerCodeV1(self.code))
        except (TypeError, ValueError) as error:
            raise ConstructionK7AllPathOperationBoundaryManifestV1Error(
                "operation-boundary blocker taxonomy is invalid"
            ) from error
        if not all(
            type(value) is str and value
            for value in (
                self.site_key,
                self.module_name,
                self.symbol_qualname,
                self.detail,
            )
        ):
            _fail("operation-boundary blocker text is invalid")

    @property
    def blocker_id(self) -> str:
        return _content_id(BLOCKER_DOMAIN, self._payload())

    def _payload(self) -> dict[str, str]:
        return {
            "schema": "acfqp.construction_k7_all_path_operation_boundary_blocker.v1",
            "schema_version": SCHEMA_VERSION,
            "family": self.family.value,
            "site_key": self.site_key,
            "code": self.code.value,
            "module_name": self.module_name,
            "symbol_qualname": self.symbol_qualname,
            "detail": self.detail,
        }

    def to_document(self) -> dict[str, str]:
        return {**self._payload(), "blocker_id": self.blocker_id}


@dataclass(frozen=True, slots=True)
class _SiteSpecV1:
    site_key: str
    family: BoundaryFamilyV1
    module_name: str
    relative_path: str
    symbol_qualname: str
    call_target: str
    call_index: int
    call_count: int
    call_lineno: int
    call_col_offset: int
    call_end_lineno: int
    call_end_col_offset: int
    source_byte_count: int
    source_sha256: str
    symbol_ast_sha256: str
    call_ast_sha256: str
    stage_kind: registry_v6.ConstructionStageKindV6
    route_kinds: tuple[RouteKindEnum, ...]
    accounting_families: tuple[profile_v1.AccountingFamilyV1, ...]
    evidence_roles: tuple[str, ...]


# These values bind the exact source tree on which Contract 2.0.36 was
# designed.  They are constants rather than import-time observations: a later
# source edit therefore blocks replay instead of silently redefining the site.
_SITE_SPECS_V1: tuple[_SiteSpecV1, ...] = (
    _SiteSpecV1(
        "preopen.prepared-authority-validation",
        BoundaryFamilyV1.PREOPEN_COMMON,
        "acfqp.phase3e_runner_v1",
        "phase3e_runner_v1.py",
        "run_phase3e",
        "prepared.validate",
        0,
        1,
        2617,
        20,
        2617,
        56,
        137439,
        "ca8b4314d6172223c6d59f0b5d6f4f08728c9df4ba99ce89cbc4c7a33d007b13",
        "a03444c7ec503eba2a61e46bc027ea24e35d6281389486a307fc8b56c73a0ad5",
        "04c774cd06101f22314f63c5f6fddf5acb4cf746a4a6f0949e697bae26ab1026",
        registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX,
        tuple(RouteKindEnum),
        (
            profile_v1.AccountingFamilyV1.COMMON_OWNER,
            profile_v1.AccountingFamilyV1.SHARED_RESOURCE,
            profile_v1.AccountingFamilyV1.DERIVED_RECONCILIATION,
        ),
        ("COUNTER_RECORD_SET", "SHARED_RESOURCE_RECEIPT_SET"),
    ),
    _SiteSpecV1(
        "preopen.decision-freeze-dispatch",
        BoundaryFamilyV1.PREOPEN_COMMON,
        "acfqp.phase3e_runner_v1",
        "phase3e_runner_v1.py",
        "run_phase3e",
        "decide_then_execute",
        0,
        1,
        2751,
        20,
        2756,
        9,
        137439,
        "ca8b4314d6172223c6d59f0b5d6f4f08728c9df4ba99ce89cbc4c7a33d007b13",
        "a03444c7ec503eba2a61e46bc027ea24e35d6281389486a307fc8b56c73a0ad5",
        "4a772af8bf35228610aca5b0fb4900ff11ffaa3abf6a7e37d0abf88ffc2da5e9",
        registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX,
        tuple(RouteKindEnum),
        (
            profile_v1.AccountingFamilyV1.COMMON_OWNER,
            profile_v1.AccountingFamilyV1.SHARED_RESOURCE,
            profile_v1.AccountingFamilyV1.DERIVED_RECONCILIATION,
        ),
        ("ROUTE_DECISION", "ROUTE_UPPER"),
    ),
    _SiteSpecV1(
        "abstract.contingent-plan-selection",
        BoundaryFamilyV1.ABSTRACT,
        "acfqp.phase3e_model_only_v1",
        "phase3e_model_only_v1.py",
        "run_phase3e_model_only_from_source_v1",
        "select_contingent_plan_v1",
        0,
        1,
        668,
        20,
        670,
        5,
        27460,
        "00af2fd30f9666afe31d2af80846288ca7daadab622183493a2170bf36d81084",
        "88bb055ce47de399bdff9d0c2c2e920da0c4317ba54be1d689c7d4f1a56f84c8",
        "c9bf8e2018fdb85d44b48a8b354f3219adef3bd1c33dd6ee949911b55a9a66c4",
        registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX,
        (
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        ),
        (profile_v1.AccountingFamilyV1.COMMON_OWNER,),
        ("ABSTRACT_AUDIT",),
    ),
    _SiteSpecV1(
        "abstract.portable-sound-audit",
        BoundaryFamilyV1.ABSTRACT,
        "acfqp.phase3e_model_only_v1",
        "phase3e_model_only_v1.py",
        "run_phase3e_model_only_from_source_v1",
        "build_portable_sound_audit_v1",
        0,
        1,
        672,
        23,
        678,
        9,
        27460,
        "00af2fd30f9666afe31d2af80846288ca7daadab622183493a2170bf36d81084",
        "88bb055ce47de399bdff9d0c2c2e920da0c4317ba54be1d689c7d4f1a56f84c8",
        "605247e6b3039ef3a85c44f7657f6cd9834aba9ae8d4179ee415dd060c763ef0",
        registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX,
        (
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        ),
        (profile_v1.AccountingFamilyV1.COMMON_OWNER,),
        ("ABSTRACT_AUDIT",),
    ),
    _SiteSpecV1(
        "local.slice-materialization",
        BoundaryFamilyV1.LOCAL,
        "acfqp.phase3e_local_adapter_v1",
        "phase3e_local_adapter_v1.py",
        "AuthorizedSafeChainLocalExecutorV1._execute",
        "_execute_safe_chain_local_preparation",
        0,
        1,
        551,
        28,
        551,
        86,
        43389,
        "87c735bec2c22e559c818051cbabf0fd2ecb2f24b4e2b886bf988843433c15be",
        "36dab82652fda15dc05b43af1629677aa04f165694772dc5631915bcf221874f",
        "8fe191ed8a3f92543cc3513e0ebea685ef8062a71f6a14a4a2e303db40cf168d",
        registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT,
        (RouteKindEnum.LOCAL_ATTEMPT,),
        (profile_v1.AccountingFamilyV1.LOCAL_OWNER,),
        ("LOCAL_SOLVER_RESULT", "POST_AUDIT"),
    ),
    _SiteSpecV1(
        "local.isolated-worker-launch",
        BoundaryFamilyV1.LOCAL,
        "acfqp.phase3e_local_adapter_v1",
        "phase3e_local_adapter_v1.py",
        "AuthorizedSafeChainLocalExecutorV1._execute",
        "_run_fresh_general_solver",
        0,
        1,
        613,
        45,
        619,
        9,
        43389,
        "87c735bec2c22e559c818051cbabf0fd2ecb2f24b4e2b886bf988843433c15be",
        "36dab82652fda15dc05b43af1629677aa04f165694772dc5631915bcf221874f",
        "0f3141a3ff692fee3b956a13538356e8a560b0e8da2f61e1e4dd6b90724c6899",
        registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT,
        (RouteKindEnum.LOCAL_ATTEMPT,),
        (profile_v1.AccountingFamilyV1.LOCAL_OWNER,),
        ("LOCAL_SOLVER_RESULT",),
    ),
    _SiteSpecV1(
        "fallback.authorized-ground-search",
        BoundaryFamilyV1.FALLBACK,
        "acfqp.phase3e_fallback_v1",
        "phase3e_fallback_v1.py",
        "execute_authorized_ground_fallback_v1",
        "run_ground_fallback_search_v1",
        0,
        1,
        2536,
        16,
        2547,
        5,
        104003,
        "2dfc116a5f7997ef505ba72eb1bd97234cc8bd25dd7b2f086812f68f792c1afe",
        "a3d635b8e9664d3221bfdf006c66dc4eb883507f60016317dc75d5ab5d56d943",
        "fc467ea528cb56bfc1d9d47214183612ebf39902d8cff6000579c806103364fd",
        registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
        (RouteKindEnum.DIRECT_FALLBACK,),
        (profile_v1.AccountingFamilyV1.FALLBACK_OWNER,),
        ("GROUND_FALLBACK", "ROUTE_DECISION"),
    ),
    _SiteSpecV1(
        "rebuild.registered-rebuild-callback",
        BoundaryFamilyV1.REBUILD,
        "acfqp.phase3e_rebuild_runner_v1",
        "phase3e_rebuild_runner_v1.py",
        "run_bounded_rebuild_retry_v1",
        "rebuild_callback.callback",
        0,
        1,
        659,
        19,
        659,
        56,
        29064,
        "483c861b6838731fdaa04162d5c1a96be3ebadf11ef6902502208cff578774c0",
        "7fdf349e42878d92de89c69427d94adf1bc5a80e4f159e6dc892d0c35f9ae669",
        "49d5feb18fcece1217afd5f500d6c71541fe1a5c3a696c45563d8c8ba0a97780",
        registry_v6.ConstructionStageKindV6.REBUILD,
        (RouteKindEnum.REBUILD,),
        (profile_v1.AccountingFamilyV1.REBUILD_OWNER,),
        ("COUNTER_RECORD_SET", "WORK_VECTOR"),
    ),
    _SiteSpecV1(
        "rebuild.single-retry-callback",
        BoundaryFamilyV1.REBUILD,
        "acfqp.phase3e_rebuild_runner_v1",
        "phase3e_rebuild_runner_v1.py",
        "run_bounded_rebuild_retry_v1",
        "retry_callback",
        0,
        1,
        692,
        25,
        692,
        47,
        29064,
        "483c861b6838731fdaa04162d5c1a96be3ebadf11ef6902502208cff578774c0",
        "7fdf349e42878d92de89c69427d94adf1bc5a80e4f159e6dc892d0c35f9ae669",
        "1fb43f6c782ec01039250f9c5d57ae9a2f60cde03dfca767da8f04b8a15c8e75",
        registry_v6.ConstructionStageKindV6.REBUILD,
        (RouteKindEnum.REBUILD,),
        (profile_v1.AccountingFamilyV1.REBUILD_OWNER,),
        ("OCCURRENCE_TERMINAL",),
    ),
    _SiteSpecV1(
        "verification.terminal-semantic-attestation-replay",
        BoundaryFamilyV1.VERIFICATION_TERMINAL,
        "acfqp.semantic_verification_v1",
        "semantic_verification_v1.py",
        "verify_terminal_classification_semantics_v1",
        "verify_typed_attestation_v1",
        0,
        1,
        4265,
        12,
        4269,
        13,
        185445,
        "fbec2336f823d96547718d13f89e0882856bcc17ab129cef045249fdbb97e154",
        "92a38123a2b7573a6569ba5dcaa66386db9e4dc7e89b96082a3448c2175a21e5",
        "57bd062d9a4d806bc9018e09251cb8ac63d0e8890b4c43e96a5f732c976745f4",
        registry_v6.ConstructionStageKindV6.CLOSED_RECONCILIATION_AND_TERMINALIZATION,
        tuple(RouteKindEnum),
        (
            profile_v1.AccountingFamilyV1.SHARED_RESOURCE,
            profile_v1.AccountingFamilyV1.DERIVED_RECONCILIATION,
        ),
        (
            "ACTUAL_PROJECTION",
            "DERIVED_RECONCILIATION",
            "OCCURRENCE_TERMINAL",
            "TERMINAL_CLASSIFICATION",
        ),
    ),
)


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


def _terminal_codes_for_site(
    spec: _SiteSpecV1,
    profile: profile_v1.ConstructionK7AllPathAccountingProfileV1,
) -> tuple[TerminalCode, ...]:
    result: list[TerminalCode] = []
    for code in TerminalCode:
        rule = profile.terminal_path_rule_by_code[code]
        stages = {row.stage_kind: row.disposition for row in rule.stage_plan}
        if (
            any(route in rule.route_kinds_permitted_in_attempt for route in spec.route_kinds)
            and stages[spec.stage_kind] is not profile_v1.StageDispositionV1.FORBIDDEN
        ):
            result.append(code)
    if not result:
        _fail(f"site {spec.site_key} has no profile-authorized terminal context")
    return tuple(result)


@dataclass(frozen=True, slots=True)
class OperationBoundarySiteV1:
    _issuer: object = field(repr=False, compare=False)
    site_key: str = ""
    family: BoundaryFamilyV1 = BoundaryFamilyV1.PREOPEN_COMMON
    module_name: str = ""
    relative_path: str = ""
    source_byte_count: int = 0
    source_sha256: str = ""
    symbol_qualname: str = ""
    symbol_ast_sha256: str = ""
    call_target: str = ""
    call_index: int = 0
    call_count: int = 0
    call_lineno: int = 0
    call_col_offset: int = 0
    call_end_lineno: int = 0
    call_end_col_offset: int = 0
    call_ast_sha256: str = ""
    stage_kind: registry_v6.ConstructionStageKindV6 = (
        registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX
    )
    route_kinds: tuple[RouteKindEnum, ...] = ()
    terminal_codes: tuple[TerminalCode, ...] = ()
    accounting_families: tuple[profile_v1.AccountingFamilyV1, ...] = ()
    evidence_roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("operation-boundary site is caller-minted")
        try:
            object.__setattr__(self, "family", BoundaryFamilyV1(self.family))
            object.__setattr__(
                self, "stage_kind", registry_v6.ConstructionStageKindV6(self.stage_kind)
            )
            object.__setattr__(
                self,
                "route_kinds",
                tuple(RouteKindEnum(item) for item in self.route_kinds),
            )
            object.__setattr__(
                self,
                "terminal_codes",
                tuple(TerminalCode(item) for item in self.terminal_codes),
            )
            object.__setattr__(
                self,
                "accounting_families",
                tuple(profile_v1.AccountingFamilyV1(item) for item in self.accounting_families),
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7AllPathOperationBoundaryManifestV1Error(
                "operation-boundary site taxonomy is invalid"
            ) from error
        for name in ("source_sha256", "symbol_ast_sha256", "call_ast_sha256"):
            try:
                parse_content_id(getattr(self, name))
            except (TypeError, ValueError) as error:
                raise ConstructionK7AllPathOperationBoundaryManifestV1Error(
                    f"{name} is not one exact SHA-256 digest"
                ) from error
        if (
            not self.site_key
            or not self.module_name.startswith("acfqp.")
            or not self.relative_path.endswith(".py")
            or not self.symbol_qualname
            or not self.call_target
            or self.source_byte_count <= 0
            or self.call_index < 0
            or self.call_count <= self.call_index
            or min(
                self.call_lineno,
                self.call_col_offset + 1,
                self.call_end_lineno,
                self.call_end_col_offset + 1,
            )
            <= 0
            or not self.route_kinds
            or not self.terminal_codes
            or not self.accounting_families
            or not self.evidence_roles
            or len(set(self.evidence_roles)) != len(self.evidence_roles)
        ):
            _fail("operation-boundary site is incomplete")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_all_path_operation_boundary_site.v1",
            "schema_version": SCHEMA_VERSION,
            "site_key": self.site_key,
            "family": self.family.value,
            "module_name": self.module_name,
            "relative_path": self.relative_path,
            "source_byte_count": self.source_byte_count,
            "source_sha256": self.source_sha256,
            "symbol_qualname": self.symbol_qualname,
            "symbol_ast_sha256": self.symbol_ast_sha256,
            "call_target": self.call_target,
            "call_index": self.call_index,
            "call_count": self.call_count,
            "call_lineno": self.call_lineno,
            "call_col_offset": self.call_col_offset,
            "call_end_lineno": self.call_end_lineno,
            "call_end_col_offset": self.call_end_col_offset,
            "call_ast_sha256": self.call_ast_sha256,
            "stage_kind": self.stage_kind.value,
            "route_kinds": [item.value for item in self.route_kinds],
            "terminal_codes": [item.value for item in self.terminal_codes],
            "accounting_families": [item.value for item in self.accounting_families],
            "evidence_roles": list(self.evidence_roles),
            "execution_performed": False,
            "accounting_event_emitted": False,
        }

    @property
    def site_id(self) -> str:
        return _content_id(SITE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "site_id": self.site_id}


@dataclass(frozen=True, slots=True)
class ConstructionK7AllPathOperationBoundaryManifestV1:
    _issuer: object = field(repr=False, compare=False)
    all_path_accounting_profile_id: str = ""
    source_archive_id: str = ""
    source_members: tuple[tuple[str, str, int], ...] = ()
    sites: tuple[OperationBoundarySiteV1, ...] = ()

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("operation-boundary manifest is caller-minted")
        for value in (self.all_path_accounting_profile_id, self.source_archive_id):
            try:
                parse_content_id(value)
            except (TypeError, ValueError) as error:
                raise ConstructionK7AllPathOperationBoundaryManifestV1Error(
                    "operation-boundary manifest identity is invalid"
                ) from error
        if (
            len(self.source_members) != EXPECTED_SOURCE_MEMBER_COUNT
            or tuple(sorted(self.source_members)) != self.source_members
            or len({row[0] for row in self.source_members}) != len(self.source_members)
            or len(self.sites) != EXPECTED_SITE_COUNT
            or tuple(sorted(self.sites, key=lambda row: row.site_key)) != self.sites
            or len({row.site_key for row in self.sites}) != len(self.sites)
            or {row.family for row in self.sites} != set(BoundaryFamilyV1)
        ):
            _fail("operation-boundary manifest coverage is incomplete")

    @property
    def by_key(self) -> Mapping[str, OperationBoundarySiteV1]:
        return MappingProxyType({row.site_key: row for row in self.sites})

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_all_path_operation_boundary_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "all_path_accounting_profile_id": self.all_path_accounting_profile_id,
            "source_archive_id": self.source_archive_id,
            "source_members": [
                {
                    "module_name": module,
                    "source_sha256": digest,
                    "source_byte_count": byte_count,
                }
                for module, digest, byte_count in self.source_members
            ],
            "sites": [row.to_document() for row in self.sites],
            "boundary_family_count": EXPECTED_BOUNDARY_FAMILY_COUNT,
            "site_count": EXPECTED_SITE_COUNT,
            "source_member_count": EXPECTED_SOURCE_MEMBER_COUNT,
            "catalogue_only": True,
            "source_archive_replay_required": True,
            "all_required_boundary_families_present": True,
            "execution_performed": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "all_path_native_accounting_complete": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "central_domain_registration_pending": False,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id(MANIFEST_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operation_boundary_manifest_id": self.manifest_id}


@dataclass(frozen=True, slots=True)
class OperationBoundaryReplayV1:
    outcome: BoundaryReplayOutcomeV1
    profile_id: str
    source_archive_id: str | None
    manifest: ConstructionK7AllPathOperationBoundaryManifestV1 | None
    blockers: tuple[BoundaryBlockerV1, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "outcome", BoundaryReplayOutcomeV1(self.outcome))
            parse_content_id(self.profile_id)
            if self.source_archive_id is not None:
                parse_content_id(self.source_archive_id)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AllPathOperationBoundaryManifestV1Error(
                "operation-boundary replay identity is invalid"
            ) from error
        if (
            (self.outcome is BoundaryReplayOutcomeV1.VERIFIED)
            != (self.manifest is not None and not self.blockers)
            or (self.outcome is BoundaryReplayOutcomeV1.BLOCKED)
            != (self.manifest is None and bool(self.blockers))
            or tuple(sorted(self.blockers)) != self.blockers
        ):
            _fail("operation-boundary replay outcome is inconsistent")

    @property
    def replay_id(self) -> str:
        return _content_id(
            REPLAY_DOMAIN,
            {
                "schema": "acfqp.construction_k7_all_path_operation_boundary_replay.v1",
                "schema_version": SCHEMA_VERSION,
                "outcome": self.outcome.value,
                "profile_id": self.profile_id,
                "source_archive_id": self.source_archive_id,
                "manifest_id": None if self.manifest is None else self.manifest.manifest_id,
                "blocker_ids": [row.blocker_id for row in self.blockers],
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_all_path_operation_boundary_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "outcome": self.outcome.value,
            "profile_id": self.profile_id,
            "source_archive_id": self.source_archive_id,
            "manifest_id": None if self.manifest is None else self.manifest.manifest_id,
            "blockers": [row.to_document() for row in self.blockers],
            "execution_performed": False,
            "accounting_claim_created": False,
            "replay_id": self.replay_id,
        }


def load_official_operation_boundary_source_archive_v1() -> dict[str, bytes]:
    """Read the six frozen modules without importing or executing them."""

    root = Path(__file__).resolve().parent
    modules = {spec.module_name: spec.relative_path for spec in _SITE_SPECS_V1}
    return {module: (root / path).read_bytes() for module, path in sorted(modules.items())}


def _source_archive_identity(
    source_archive: Mapping[str, bytes],
) -> tuple[str, tuple[tuple[str, str, int], ...]]:
    rows = tuple(
        sorted(
            (module, _sha256(raw), len(raw))
            for module, raw in source_archive.items()
            if type(module) is str and type(raw) is bytes
        )
    )
    payload = {
        "schema": "acfqp.construction_k7_all_path_operation_boundary_source_archive.v1",
        "schema_version": SCHEMA_VERSION,
        "members": [
            {"module_name": module, "source_sha256": digest, "source_byte_count": size}
            for module, digest, size in rows
        ],
    }
    return _content_id(SOURCE_ARCHIVE_DOMAIN, payload), rows


def replay_operation_boundary_source_archive_v1(
    source_archive: Mapping[str, bytes],
    *,
    profile: profile_v1.ConstructionK7AllPathAccountingProfileV1 | None = None,
) -> OperationBoundaryReplayV1:
    """Replay all exact source/AST/call-site identities, returning blockers."""

    expected_profile = profile_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    supplied_profile = expected_profile if profile is None else profile
    if type(supplied_profile) is not profile_v1.ConstructionK7AllPathAccountingProfileV1:
        _fail("operation-boundary replay requires the exact all-path profile type")
    if supplied_profile.profile_id != expected_profile.profile_id:
        blocker = BoundaryBlockerV1(
            BoundaryFamilyV1.PREOPEN_COMMON,
            "profile.identity",
            BoundaryBlockerCodeV1.PROFILE_ID_CHANGED,
            "acfqp.construction_k7_all_path_accounting_profile_v1",
            "freeze_construction_k7_all_path_accounting_profile_v1",
            "supplied all-path profile identity differs from Contract 2.0.33",
        )
        return OperationBoundaryReplayV1(
            BoundaryReplayOutcomeV1.BLOCKED,
            expected_profile.profile_id,
            None,
            None,
            (blocker,),
        )
    if not isinstance(source_archive, Mapping):
        _fail("source archive must be one module-to-bytes mapping")

    archive_id, source_members = _source_archive_identity(source_archive)
    blockers: list[BoundaryBlockerV1] = []
    parsed: dict[str, ast.Module] = {}
    symbols: dict[str, dict[str, tuple[ast.AST, ...]]] = {}

    def block(spec: _SiteSpecV1, code: BoundaryBlockerCodeV1, detail: str) -> None:
        blockers.append(
            BoundaryBlockerV1(
                spec.family,
                spec.site_key,
                code,
                spec.module_name,
                spec.symbol_qualname,
                detail,
            )
        )

    expected_modules = {spec.module_name for spec in _SITE_SPECS_V1}
    supplied_modules = {
        key for key in source_archive if type(key) is str
    }
    if supplied_modules != expected_modules:
        representative = _SITE_SPECS_V1[0]
        block(
            representative,
            BoundaryBlockerCodeV1.SOURCE_MEMBER_SET_CHANGED,
            "archive module key set differs from the six frozen source members",
        )

    sites: list[OperationBoundarySiteV1] = []
    for spec in _SITE_SPECS_V1:
        raw = source_archive.get(spec.module_name)
        if raw is None:
            block(spec, BoundaryBlockerCodeV1.SOURCE_MEMBER_MISSING, "module absent from archive")
            continue
        if type(raw) is not bytes:
            block(spec, BoundaryBlockerCodeV1.SOURCE_MEMBER_NOT_BYTES, "archive member is not exact bytes")
            continue
        if len(raw) != spec.source_byte_count or _sha256(raw) != spec.source_sha256:
            block(
                spec,
                BoundaryBlockerCodeV1.SOURCE_BYTES_CHANGED,
                "complete module bytes differ from the frozen byte count or SHA-256",
            )
            continue
        if spec.module_name not in parsed:
            try:
                parsed[spec.module_name] = ast.parse(raw, filename=spec.relative_path)
            except (SyntaxError, ValueError, TypeError):
                block(spec, BoundaryBlockerCodeV1.SOURCE_SYNTAX_INVALID, "module does not parse as Python AST")
                continue
            symbols[spec.module_name] = _qualified_symbols(parsed[spec.module_name])
        matches = symbols[spec.module_name].get(spec.symbol_qualname, ())
        if not matches:
            block(spec, BoundaryBlockerCodeV1.AST_SYMBOL_MISSING, "qualified AST symbol is absent")
            continue
        if len(matches) != 1:
            block(spec, BoundaryBlockerCodeV1.AST_SYMBOL_AMBIGUOUS, "qualified AST symbol is ambiguous")
            continue
        symbol = matches[0]
        if _sha256(ast.dump(symbol, include_attributes=False).encode("utf-8")) != spec.symbol_ast_sha256:
            block(spec, BoundaryBlockerCodeV1.SYMBOL_AST_CHANGED, "enclosing symbol AST changed")
            continue
        calls = tuple(
            sorted(
                (
                    node
                    for node in ast.walk(symbol)
                    if isinstance(node, ast.Call) and _call_name(node.func) == spec.call_target
                ),
                key=lambda node: (
                    node.lineno,
                    node.col_offset,
                    node.end_lineno or -1,
                    node.end_col_offset or -1,
                ),
            )
        )
        if not calls:
            block(spec, BoundaryBlockerCodeV1.CALL_SITE_MISSING, "selected call target is absent")
            continue
        if len(calls) != spec.call_count:
            block(spec, BoundaryBlockerCodeV1.CALL_SITE_CARDINALITY_CHANGED, "selected call target cardinality changed")
            continue
        call = calls[spec.call_index]
        location = (call.lineno, call.col_offset, call.end_lineno, call.end_col_offset)
        if location != (
            spec.call_lineno,
            spec.call_col_offset,
            spec.call_end_lineno,
            spec.call_end_col_offset,
        ):
            block(spec, BoundaryBlockerCodeV1.CALL_SITE_LOCATION_CHANGED, "selected call location changed")
            continue
        if _sha256(ast.dump(call, include_attributes=False).encode("utf-8")) != spec.call_ast_sha256:
            block(spec, BoundaryBlockerCodeV1.CALL_SITE_AST_CHANGED, "selected call expression AST changed")
            continue
        sites.append(
            OperationBoundarySiteV1(
                _ISSUER,
                spec.site_key,
                spec.family,
                spec.module_name,
                spec.relative_path,
                spec.source_byte_count,
                spec.source_sha256,
                spec.symbol_qualname,
                spec.symbol_ast_sha256,
                spec.call_target,
                spec.call_index,
                spec.call_count,
                spec.call_lineno,
                spec.call_col_offset,
                spec.call_end_lineno,
                spec.call_end_col_offset,
                spec.call_ast_sha256,
                spec.stage_kind,
                spec.route_kinds,
                _terminal_codes_for_site(spec, expected_profile),
                spec.accounting_families,
                spec.evidence_roles,
            )
        )

    if blockers:
        return OperationBoundaryReplayV1(
            BoundaryReplayOutcomeV1.BLOCKED,
            expected_profile.profile_id,
            archive_id,
            None,
            tuple(sorted(set(blockers))),
        )
    manifest = ConstructionK7AllPathOperationBoundaryManifestV1(
        _ISSUER,
        expected_profile.profile_id,
        archive_id,
        source_members,
        tuple(sorted(sites, key=lambda row: row.site_key)),
    )
    return OperationBoundaryReplayV1(
        BoundaryReplayOutcomeV1.VERIFIED,
        expected_profile.profile_id,
        archive_id,
        manifest,
        (),
    )


def freeze_construction_k7_all_path_operation_boundary_manifest_v1(
    *,
    source_archive: Mapping[str, bytes] | None = None,
    profile: profile_v1.ConstructionK7AllPathAccountingProfileV1 | None = None,
) -> ConstructionK7AllPathOperationBoundaryManifestV1:
    """Freeze the catalogue only when every exact source site replays."""

    replay = replay_operation_boundary_source_archive_v1(
        load_official_operation_boundary_source_archive_v1()
        if source_archive is None
        else source_archive,
        profile=profile,
    )
    if replay.outcome is not BoundaryReplayOutcomeV1.VERIFIED:
        error = ConstructionK7AllPathOperationBoundaryManifestV1Error(
            "operation-boundary source replay is blocked"
        )
        error.blockers = replay.blockers  # type: ignore[attr-defined]
        raise error
    assert replay.manifest is not None
    return replay.manifest


def verify_construction_k7_all_path_operation_boundary_manifest_document_v1(
    document: Mapping[str, Any],
    source_archive: Mapping[str, bytes],
) -> OperationBoundaryReplayV1:
    """Independently reconstruct the manifest and compare canonical bytes."""

    replay = replay_operation_boundary_source_archive_v1(source_archive)
    if replay.outcome is BoundaryReplayOutcomeV1.BLOCKED:
        return replay
    assert replay.manifest is not None
    if type(document) is not dict or canonical_json_bytes(document) != canonical_json_bytes(
        replay.manifest.to_document()
    ):
        blocker = BoundaryBlockerV1(
            BoundaryFamilyV1.VERIFICATION_TERMINAL,
            "manifest.document",
            BoundaryBlockerCodeV1.MANIFEST_DOCUMENT_CHANGED,
            "acfqp.construction_k7_all_path_operation_boundary_manifest_v1",
            "ConstructionK7AllPathOperationBoundaryManifestV1.to_document",
            "supplied manifest document differs from independent source replay",
        )
        return OperationBoundaryReplayV1(
            BoundaryReplayOutcomeV1.BLOCKED,
            replay.profile_id,
            replay.source_archive_id,
            None,
            (blocker,),
        )
    return replay


__all__ = [
    "BoundaryBlockerCodeV1",
    "BoundaryBlockerV1",
    "BoundaryFamilyV1",
    "BoundaryReplayOutcomeV1",
    "ConstructionK7AllPathOperationBoundaryManifestV1",
    "ConstructionK7AllPathOperationBoundaryManifestV1Error",
    "OperationBoundaryReplayV1",
    "OperationBoundarySiteV1",
    "freeze_construction_k7_all_path_operation_boundary_manifest_v1",
    "load_official_operation_boundary_source_archive_v1",
    "replay_operation_boundary_source_archive_v1",
    "verify_construction_k7_all_path_operation_boundary_manifest_document_v1",
]
