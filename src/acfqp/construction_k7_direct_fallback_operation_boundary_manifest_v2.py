"""Exact seven-site manifest for an additive DIRECT_FALLBACK V2 segment.

The manifest binds seven V6 operational paths to literal unit-emission sites
in the future/test owner source provided by
``construction_accounting_route_segment_v2``.  It is parented by the exact
Contract-2.0.36 ``fallback.authorized-ground-search`` catalogue site, but it
does not claim that the production fallback solver has adopted these sites.

All content domains in this construction slice are local.  Central domain
registration and production closure are intentionally deferred.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as parent_v1
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.44"
PROFILE_KEY = "construction_k7_direct_fallback_operation_boundary_manifest_v2"
EXPECTED_BOUNDARY_COUNT = 7
EXPECTED_SOURCE_MEMBER_COUNT = 1
PARENT_SITE_KEY = "fallback.authorized-ground-search"
EXPECTED_PARENT_MANIFEST_ID = (
    "5a4ce864c2ef29f27cbf2ecb73ce3a43ac6ef4c19c0ce52706d27f628af477ed"
)
EXPECTED_PARENT_FALLBACK_SITE_ID = (
    "9dfd41a1140110df489073b682b443c05b5d73fd42f68b434d51ef4697af2ff3"
)
EXPECTED_PARENT_MANIFEST_DOCUMENT_SHA256 = (
    "72eb56f8cf6ad7412b53172c45fe8d5e05ee2a3906a8a7981f579d1273f15622"
)
EXPECTED_PARENT_FALLBACK_SITE_DOCUMENT_SHA256 = (
    "a0cf6fb05b16e96cda7a7dad1132b8434756726c6810f9af9fd21b43a6d651a1"
)
SOURCE_MODULE = "acfqp.construction_accounting_route_segment_v2"
SOURCE_RELATIVE_PATH = "construction_accounting_route_segment_v2.py"
HOOK_SYMBOL = "emit_route_segment_operation_v2"

CENTRAL_DOMAIN_REGISTRATION_PENDING = True
PRODUCTION_SOURCE_INTEGRATED = False
PRODUCTION_CLOSURE_CLAIMED = False

_BOUNDARY_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-boundary:v2"
)
_MANIFEST_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-boundary-manifest:v2"
)
_SOURCE_ARCHIVE_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-source-archive:v2"
)
_BLOCKER_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-blocker:v2"
)
_REPLAY_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-replay:v2"
)


class ConstructionK7DirectFallbackOperationBoundaryManifestV2Error(ValueError):
    """The seven-site source archive or manifest changed."""


class DirectFallbackBoundaryReplayOutcomeV2(str, Enum):
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"


class DirectFallbackBoundaryBlockerCodeV2(str, Enum):
    SOURCE_MEMBER_SET_CHANGED = "SOURCE_MEMBER_SET_CHANGED"
    SOURCE_MEMBER_MISSING = "SOURCE_MEMBER_MISSING"
    SOURCE_MEMBER_NOT_BYTES = "SOURCE_MEMBER_NOT_BYTES"
    SOURCE_SYNTAX_INVALID = "SOURCE_SYNTAX_INVALID"
    HOOK_NON_LITERAL = "HOOK_NON_LITERAL"
    HOOK_MISSING = "HOOK_MISSING"
    HOOK_EXTRA = "HOOK_EXTRA"
    SOURCE_BYTES_CHANGED = "SOURCE_BYTES_CHANGED"
    SYMBOL_MISSING = "SYMBOL_MISSING"
    SYMBOL_AMBIGUOUS = "SYMBOL_AMBIGUOUS"
    SYMBOL_AST_CHANGED = "SYMBOL_AST_CHANGED"
    CALL_LOCATION_CHANGED = "CALL_LOCATION_CHANGED"
    CALL_AST_CHANGED = "CALL_AST_CHANGED"
    REGISTRY_BINDING_CHANGED = "REGISTRY_BINDING_CHANGED"
    PARENT_MANIFEST_CHANGED = "PARENT_MANIFEST_CHANGED"
    MANIFEST_DOCUMENT_CHANGED = "MANIFEST_DOCUMENT_CHANGED"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DirectFallbackOperationBoundaryManifestV2Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackOperationBoundaryManifestV2Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True, order=True)
class DirectFallbackBoundaryBlockerV2:
    code: DirectFallbackBoundaryBlockerCodeV2
    site_key: str
    detail: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self, "code", DirectFallbackBoundaryBlockerCodeV2(self.code)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackOperationBoundaryManifestV2Error(
                "direct-fallback blocker code is invalid"
            ) from error
        if not all(
            type(value) is str and value for value in (self.site_key, self.detail)
        ):
            _fail("direct-fallback blocker text is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_boundary_blocker.v2",
            "schema_version": SCHEMA_VERSION,
            "code": self.code.value,
            "site_key": self.site_key,
            "detail": self.detail,
            "central_domain_registration_pending": True,
        }

    @property
    def blocker_id(self) -> str:
        return _content_id(_BLOCKER_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "blocker_id": self.blocker_id}


@dataclass(frozen=True, slots=True)
class _BoundarySpecV2:
    boundary_key: str
    dispatch_key: str
    target_path: str
    operation_source_symbol: str
    call_lineno: int
    call_col_offset: int
    call_end_lineno: int
    call_end_col_offset: int
    symbol_ast_sha256: str
    call_ast_sha256: str


_SOURCE_BYTE_COUNT = 45412
_SOURCE_SHA256 = "0ae2b6f4513f81263e56b2d5d8df14acf6d0d8b1191dc7529c7d3402a999ea56"

_SPECS: tuple[_BoundarySpecV2, ...] = (
    _BoundarySpecV2(
        "direct-fallback.action-evaluated",
        "direct-fallback.action.evaluated",
        "fallback.actions_evaluated",
        "DirectFallbackOwnedOperationSourceV2.action_evaluated_v2",
        1115,
        8,
        1115,
        78,
        "3553687646b1fb799134db686f4b0bceabcc2962b3c7ce1c1d680b5ac6a8fcab",
        "e7064147db0c5cf4ebefeeb62c17d8712d908aa90293c59f49f56a1fe9bb5621",
    ),
    _BoundarySpecV2(
        "direct-fallback.bellman-backup",
        "direct-fallback.bellman.backup",
        "fallback.bellman_backups",
        "DirectFallbackOwnedOperationSourceV2.bellman_backup_v2",
        1127,
        8,
        1127,
        76,
        "274ef3a44c05d3320ba0efc1dd31c1784bd6d255414f7d89698ddd876efc536e",
        "99bcca90e679490c01b78644351cacaf4a78e348a02a61a53eb917d6a45059c3",
    ),
    _BoundarySpecV2(
        "direct-fallback.cap-check",
        "direct-fallback.control.cap-check",
        "control.cap_checks",
        "DirectFallbackOwnedOperationSourceV2.cap_check_v2",
        1101,
        8,
        1101,
        79,
        "e2935a48f7ac3feb85028154414f7e94ca1f17eae0df24a6dd3d5fd8bef412d5",
        "69ecd5790818bf067257450f0ed4a4fdee5b2f45842b7fc45852c49188098c5c",
    ),
    _BoundarySpecV2(
        "direct-fallback.cap-rejection",
        "direct-fallback.control.cap-rejection",
        "control.cap_rejections",
        "DirectFallbackOwnedOperationSourceV2.cap_rejection_v2",
        1105,
        8,
        1107,
        9,
        "36c42afc2d3ebf96e5a404efea009e259f58603117cece9d1aa1819a4c7825ae",
        "963e65d2f5f982982cd1f46211276c2cd9e088b19f313d8822a5b8d3f93a09b3",
    ),
    _BoundarySpecV2(
        "direct-fallback.ground-step",
        "direct-fallback.kernel.transition",
        "fallback.ground_steps",
        "DirectFallbackOwnedOperationSourceV2.ground_step_v2",
        1119,
        8,
        1119,
        79,
        "643ba5b3a4c195548c28fb6270def1fa9232072659988c67c49af6f77f59b49e",
        "1b5511e02dc7317bc39ca00f15763e88ccdec9e37819d4b18166d205d1d22f41",
    ),
    _BoundarySpecV2(
        "direct-fallback.outcome-row",
        "direct-fallback.outcome.row",
        "fallback.outcome_rows",
        "DirectFallbackOwnedOperationSourceV2.outcome_row_v2",
        1123,
        8,
        1123,
        73,
        "ea5151f219bcb27442a81f2c5c05cd428b54acbb535aac4bac797877e04804ac",
        "2dd83549600cba07dd966ffc746e154ca3cd6337ef4ca33e14dbdb19e50e4c3c",
    ),
    _BoundarySpecV2(
        "direct-fallback.state-expanded",
        "direct-fallback.state.expanded",
        "fallback.states_expanded",
        "DirectFallbackOwnedOperationSourceV2.state_expanded_v2",
        1111,
        8,
        1111,
        76,
        "4702fa10357fa07fab2c70afc9b6932e9bcc92ef27db9aa7984f0e264104fa72",
        "d48e8eeebf4716edb1fe1e74a77a986c795418e99b342c60d2212668e6b3909f",
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


def _literal_hook_dispatch(call: ast.Call) -> str | None:
    if (
        len(call.args) != 2
        or call.keywords
        or not isinstance(call.args[0], ast.Constant)
        or type(call.args[0].value) is not str
        or not isinstance(call.args[1], ast.Constant)
        or type(call.args[1].value) is not int
        or call.args[1].value != 1
    ):
        return None
    return call.args[0].value


def _parent_manifest_and_site() -> tuple[Any, Any]:
    parent = parent_v1.freeze_construction_k7_all_path_operation_boundary_manifest_v1()
    site = parent.by_key.get(PARENT_SITE_KEY)
    if site is None:
        _fail("Contract-2.0.36 fallback parent site is absent")
    if (
        parent.manifest_id != EXPECTED_PARENT_MANIFEST_ID
        or site.site_id != EXPECTED_PARENT_FALLBACK_SITE_ID
        or _sha256(canonical_json_bytes(parent.to_document()))
        != EXPECTED_PARENT_MANIFEST_DOCUMENT_SHA256
        or _sha256(canonical_json_bytes(site.to_document()))
        != EXPECTED_PARENT_FALLBACK_SITE_DOCUMENT_SHA256
    ):
        _fail("Contract-2.0.36 parent identity or document changed")
    return parent, site


@dataclass(frozen=True, slots=True)
class DirectFallbackOperationBoundaryV2:
    _issuer: object = field(repr=False, compare=False)
    boundary_key: str = ""
    dispatch_key: str = ""
    stage_kind: registry_v6.ConstructionStageKindV6 = (
        registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    )
    target_path: str = ""
    registered_owner: str = ""
    reducer: ReducerEnum = ReducerEnum.SUM
    operation_source_module: str = SOURCE_MODULE
    operation_source_symbol: str = ""
    source_sha256: str = _SOURCE_SHA256
    source_byte_count: int = _SOURCE_BYTE_COUNT
    symbol_ast_sha256: str = ""
    call_ast_sha256: str = ""
    call_lineno: int = 0
    call_col_offset: int = 0
    call_end_lineno: int = 0
    call_end_col_offset: int = 0
    parent_site_id: str = ""

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("direct-fallback boundary is caller-minted")
        try:
            stage = registry_v6.ConstructionStageKindV6(self.stage_kind)
            reducer = ReducerEnum(self.reducer)
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackOperationBoundaryManifestV2Error(
                "direct-fallback boundary enum is invalid"
            ) from error
        object.__setattr__(self, "stage_kind", stage)
        object.__setattr__(self, "reducer", reducer)
        if (
            stage is not registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
            or reducer is not ReducerEnum.SUM
            or not all(
                type(value) is str and value
                for value in (
                    self.boundary_key,
                    self.dispatch_key,
                    self.target_path,
                    self.registered_owner,
                    self.operation_source_module,
                    self.operation_source_symbol,
                )
            )
            or self.operation_source_module != SOURCE_MODULE
            or self.source_sha256 != _SOURCE_SHA256
            or self.source_byte_count != _SOURCE_BYTE_COUNT
            or min(
                self.call_lineno,
                self.call_col_offset + 1,
                self.call_end_lineno,
                self.call_end_col_offset + 1,
            )
            <= 0
        ):
            _fail("direct-fallback boundary fields are incomplete")
        for value, label in (
            (self.source_sha256, "source SHA"),
            (self.symbol_ast_sha256, "symbol AST SHA"),
            (self.call_ast_sha256, "call AST SHA"),
            (self.parent_site_id, "parent site"),
        ):
            _cid(value, label)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_operation_boundary.v2",
            "schema_version": SCHEMA_VERSION,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "stage_kind": self.stage_kind.value,
            "target_path": self.target_path,
            "registered_owner": self.registered_owner,
            "reducer": self.reducer.value,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "symbol_ast_sha256": self.symbol_ast_sha256,
            "call_ast_sha256": self.call_ast_sha256,
            "call_location": {
                "lineno": self.call_lineno,
                "col_offset": self.call_col_offset,
                "end_lineno": self.call_end_lineno,
                "end_col_offset": self.call_end_col_offset,
            },
            "parent_contract_2_0_36_fallback_site_id": self.parent_site_id,
            "literal_dispatch_required": True,
            "unit_amount_required": True,
            "future_test_owner_source_only": True,
            "production_source_integrated": False,
            "runtime_evidence_issued": False,
            "central_domain_registration_pending": True,
            "production_closure_claimed": False,
        }

    @property
    def boundary_id(self) -> str:
        return _content_id(_BOUNDARY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "boundary_id": self.boundary_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class DirectFallbackOperationBoundaryManifestV2:
    _issuer: object = field(repr=False, compare=False)
    counter_registry_id: str = ""
    stage_profile_id: str = ""
    stage_kind: registry_v6.ConstructionStageKindV6 = (
        registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    )
    parent_manifest_id: str = ""
    parent_site_id: str = ""
    source_archive_id: str = ""
    boundaries: tuple[DirectFallbackOperationBoundaryV2, ...] = ()

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("direct-fallback manifest is caller-minted")
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.parent_manifest_id, "parent manifest"),
            (self.parent_site_id, "parent site"),
            (self.source_archive_id, "source archive"),
        ):
            _cid(value, label)
        object.__setattr__(self, "stage_kind", registry_v6.ConstructionStageKindV6(self.stage_kind))
        if (
            self.stage_kind is not registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
            or type(self.boundaries) is not tuple
            or len(self.boundaries) != EXPECTED_BOUNDARY_COUNT
            or tuple(sorted(self.boundaries, key=lambda row: row.boundary_key))
            != self.boundaries
            or len({row.boundary_key for row in self.boundaries})
            != EXPECTED_BOUNDARY_COUNT
            or len({row.dispatch_key for row in self.boundaries})
            != EXPECTED_BOUNDARY_COUNT
            or len({row.target_path for row in self.boundaries})
            != EXPECTED_BOUNDARY_COUNT
            or any(
                type(row) is not DirectFallbackOperationBoundaryV2
                or row.parent_site_id != self.parent_site_id
                for row in self.boundaries
            )
        ):
            _fail("direct-fallback manifest lacks its exact seven-site set")

    @property
    def by_dispatch(self) -> Mapping[str, DirectFallbackOperationBoundaryV2]:
        return MappingProxyType({row.dispatch_key: row for row in self.boundaries})

    @property
    def by_path(self) -> Mapping[str, DirectFallbackOperationBoundaryV2]:
        return MappingProxyType({row.target_path: row for row in self.boundaries})

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_operation_boundary_manifest.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "stage_kind": self.stage_kind.value,
            "parent_contract_2_0_36_manifest_id": self.parent_manifest_id,
            "parent_contract_2_0_36_fallback_site_id": self.parent_site_id,
            "parent_contract_2_0_36_manifest_document_sha256": (
                EXPECTED_PARENT_MANIFEST_DOCUMENT_SHA256
            ),
            "parent_contract_2_0_36_fallback_site_document_sha256": (
                EXPECTED_PARENT_FALLBACK_SITE_DOCUMENT_SHA256
            ),
            "source_archive_id": self.source_archive_id,
            "source_members": [
                {
                    "module_name": SOURCE_MODULE,
                    "relative_path": SOURCE_RELATIVE_PATH,
                    "source_sha256": _SOURCE_SHA256,
                    "source_byte_count": _SOURCE_BYTE_COUNT,
                }
            ],
            "boundaries": [row.to_document() for row in self.boundaries],
            "boundary_count": EXPECTED_BOUNDARY_COUNT,
            "source_member_count": EXPECTED_SOURCE_MEMBER_COUNT,
            "literal_dispatch_inventory_complete": True,
            "unit_amount_inventory_complete": True,
            "future_test_owner_source_only": True,
            "production_source_integrated": False,
            "runtime_evidence_issued": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "central_domain_registration_pending": True,
            "production_closure_claimed": False,
        }

    @property
    def boundary_manifest_id(self) -> str:
        return _content_id(_MANIFEST_DOMAIN, self._payload())

    @property
    def manifest_id(self) -> str:
        return self.boundary_manifest_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "boundary_manifest_id": self.boundary_manifest_id}

    def validate_official(self) -> None:
        expected = freeze_direct_fallback_operation_boundary_manifest_v2()
        if self.to_document() != expected.to_document():
            _fail("direct-fallback manifest differs from exact source replay")


@dataclass(frozen=True, slots=True)
class DirectFallbackBoundaryReplayV2:
    outcome: DirectFallbackBoundaryReplayOutcomeV2
    source_archive_id: str | None
    manifest: DirectFallbackOperationBoundaryManifestV2 | None
    blockers: tuple[DirectFallbackBoundaryBlockerV2, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self,
                "outcome",
                DirectFallbackBoundaryReplayOutcomeV2(self.outcome),
            )
            if self.source_archive_id is not None:
                _cid(self.source_archive_id, "source archive")
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackOperationBoundaryManifestV2Error(
                "direct-fallback replay identity is invalid"
            ) from error
        if (
            (self.outcome is DirectFallbackBoundaryReplayOutcomeV2.VERIFIED)
            != (self.manifest is not None and not self.blockers)
            or (self.outcome is DirectFallbackBoundaryReplayOutcomeV2.BLOCKED)
            != (self.manifest is None and bool(self.blockers))
            or tuple(sorted(set(self.blockers))) != self.blockers
        ):
            _fail("direct-fallback source replay outcome is inconsistent")

    @property
    def replay_id(self) -> str:
        return _content_id(
            _REPLAY_DOMAIN,
            {
                "schema": "acfqp.construction_k7_direct_fallback_boundary_replay.v2",
                "schema_version": SCHEMA_VERSION,
                "outcome": self.outcome.value,
                "source_archive_id": self.source_archive_id,
                "manifest_id": (
                    None if self.manifest is None else self.manifest.manifest_id
                ),
                "blocker_ids": [row.blocker_id for row in self.blockers],
                "production_closure_claimed": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_boundary_replay.v2",
            "schema_version": SCHEMA_VERSION,
            "outcome": self.outcome.value,
            "source_archive_id": self.source_archive_id,
            "manifest_id": None if self.manifest is None else self.manifest.manifest_id,
            "blockers": [row.to_document() for row in self.blockers],
            "execution_performed": False,
            "production_closure_claimed": False,
            "replay_id": self.replay_id,
        }


def load_direct_fallback_operation_source_archive_v2() -> dict[str, bytes]:
    root = Path(__file__).resolve().parent
    return {SOURCE_MODULE: (root / SOURCE_RELATIVE_PATH).read_bytes()}


def _archive_id(source_archive: Mapping[str, bytes]) -> str | None:
    if set(source_archive) != {SOURCE_MODULE}:
        return None
    raw = source_archive.get(SOURCE_MODULE)
    if type(raw) is not bytes:
        return None
    return _content_id(
        _SOURCE_ARCHIVE_DOMAIN,
        {
            "schema": "acfqp.construction_k7_direct_fallback_operation_source_archive.v2",
            "schema_version": SCHEMA_VERSION,
            "members": [
                {
                    "module_name": SOURCE_MODULE,
                    "source_sha256": _sha256(raw),
                    "source_byte_count": len(raw),
                }
            ],
            "central_domain_registration_pending": True,
        },
    )


def replay_direct_fallback_operation_source_archive_v2(
    source_archive: Mapping[str, bytes],
) -> DirectFallbackBoundaryReplayV2:
    if not isinstance(source_archive, Mapping):
        _fail("direct-fallback source archive must be one mapping")
    blockers: list[DirectFallbackBoundaryBlockerV2] = []

    def block(
        code: DirectFallbackBoundaryBlockerCodeV2,
        site_key: str,
        detail: str,
    ) -> None:
        blockers.append(DirectFallbackBoundaryBlockerV2(code, site_key, detail))

    supplied = set(source_archive)
    if supplied != {SOURCE_MODULE}:
        block(
            DirectFallbackBoundaryBlockerCodeV2.SOURCE_MEMBER_SET_CHANGED,
            "source.archive",
            "source archive must contain exactly the future/test owner module",
        )
    raw = source_archive.get(SOURCE_MODULE)
    if raw is None:
        block(
            DirectFallbackBoundaryBlockerCodeV2.SOURCE_MEMBER_MISSING,
            "source.module",
            "future/test owner module is absent",
        )
        return DirectFallbackBoundaryReplayV2(
            DirectFallbackBoundaryReplayOutcomeV2.BLOCKED,
            None,
            None,
            tuple(sorted(set(blockers))),
        )
    if type(raw) is not bytes:
        block(
            DirectFallbackBoundaryBlockerCodeV2.SOURCE_MEMBER_NOT_BYTES,
            "source.module",
            "future/test owner module is not exact bytes",
        )
        return DirectFallbackBoundaryReplayV2(
            DirectFallbackBoundaryReplayOutcomeV2.BLOCKED,
            None,
            None,
            tuple(sorted(set(blockers))),
        )
    archive_id = _archive_id({SOURCE_MODULE: raw})
    assert archive_id is not None
    try:
        tree = ast.parse(raw, filename=SOURCE_RELATIVE_PATH)
    except (SyntaxError, TypeError, ValueError):
        block(
            DirectFallbackBoundaryBlockerCodeV2.SOURCE_SYNTAX_INVALID,
            "source.module",
            "future/test owner module is not valid Python",
        )
        return DirectFallbackBoundaryReplayV2(
            DirectFallbackBoundaryReplayOutcomeV2.BLOCKED,
            archive_id,
            None,
            tuple(sorted(set(blockers))),
        )

    hook_calls = tuple(
        sorted(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and _call_name(node.func) == HOOK_SYMBOL
            ),
            key=lambda node: (
                node.lineno,
                node.col_offset,
                node.end_lineno or -1,
                node.end_col_offset or -1,
            ),
        )
    )
    literal_dispatches: list[str] = []
    for call in hook_calls:
        dispatch = _literal_hook_dispatch(call)
        if dispatch is None:
            block(
                DirectFallbackBoundaryBlockerCodeV2.HOOK_NON_LITERAL,
                "hook.inventory",
                "every route-segment hook requires literal dispatch and unit amount",
            )
        else:
            literal_dispatches.append(dispatch)
    expected_dispatches = tuple(sorted(spec.dispatch_key for spec in _SPECS))
    actual_dispatches = tuple(sorted(literal_dispatches))
    missing = tuple(sorted(set(expected_dispatches) - set(actual_dispatches)))
    extra = tuple(sorted(set(actual_dispatches) - set(expected_dispatches)))
    if missing or len(hook_calls) < EXPECTED_BOUNDARY_COUNT:
        block(
            DirectFallbackBoundaryBlockerCodeV2.HOOK_MISSING,
            "hook.inventory",
            f"missing literal dispatches: {missing!r}",
        )
    if extra or len(hook_calls) > EXPECTED_BOUNDARY_COUNT:
        block(
            DirectFallbackBoundaryBlockerCodeV2.HOOK_EXTRA,
            "hook.inventory",
            f"extra literal dispatches: {extra!r}",
        )

    symbols = _qualified_symbols(tree)
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    direct_stage = registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    allowed = set(stage.by_stage[direct_stage].allowed_nonzero_paths)
    boundaries: list[DirectFallbackOperationBoundaryV2] = []
    try:
        parent, parent_site = _parent_manifest_and_site()
    except Exception:
        block(
            DirectFallbackBoundaryBlockerCodeV2.PARENT_MANIFEST_CHANGED,
            PARENT_SITE_KEY,
            "Contract-2.0.36 parent fallback site did not replay",
        )
        parent = parent_site = None

    for spec in _SPECS:
        leaf = registry.by_path.get(spec.target_path)
        if (
            leaf is None
            or spec.target_path not in allowed
            or leaf.reducer is not ReducerEnum.SUM
        ):
            block(
                DirectFallbackBoundaryBlockerCodeV2.REGISTRY_BINDING_CHANGED,
                spec.boundary_key,
                "V6 direct-fallback path, stage owner, or reducer changed",
            )
            continue
        matches = symbols.get(spec.operation_source_symbol, ())
        if not matches:
            block(
                DirectFallbackBoundaryBlockerCodeV2.SYMBOL_MISSING,
                spec.boundary_key,
                "frozen owner symbol is absent",
            )
            continue
        if len(matches) != 1:
            block(
                DirectFallbackBoundaryBlockerCodeV2.SYMBOL_AMBIGUOUS,
                spec.boundary_key,
                "frozen owner symbol is ambiguous",
            )
            continue
        symbol = matches[0]
        if _sha256(ast.dump(symbol, include_attributes=False).encode("utf-8")) != spec.symbol_ast_sha256:
            block(
                DirectFallbackBoundaryBlockerCodeV2.SYMBOL_AST_CHANGED,
                spec.boundary_key,
                "frozen owner symbol AST changed",
            )
            continue
        calls = tuple(
            node
            for node in ast.walk(symbol)
            if isinstance(node, ast.Call) and _call_name(node.func) == HOOK_SYMBOL
        )
        if len(calls) != 1 or _literal_hook_dispatch(calls[0]) != spec.dispatch_key:
            block(
                DirectFallbackBoundaryBlockerCodeV2.HOOK_MISSING,
                spec.boundary_key,
                "owner symbol lacks its exact literal unit hook",
            )
            continue
        call = calls[0]
        if (
            call.lineno,
            call.col_offset,
            call.end_lineno,
            call.end_col_offset,
        ) != (
            spec.call_lineno,
            spec.call_col_offset,
            spec.call_end_lineno,
            spec.call_end_col_offset,
        ):
            block(
                DirectFallbackBoundaryBlockerCodeV2.CALL_LOCATION_CHANGED,
                spec.boundary_key,
                "literal hook call location changed",
            )
            continue
        if _sha256(ast.dump(call, include_attributes=False).encode("utf-8")) != spec.call_ast_sha256:
            block(
                DirectFallbackBoundaryBlockerCodeV2.CALL_AST_CHANGED,
                spec.boundary_key,
                "literal hook call AST changed",
            )
            continue
        if parent_site is not None:
            boundaries.append(
                DirectFallbackOperationBoundaryV2(
                    _ISSUER,
                    spec.boundary_key,
                    spec.dispatch_key,
                    direct_stage,
                    spec.target_path,
                    leaf.owner,
                    leaf.reducer,
                    SOURCE_MODULE,
                    spec.operation_source_symbol,
                    _SOURCE_SHA256,
                    _SOURCE_BYTE_COUNT,
                    spec.symbol_ast_sha256,
                    spec.call_ast_sha256,
                    spec.call_lineno,
                    spec.call_col_offset,
                    spec.call_end_lineno,
                    spec.call_end_col_offset,
                    parent_site.site_id,
                )
            )

    if len(raw) != _SOURCE_BYTE_COUNT or _sha256(raw) != _SOURCE_SHA256:
        block(
            DirectFallbackBoundaryBlockerCodeV2.SOURCE_BYTES_CHANGED,
            "source.module",
            "complete future/test owner source bytes changed",
        )
    if blockers:
        return DirectFallbackBoundaryReplayV2(
            DirectFallbackBoundaryReplayOutcomeV2.BLOCKED,
            archive_id,
            None,
            tuple(sorted(set(blockers))),
        )
    assert parent is not None and parent_site is not None
    manifest = DirectFallbackOperationBoundaryManifestV2(
        _ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        direct_stage,
        parent.manifest_id,
        parent_site.site_id,
        archive_id,
        tuple(sorted(boundaries, key=lambda row: row.boundary_key)),
    )
    return DirectFallbackBoundaryReplayV2(
        DirectFallbackBoundaryReplayOutcomeV2.VERIFIED,
        archive_id,
        manifest,
        (),
    )


def freeze_direct_fallback_operation_boundary_manifest_v2(
    *, source_archive: Mapping[str, bytes] | None = None
) -> DirectFallbackOperationBoundaryManifestV2:
    replay = replay_direct_fallback_operation_source_archive_v2(
        load_direct_fallback_operation_source_archive_v2()
        if source_archive is None
        else source_archive
    )
    if replay.outcome is DirectFallbackBoundaryReplayOutcomeV2.BLOCKED:
        error = ConstructionK7DirectFallbackOperationBoundaryManifestV2Error(
            "direct-fallback V2 source replay is blocked"
        )
        error.blockers = replay.blockers  # type: ignore[attr-defined]
        raise error
    assert replay.manifest is not None
    return replay.manifest


def verify_direct_fallback_operation_boundary_manifest_document_v2(
    document: Mapping[str, Any],
    source_archive: Mapping[str, bytes],
) -> DirectFallbackBoundaryReplayV2:
    replay = replay_direct_fallback_operation_source_archive_v2(source_archive)
    if replay.outcome is DirectFallbackBoundaryReplayOutcomeV2.BLOCKED:
        return replay
    assert replay.manifest is not None
    if (
        type(document) is not dict
        or canonical_json_bytes(document)
        != canonical_json_bytes(replay.manifest.to_document())
    ):
        blocker = DirectFallbackBoundaryBlockerV2(
            DirectFallbackBoundaryBlockerCodeV2.MANIFEST_DOCUMENT_CHANGED,
            "manifest.document",
            "supplied manifest differs from independent source replay",
        )
        return DirectFallbackBoundaryReplayV2(
            DirectFallbackBoundaryReplayOutcomeV2.BLOCKED,
            replay.source_archive_id,
            None,
            (blocker,),
        )
    return replay


__all__ = (
    "CENTRAL_DOMAIN_REGISTRATION_PENDING",
    "ConstructionK7DirectFallbackOperationBoundaryManifestV2Error",
    "DirectFallbackBoundaryBlockerCodeV2",
    "DirectFallbackBoundaryBlockerV2",
    "DirectFallbackBoundaryReplayOutcomeV2",
    "DirectFallbackBoundaryReplayV2",
    "DirectFallbackOperationBoundaryManifestV2",
    "DirectFallbackOperationBoundaryV2",
    "EXPECTED_PARENT_FALLBACK_SITE_DOCUMENT_SHA256",
    "EXPECTED_PARENT_FALLBACK_SITE_ID",
    "EXPECTED_PARENT_MANIFEST_DOCUMENT_SHA256",
    "EXPECTED_PARENT_MANIFEST_ID",
    "EXPECTED_BOUNDARY_COUNT",
    "EXPECTED_SOURCE_MEMBER_COUNT",
    "PARENT_SITE_KEY",
    "PRODUCTION_CLOSURE_CLAIMED",
    "PRODUCTION_SOURCE_INTEGRATED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SOURCE_MODULE",
    "freeze_direct_fallback_operation_boundary_manifest_v2",
    "load_direct_fallback_operation_source_archive_v2",
    "replay_direct_fallback_operation_source_archive_v2",
    "verify_direct_fallback_operation_boundary_manifest_document_v2",
)
