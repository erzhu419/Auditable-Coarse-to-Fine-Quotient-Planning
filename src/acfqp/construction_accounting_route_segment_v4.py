"""Sealed-source construction successor for the owned fallback segment.

V3 joins the owner ledger to live repository paths while constructing its
session.  This additive V4 slice removes that construction dependency: its
only source inputs are one canonical sealed member and one canonical V3
operation-boundary-manifest document.  It replays their exact join without a
live archive loader, ``Path(__file__)``, cwd/repository discovery, or any
ground/planner operation.

The currently sealed owner still imports the frozen V3 gateway, bind and
finish functions.  Consequently the verified V4 authority carries an
explicit blocker for production owner execution.  A construction harness
exercises the immutable positive-prefix lifecycle without pretending that its
events came from the production owner.  A future owner engine must import the
V4 gateway before the production runtime entry can be enabled.
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import InitVar, dataclass
from enum import Enum
import hashlib
import sys
import threading
from types import MappingProxyType
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_EVENT_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_MANIFEST_AUTHORITY_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNER_BLOCKER_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_SOURCE_AUTHORITY_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_START_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TERMINAL_DOMAIN,
    CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TRANSCRIPT_DOMAIN,
    Phase3EIdentityError,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "4.0.0"
PROFILE_KEY = "construction_accounting_route_segment_v4"
PROPOSED_CONTRACT_VERSION = "2.0.53"
REQUIRED_CONTRACT_VERSION = "2.0.52"
CONSTRUCTION_ONLY = True
PRODUCTION_OWNER_SOURCE_INTEGRATED = False
PRODUCTION_CLOSURE_CLAIMED = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"

SOURCE_MODULE = "acfqp.phase3e_fallback_owned_v2"
SOURCE_RELATIVE_PATH = "phase3e_fallback_owned_v2.py"
LEGACY_OWNER_GATEWAY = "emit_owned_route_operation_v3"
REQUIRED_OWNER_GATEWAY = "emit_owned_route_operation_v4"
EXPECTED_SOURCE_BYTE_COUNT = 24965
EXPECTED_SOURCE_SHA256 = (
    "ed1b6f6dbc186552f33363da55f6fbeb1727f84f1b598d15939c63cbba0ce3b4"
)
EXPECTED_BOUNDARY_MANIFEST_ID = (
    "867b465489484b8fafe5acbb39675b9b14eb152729df93116e138e9ed8b23e17"
)
EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256 = (
    "20545882606e09958a7895130bb03d6a9b29f4ee956d79611a3ffbda5e4a8274"
)
EXPECTED_BOUNDARY_COUNT = 7

_LEGACY_ARCHIVE_DOMAIN = "acfqp:construction-k7-direct-fallback-source-archive:v3"
_LEGACY_BOUNDARY_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-boundary:v3"
)
_LEGACY_MANIFEST_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-operation-manifest:v3"
)
_ISSUER = object()
_FROZEN_GETFRAME_V4 = sys._getframe  # noqa: SLF001


class ConstructionAccountingRouteSegmentV4Error(ValueError):
    """The sealed source, authority, operation prefix, or lifecycle is invalid."""


class OwnerRuntimeIntegrationBlockedV4(ConstructionAccountingRouteSegmentV4Error):
    """The sealed owner does not import the V4 runtime gateway."""

    def __init__(self, blocker: "OwnerRuntimeIntegrationBlockerV4") -> None:
        super().__init__(blocker.code)
        self.blocker = blocker


class RouteSegmentTerminalKindV4(str, Enum):
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class RouteOperationOriginV4(str, Enum):
    CONSTRUCTION_VERIFIED_SOURCE_REPLAY = "CONSTRUCTION_VERIFIED_SOURCE_REPLAY"
    SOURCE_OWNED_RUNTIME = "SOURCE_OWNED_RUNTIME"


class _SessionModeV4(str, Enum):
    CONSTRUCTION = "CONSTRUCTION"
    OWNED_RUNTIME = "OWNED_RUNTIME"


def _fail(message: str) -> NoReturn:
    raise ConstructionAccountingRouteSegmentV4Error(message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _legacy_content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            f"{label} must be one full content ID"
        ) from error


def _require_route_node_issuance(issuer: object, key: str, node: Any) -> None:
    """Bind readable-token construction to one exact session method."""

    if issuer is not _ISSUER:
        _fail("V4 route-segment node is session-issued only")
    try:
        generated_init = _FROZEN_GETFRAME_V4(2)
        session_caller = _FROZEN_GETFRAME_V4(3)
        expected_code = _FROZEN_ROUTE_NODE_CODES_V4[key]
    except (AttributeError, KeyError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "V4 route-segment issuance ancestry is unavailable"
        ) from error
    if (
        generated_init.f_code is not type(node).__init__.__code__
        or session_caller.f_globals is not _FROZEN_ROUTE_NODE_GLOBALS_V4
        or (
            session_caller.f_code not in expected_code
            if type(expected_code) is tuple
            else session_caller.f_code is not expected_code
        )
    ):
        _fail("V4 route-segment node bypassed its exact session issuer")


@dataclass(frozen=True, slots=True)
class _SiteSpecV4:
    boundary_key: str
    dispatch_key: str
    target_path: str
    operation_source_symbol: str


_SITE_SPECS: tuple[_SiteSpecV4, ...] = (
    _SiteSpecV4(
        "direct-fallback.action-evaluated",
        "direct-fallback.action.evaluated",
        "fallback.actions_evaluated",
        "_OwnedFallbackLedgerV2.evaluate_action",
    ),
    _SiteSpecV4(
        "direct-fallback.bellman-backup",
        "direct-fallback.bellman.backup",
        "fallback.bellman_backups",
        "_OwnedFallbackLedgerV2.compose_candidate",
    ),
    _SiteSpecV4(
        "direct-fallback.cap-check",
        "direct-fallback.control.cap-check",
        "control.cap_checks",
        "_OwnedFallbackLedgerV2._guard",
    ),
    _SiteSpecV4(
        "direct-fallback.cap-rejection",
        "direct-fallback.control.cap-rejection",
        "control.cap_rejections",
        "_OwnedFallbackLedgerV2._reject",
    ),
    _SiteSpecV4(
        "direct-fallback.ground-step",
        "direct-fallback.kernel.transition",
        "fallback.ground_steps",
        "_OwnedFallbackLedgerV2.reserve_transition",
    ),
    _SiteSpecV4(
        "direct-fallback.outcome-row",
        "direct-fallback.outcome.row",
        "fallback.outcome_rows",
        "_OwnedFallbackLedgerV2.record_outcomes",
    ),
    _SiteSpecV4(
        "direct-fallback.state-expanded",
        "direct-fallback.state.expanded",
        "fallback.states_expanded",
        "_OwnedFallbackLedgerV2.expand_state",
    ),
)
_SPEC_BY_DISPATCH = MappingProxyType({row.dispatch_key: row for row in _SITE_SPECS})
_EXPECTED_PATHS = frozenset(row.target_path for row in _SITE_SPECS)


@dataclass(frozen=True, slots=True)
class SealedSourceMemberAuthorityV4:
    _issuer: InitVar[object]
    source_module: str
    source_sha256: str
    source_byte_count: int
    legacy_source_archive_id: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("sealed source authority is verifier-issued only")
        if (
            self.source_module != SOURCE_MODULE
            or self.source_sha256 != EXPECTED_SOURCE_SHA256
            or self.source_byte_count != EXPECTED_SOURCE_BYTE_COUNT
        ):
            _fail("sealed source authority changed the exact member")
        _cid(self.legacy_source_archive_id, "legacy source archive")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.sealed_route_segment_source_authority.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_module": self.source_module,
            "source_relative_path": SOURCE_RELATIVE_PATH,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "legacy_source_archive_id": self.legacy_source_archive_id,
            "input_form": "CALLER_SUPPLIED_CANONICAL_SEALED_MEMBER_BYTES",
            "live_archive_loader_called": False,
            "filesystem_locator_used": False,
            "construction_only": True,
        }

    @property
    def source_authority_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_SOURCE_AUTHORITY_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_authority_id": self.source_authority_id}


@dataclass(frozen=True, slots=True)
class VerifiedOperationBoundaryV4:
    _issuer: InitVar[object]
    boundary_id: str
    boundary_key: str
    dispatch_key: str
    target_path: str
    owner: str
    operation_source_module: str
    operation_source_symbol: str
    source_gateway_symbol: str
    symbol_ast_sha256: str
    call_ast_sha256: str
    call_location: tuple[int, int, int, int]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("verified operation boundary is verifier-issued only")
        _cid(self.boundary_id, "operation boundary")
        spec = _SPEC_BY_DISPATCH.get(self.dispatch_key)
        if (
            spec is None
            or self.boundary_key != spec.boundary_key
            or self.target_path != spec.target_path
            or self.operation_source_module != SOURCE_MODULE
            or self.operation_source_symbol != spec.operation_source_symbol
            or self.source_gateway_symbol != LEGACY_OWNER_GATEWAY
            or type(self.call_location) is not tuple
            or len(self.call_location) != 4
            or any(type(value) is not int or value < 0 for value in self.call_location)
        ):
            _fail("verified operation boundary changed the seven-site inventory")
        for value in (self.owner, self.symbol_ast_sha256, self.call_ast_sha256):
            if type(value) is not str or not value:
                _fail("verified operation boundary text is invalid")

    def to_document(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "target_path": self.target_path,
            "owner": self.owner,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "source_gateway_symbol": self.source_gateway_symbol,
            "symbol_ast_sha256": self.symbol_ast_sha256,
            "call_ast_sha256": self.call_ast_sha256,
            "call_location": list(self.call_location),
            "reducer": ReducerEnum.SUM.value,
            "unit_amount": True,
        }


@dataclass(frozen=True, slots=True)
class OwnerRuntimeIntegrationBlockerV4:
    _issuer: InitVar[object]
    observed_gateway_symbol: str
    required_gateway_symbol: str
    observed_bind_finish_contract: str
    required_successor: str
    code: str = "SUCCESSOR_OWNED_ENGINE_IMPORTING_V4_GATEWAYS_REQUIRED"

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("owner integration blocker is verifier-issued only")
        if (
            self.observed_gateway_symbol != LEGACY_OWNER_GATEWAY
            or self.required_gateway_symbol != REQUIRED_OWNER_GATEWAY
            or self.observed_bind_finish_contract != "FROZEN_V3_AUTHORIZER"
            or self.required_successor != "SEALED_SOURCE_OWNED_ENGINE_V4"
        ):
            _fail("owner integration blocker changed its exact dependency")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_segment_owner_integration_blocker.v4",
            "schema_version": SCHEMA_VERSION,
            "code": self.code,
            "observed_gateway_symbol": self.observed_gateway_symbol,
            "required_gateway_symbol": self.required_gateway_symbol,
            "observed_bind_finish_contract": self.observed_bind_finish_contract,
            "required_successor": self.required_successor,
            "v3_authorizer_bypass_allowed": False,
            "production_owner_source_integrated": False,
            "construction_only": True,
        }

    @property
    def blocker_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNER_BLOCKER_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "blocker_id": self.blocker_id}


@dataclass(frozen=True, slots=True)
class VerifiedOperationBoundaryManifestAuthorityV4:
    _issuer: InitVar[object]
    source_authority: SealedSourceMemberAuthorityV4
    legacy_boundary_manifest_id: str
    manifest_document_sha256: str
    manifest_document_byte_count: int
    counter_registry_id: str
    stage_profile_id: str
    boundaries: tuple[VerifiedOperationBoundaryV4, ...]
    owner_integration_blocker: OwnerRuntimeIntegrationBlockerV4

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("operation-boundary manifest authority is verifier-issued only")
        if (
            type(self.source_authority) is not SealedSourceMemberAuthorityV4
            or type(self.boundaries) is not tuple
            or len(self.boundaries) != EXPECTED_BOUNDARY_COUNT
            or tuple(sorted(self.boundaries, key=lambda row: row.boundary_key))
            != self.boundaries
            or {row.dispatch_key for row in self.boundaries}
            != set(_SPEC_BY_DISPATCH)
            or type(self.owner_integration_blocker)
            is not OwnerRuntimeIntegrationBlockerV4
            or self.legacy_boundary_manifest_id != EXPECTED_BOUNDARY_MANIFEST_ID
            or self.manifest_document_sha256
            != EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256
            or type(self.manifest_document_byte_count) is not int
            or self.manifest_document_byte_count <= 0
        ):
            _fail("operation-boundary manifest authority is inconsistent")
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
        ):
            _cid(value, label)

    @property
    def by_dispatch(self) -> Mapping[str, VerifiedOperationBoundaryV4]:
        return MappingProxyType({row.dispatch_key: row for row in self.boundaries})

    @property
    def runtime_gateway_compatible(self) -> bool:
        return False

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_operation_boundary_manifest_authority.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "required_contract_version": REQUIRED_CONTRACT_VERSION,
            "source_authority_id": self.source_authority.source_authority_id,
            "legacy_boundary_manifest_id": self.legacy_boundary_manifest_id,
            "manifest_document_sha256": self.manifest_document_sha256,
            "manifest_document_byte_count": self.manifest_document_byte_count,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "stage_kind": registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value,
            "boundaries": [row.to_document() for row in self.boundaries],
            "boundary_count": len(self.boundaries),
            "owner_integration_blocker_id": self.owner_integration_blocker.blocker_id,
            "runtime_gateway_compatible": False,
            "ground_or_planner_work_performed_during_construction": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "production_owner_source_integrated": False,
            "production_closure_claimed": False,
        }

    @property
    def manifest_authority_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_MANIFEST_AUTHORITY_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_authority": self.source_authority.to_document(),
            "owner_integration_blocker": self.owner_integration_blocker.to_document(),
            "manifest_authority_id": self.manifest_authority_id,
        }


_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "counter_registry_id",
        "stage_profile_id",
        "stage_kind",
        "parent_v2_manifest_id",
        "parent_v2_manifest_document_sha256",
        "source_archive_id",
        "live_owner_binding_id",
        "source_members",
        "boundaries",
        "boundary_count",
        "production_source_integrated",
        "runtime_evidence_issued",
        "counter_records_issued",
        "work_vectors_issued",
        "comparison_vectors_issued",
        "construction_only",
        "production_closure_claimed",
        "boundary_manifest_id",
    }
)
_BOUNDARY_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "boundary_key",
        "dispatch_key",
        "stage_kind",
        "target_path",
        "owner",
        "reducer",
        "operation_source_module",
        "operation_source_symbol",
        "source_sha256",
        "source_byte_count",
        "symbol_ast_sha256",
        "call_ast_sha256",
        "call_location",
        "literal_dispatch",
        "unit_amount",
        "real_ledger_primitive_site",
        "construction_only",
        "boundary_id",
    }
)


def _qualified_functions(tree: ast.AST) -> dict[str, ast.FunctionDef]:
    found: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_OwnedFallbackLedgerV2":
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    found[f"{node.name}.{child.name}"] = child
    return found


def _literal_gateway_call(call: ast.Call) -> tuple[str, str] | None:
    if not isinstance(call.func, ast.Name):
        return None
    if call.func.id not in {LEGACY_OWNER_GATEWAY, REQUIRED_OWNER_GATEWAY}:
        return None
    if len(call.args) != 2 or call.keywords:
        return None
    dispatch, amount = call.args
    if (
        not isinstance(dispatch, ast.Constant)
        or type(dispatch.value) is not str
        or not isinstance(amount, ast.Constant)
        or type(amount.value) is not int
        or amount.value != 1
    ):
        return None
    return call.func.id, dispatch.value


def verify_sealed_operation_boundary_authority_v4(
    source_member_bytes: bytes,
    boundary_manifest_document_bytes: bytes,
) -> VerifiedOperationBoundaryManifestAuthorityV4:
    """Replay the exact V3 source/manifest join from caller-supplied bytes only."""

    if type(source_member_bytes) is not bytes:
        _fail("sealed source member must be exact bytes")
    if (
        len(source_member_bytes) != EXPECTED_SOURCE_BYTE_COUNT
        or _sha256(source_member_bytes) != EXPECTED_SOURCE_SHA256
    ):
        _fail("sealed source member differs from the frozen V3 owner source")
    if type(boundary_manifest_document_bytes) is not bytes:
        _fail("operation-boundary manifest document must be canonical bytes")
    if (
        _sha256(boundary_manifest_document_bytes)
        != EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256
    ):
        _fail("operation-boundary manifest document digest changed")
    try:
        document = loads_canonical_json(boundary_manifest_document_bytes)
        require_exact_fields(
            document,
            _MANIFEST_FIELDS,
            context="V3 operation-boundary manifest",
        )
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "operation-boundary manifest document is not canonical"
        ) from error
    if type(document) is not dict:
        _fail("operation-boundary manifest document must be an object")
    manifest_payload = dict(document)
    manifest_id = manifest_payload.pop("boundary_manifest_id")
    if (
        manifest_id != EXPECTED_BOUNDARY_MANIFEST_ID
        or _legacy_content_id(_LEGACY_MANIFEST_DOMAIN, manifest_payload)
        != manifest_id
        or document["schema"]
        != "acfqp.direct_fallback_operation_boundary_manifest.v3"
        or document["schema_version"] != "3.0.0"
        or document["stage_kind"]
        != registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value
        or document["boundary_count"] != EXPECTED_BOUNDARY_COUNT
        or document["runtime_evidence_issued"] is not False
        or document["counter_records_issued"] != 0
        or document["work_vectors_issued"] != 0
        or document["comparison_vectors_issued"] != 0
        or document["construction_only"] is not True
        or document["production_closure_claimed"] is not False
    ):
        _fail("operation-boundary manifest document changed its exact contract")

    legacy_archive_id = _legacy_content_id(
        _LEGACY_ARCHIVE_DOMAIN,
        {
            "schema": "acfqp.direct_fallback_source_archive.v3",
            "schema_version": "3.0.0",
            "members": [
                {
                    "module_name": SOURCE_MODULE,
                    "source_sha256": EXPECTED_SOURCE_SHA256,
                    "source_byte_count": EXPECTED_SOURCE_BYTE_COUNT,
                }
            ],
        },
    )
    expected_member = {
        "module_name": SOURCE_MODULE,
        "relative_path": SOURCE_RELATIVE_PATH,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_byte_count": EXPECTED_SOURCE_BYTE_COUNT,
    }
    if (
        document["source_archive_id"] != legacy_archive_id
        or document["source_members"] != [expected_member]
    ):
        _fail("operation-boundary manifest crossed its sealed source member")

    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    registry.validate_official_catalogue()
    stage_profile.validate(registry)
    if (
        document["counter_registry_id"] != registry.registry_id
        or document["stage_profile_id"] != stage_profile.stage_profile_id
    ):
        _fail("operation-boundary manifest crossed the V6 registry or stage profile")
    allowed = set(
        stage_profile.by_stage[
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ].allowed_nonzero_paths
    )

    try:
        tree = ast.parse(source_member_bytes, filename="<sealed-source-member-v4>")
    except (SyntaxError, TypeError, ValueError) as error:
        raise ConstructionAccountingRouteSegmentV4Error(
            "sealed source member is not valid Python"
        ) from error
    functions = _qualified_functions(tree)
    all_gateway_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {LEGACY_OWNER_GATEWAY, REQUIRED_OWNER_GATEWAY}
    ]
    literal_calls = [_literal_gateway_call(call) for call in all_gateway_calls]
    if (
        len(all_gateway_calls) != EXPECTED_BOUNDARY_COUNT
        or any(row is None for row in literal_calls)
        or {row[1] for row in literal_calls if row is not None}
        != set(_SPEC_BY_DISPATCH)
        or {row[0] for row in literal_calls if row is not None}
        != {LEGACY_OWNER_GATEWAY}
    ):
        _fail("sealed source changed the exact seven legacy owner gateways")

    raw_boundaries = document["boundaries"]
    if type(raw_boundaries) is not list or len(raw_boundaries) != EXPECTED_BOUNDARY_COUNT:
        _fail("operation-boundary manifest lacks seven boundaries")
    verified_boundaries: list[VerifiedOperationBoundaryV4] = []
    for row in raw_boundaries:
        try:
            require_exact_fields(row, _BOUNDARY_FIELDS, context="V3 operation boundary")
        except Phase3EIdentityError as error:
            raise ConstructionAccountingRouteSegmentV4Error(
                "operation-boundary row fields changed"
            ) from error
        if type(row) is not dict:
            _fail("operation-boundary row must be an object")
        boundary_payload = dict(row)
        boundary_id = boundary_payload.pop("boundary_id")
        spec = _SPEC_BY_DISPATCH.get(row["dispatch_key"])
        leaf = registry.by_path.get(row["target_path"])
        if (
            spec is None
            or row["boundary_key"] != spec.boundary_key
            or row["target_path"] != spec.target_path
            or row["operation_source_symbol"] != spec.operation_source_symbol
            or row["operation_source_module"] != SOURCE_MODULE
            or row["source_sha256"] != EXPECTED_SOURCE_SHA256
            or row["source_byte_count"] != EXPECTED_SOURCE_BYTE_COUNT
            or row["reducer"] != ReducerEnum.SUM.value
            or row["stage_kind"]
            != registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value
            or row["literal_dispatch"] is not True
            or row["unit_amount"] is not True
            or row["real_ledger_primitive_site"] is not True
            or row["construction_only"] is not True
            or _legacy_content_id(_LEGACY_BOUNDARY_DOMAIN, boundary_payload)
            != boundary_id
            or leaf is None
            or row["target_path"] not in allowed
            or leaf.reducer is not ReducerEnum.SUM
            or row["owner"] != leaf.owner
        ):
            _fail("operation-boundary row changed its source or V6 ownership")
        symbol = functions.get(spec.operation_source_symbol)
        if symbol is None:
            _fail("sealed source lost an owned ledger method")
        matching = [
            call
            for call in ast.walk(symbol)
            if isinstance(call, ast.Call)
            and _literal_gateway_call(call)
            == (LEGACY_OWNER_GATEWAY, spec.dispatch_key)
        ]
        if len(matching) != 1:
            _fail("sealed source lost an exact owned gateway call")
        call = matching[0]
        symbol_hash = _sha256(
            ast.dump(symbol, include_attributes=False).encode("utf-8")
        )
        call_hash = _sha256(ast.dump(call, include_attributes=False).encode("utf-8"))
        location = (
            call.lineno,
            call.col_offset,
            call.end_lineno,
            call.end_col_offset,
        )
        if (
            row["symbol_ast_sha256"] != symbol_hash
            or row["call_ast_sha256"] != call_hash
            or row["call_location"] != list(location)
        ):
            _fail("sealed source AST differs from its boundary manifest")
        verified_boundaries.append(
            VerifiedOperationBoundaryV4(
                _ISSUER,
                boundary_id,
                spec.boundary_key,
                spec.dispatch_key,
                spec.target_path,
                leaf.owner,
                SOURCE_MODULE,
                spec.operation_source_symbol,
                LEGACY_OWNER_GATEWAY,
                symbol_hash,
                call_hash,
                location,
            )
        )

    source_authority = SealedSourceMemberAuthorityV4(
        _ISSUER,
        SOURCE_MODULE,
        EXPECTED_SOURCE_SHA256,
        EXPECTED_SOURCE_BYTE_COUNT,
        legacy_archive_id,
    )
    blocker = OwnerRuntimeIntegrationBlockerV4(
        _ISSUER,
        LEGACY_OWNER_GATEWAY,
        REQUIRED_OWNER_GATEWAY,
        "FROZEN_V3_AUTHORIZER",
        "SEALED_SOURCE_OWNED_ENGINE_V4",
    )
    return VerifiedOperationBoundaryManifestAuthorityV4(
        _ISSUER,
        source_authority,
        manifest_id,
        EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256,
        len(boundary_manifest_document_bytes),
        registry.registry_id,
        stage_profile.stage_profile_id,
        tuple(sorted(verified_boundaries, key=lambda item: item.boundary_key)),
        blocker,
    )


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentStartV4:
    _issuer: InitVar[object]
    route_segment_id: str
    occurrence_id: str
    route_attempt_id: str
    recorder_id: str
    manifest_authority_id: str
    owner_integration_blocker_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "START", self)
        for value, label in (
            (self.route_segment_id, "route segment"),
            (self.occurrence_id, "occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.manifest_authority_id, "manifest authority"),
            (self.owner_integration_blocker_id, "owner integration blocker"),
        ):
            _cid(value, label)
        if type(self.recorder_id) is not str or not self.recorder_id:
            _fail("recorder ID must be nonempty")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_start.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_id": self.route_segment_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "recorder_id": self.recorder_id,
            "manifest_authority_id": self.manifest_authority_id,
            "owner_integration_blocker_id": self.owner_integration_blocker_id,
            "construction_only": True,
            "production_owner_source_integrated": False,
        }

    @property
    def start_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_START_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_start_id": self.start_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteOperationEventV4:
    _issuer: InitVar[object]
    route_segment_start_id: str
    boundary_id: str
    dispatch_key: str
    path: str
    operation_source_symbol: str
    origin: RouteOperationOriginV4
    amount: int
    event_sequence: int
    predecessor_chain_id: str

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "EVENT", self)
        _cid(self.route_segment_start_id, "route segment start")
        _cid(self.boundary_id, "operation boundary")
        _cid(self.predecessor_chain_id, "predecessor chain")
        try:
            object.__setattr__(self, "origin", RouteOperationOriginV4(self.origin))
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRouteSegmentV4Error(
                "route operation origin is invalid"
            ) from error
        if (
            type(self.dispatch_key) is not str
            or not self.dispatch_key
            or type(self.path) is not str
            or not self.path
            or type(self.operation_source_symbol) is not str
            or not self.operation_source_symbol
            or type(self.amount) is not int
            or self.amount != 1
            or type(self.event_sequence) is not int
            or self.event_sequence <= 0
        ):
            _fail("route operation event is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_operation_event.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_start_id": self.route_segment_start_id,
            "boundary_id": self.boundary_id,
            "dispatch_key": self.dispatch_key,
            "path": self.path,
            "operation_source_symbol": self.operation_source_symbol,
            "origin": self.origin.value,
            "source_owned_runtime_event": (
                self.origin is RouteOperationOriginV4.SOURCE_OWNED_RUNTIME
            ),
            "reducer": ReducerEnum.SUM.value,
            "amount": self.amount,
            "event_sequence": self.event_sequence,
            "predecessor_chain_id": self.predecessor_chain_id,
            "construction_only": True,
        }

    @property
    def event_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_EVENT_DOMAIN,
            self._payload(),
        )

    @property
    def chain_id(self) -> str:
        return self.event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operation_event_id": self.event_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentTerminalV4:
    _issuer: InitVar[object]
    route_segment_start_id: str
    terminal_kind: RouteSegmentTerminalKindV4
    event_ids: tuple[str, ...]
    predecessor_chain_id: str
    abort_reason: str | None

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "TERMINAL", self)
        _cid(self.route_segment_start_id, "route segment start")
        _cid(self.predecessor_chain_id, "predecessor chain")
        try:
            object.__setattr__(
                self, "terminal_kind", RouteSegmentTerminalKindV4(self.terminal_kind)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRouteSegmentV4Error(
                "route terminal kind is invalid"
            ) from error
        if type(self.event_ids) is not tuple or len(set(self.event_ids)) != len(
            self.event_ids
        ):
            _fail("route terminal changed event coverage")
        for event_id in self.event_ids:
            _cid(event_id, "operation event")
        if self.terminal_kind is RouteSegmentTerminalKindV4.COMPLETED:
            if self.abort_reason is not None:
                _fail("completed route segment cannot carry an abort reason")
        elif type(self.abort_reason) is not str or not self.abort_reason:
            _fail("aborted route segment requires a reason")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_terminal.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_segment_start_id": self.route_segment_start_id,
            "terminal_kind": self.terminal_kind.value,
            "event_count": len(self.event_ids),
            "event_ids": list(self.event_ids),
            "predecessor_chain_id": self.predecessor_chain_id,
            "abort_reason": self.abort_reason,
            "positive_prefix_retained": True,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "production_closure_claimed": False,
        }

    @property
    def terminal_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TERMINAL_DOMAIN,
            self._payload(),
        )

    @property
    def chain_id(self) -> str:
        return self.terminal_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_terminal_id": self.terminal_id}


@dataclass(frozen=True, slots=True)
class OwnedRouteSegmentTranscriptV4:
    _issuer: InitVar[object]
    start: OwnedRouteSegmentStartV4
    events: tuple[OwnedRouteOperationEventV4, ...]
    terminal: OwnedRouteSegmentTerminalV4

    def __post_init__(self, _issuer: object) -> None:
        _require_route_node_issuance(_issuer, "TRANSCRIPT", self)
        if (
            type(self.start) is not OwnedRouteSegmentStartV4
            or type(self.events) is not tuple
            or type(self.terminal) is not OwnedRouteSegmentTerminalV4
        ):
            _fail("route transcript uses foreign objects")
        predecessor = self.start.start_id
        for sequence, event in enumerate(self.events, start=1):
            if (
                type(event) is not OwnedRouteOperationEventV4
                or event.route_segment_start_id != self.start.start_id
                or event.event_sequence != sequence
                or event.predecessor_chain_id != predecessor
            ):
                _fail("route transcript event chain is discontinuous")
            predecessor = event.chain_id
        if (
            self.terminal.route_segment_start_id != self.start.start_id
            or self.terminal.predecessor_chain_id != predecessor
            or self.terminal.event_ids != tuple(row.event_id for row in self.events)
        ):
            _fail("route transcript terminal changed its positive prefix")

    @property
    def values(self) -> Mapping[str, int]:
        values: dict[str, int] = {}
        for event in self.events:
            values[event.path] = values.get(event.path, 0) + event.amount
        return MappingProxyType(values)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.owned_route_segment_transcript.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "start": self.start.to_document(),
            "events": [row.to_document() for row in self.events],
            "terminal": self.terminal.to_document(),
            "event_count": len(self.events),
            "positive_prefix_retained": True,
            "absent_event_is_zero": False,
            "event_origins": sorted({row.origin.value for row in self.events}),
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
            "production_owner_source_integrated": False,
            "production_closure_claimed": False,
        }

    @property
    def transcript_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TRANSCRIPT_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_segment_transcript_id": self.transcript_id}


class OwnedFallbackRouteSegmentSessionV4:
    """Sealed-byte session; current production owner runtime remains blocked."""

    def __init__(
        self,
        *,
        route_segment_id: str,
        occurrence_id: str,
        route_attempt_id: str,
        recorder_id: str,
        source_member_bytes: bytes,
        boundary_manifest_document_bytes: bytes,
        manifest_authority: VerifiedOperationBoundaryManifestAuthorityV4,
    ) -> None:
        replayed = verify_sealed_operation_boundary_authority_v4(
            source_member_bytes,
            boundary_manifest_document_bytes,
        )
        if (
            type(manifest_authority)
            is not VerifiedOperationBoundaryManifestAuthorityV4
            or canonical_json_bytes(manifest_authority.to_document())
            != canonical_json_bytes(replayed.to_document())
        ):
            _fail("route segment requires the exact replayed sealed authority")
        self._lock = threading.RLock()
        self._owner_thread_id = threading.get_ident()
        self._authority = replayed
        self._by_dispatch = replayed.by_dispatch
        self._start = OwnedRouteSegmentStartV4(
            _ISSUER,
            _cid(route_segment_id, "route segment"),
            _cid(occurrence_id, "occurrence"),
            _cid(route_attempt_id, "route attempt"),
            recorder_id,
            replayed.manifest_authority_id,
            replayed.owner_integration_blocker.blocker_id,
        )
        self._events: list[OwnedRouteOperationEventV4] = []
        self._mode: _SessionModeV4 | None = None
        self._terminal: OwnedRouteSegmentTerminalV4 | None = None
        self._finished_values: Mapping[str, int] | None = None

    @property
    def authority(self) -> VerifiedOperationBoundaryManifestAuthorityV4:
        return self._authority

    @property
    def start(self) -> OwnedRouteSegmentStartV4:
        return self._start

    @property
    def is_terminal(self) -> bool:
        return self._terminal is not None

    @property
    def owner_integration_blocker(self) -> OwnerRuntimeIntegrationBlockerV4:
        return self._authority.owner_integration_blocker

    @property
    def transcript(self) -> OwnedRouteSegmentTranscriptV4:
        if self._terminal is None:
            _fail("V4 transcript is unavailable before terminalization")
        return OwnedRouteSegmentTranscriptV4(
            _ISSUER, self._start, tuple(self._events), self._terminal
        )

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            self._abort("CROSS_THREAD_ACTIVE_SCOPE")
            _fail("V4 route segment crossed its owner thread")

    def _predecessor(self) -> str:
        return self._events[-1].chain_id if self._events else self._start.start_id

    def enter_construction_harness(self) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or self._mode is not None:
                _fail("V4 construction harness entered in an invalid state")
            self._mode = _SessionModeV4.CONSTRUCTION

    def enter_owned_runtime(self) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or self._mode is not None:
                _fail("V4 owned runtime entered in an invalid state")
            if not self._authority.runtime_gateway_compatible:
                raise OwnerRuntimeIntegrationBlockedV4(
                    self._authority.owner_integration_blocker
                )
            self._mode = _SessionModeV4.OWNED_RUNTIME

    def _record(
        self,
        dispatch_key: Any,
        amount: Any,
        *,
        origin: RouteOperationOriginV4,
        caller_module: str | None = None,
        caller_qualname: str | None = None,
    ) -> object:
        with self._lock:
            self._check_thread()
            if self._terminal is not None or self._mode is None:
                self._abort("EVENT_OUTSIDE_ACTIVE_STAGE")
                _fail("V4 operation lies outside its active stage")
            if type(dispatch_key) is not str or type(amount) is not int or amount != 1:
                self._abort("MALFORMED_OPERATION")
                _fail("V4 operation must be one literal unit primitive")
            boundary = self._by_dispatch.get(dispatch_key)
            if boundary is None:
                self._abort("UNKNOWN_DISPATCH")
                _fail("V4 dispatch is absent from the verified seven-site manifest")
            if origin is RouteOperationOriginV4.CONSTRUCTION_VERIFIED_SOURCE_REPLAY:
                if self._mode is not _SessionModeV4.CONSTRUCTION:
                    self._abort("CONSTRUCTION_ORIGIN_OUTSIDE_HARNESS")
                    _fail("construction replay event crossed into owned runtime")
            else:
                if self._mode is not _SessionModeV4.OWNED_RUNTIME:
                    self._abort("RUNTIME_ORIGIN_OUTSIDE_OWNER")
                    _fail("source-owned event crossed into construction replay")
                if (
                    caller_module != boundary.operation_source_module
                    or caller_qualname != boundary.operation_source_symbol
                ):
                    self._abort("OWNER_MISMATCH")
                    _fail("V4 source-owned caller differs from its sealed boundary")
            self._events.append(
                OwnedRouteOperationEventV4(
                    _ISSUER,
                    self._start.start_id,
                    boundary.boundary_id,
                    boundary.dispatch_key,
                    boundary.target_path,
                    boundary.operation_source_symbol,
                    origin,
                    1,
                    len(self._events) + 1,
                    self._predecessor(),
                )
            )
            return OWNED_ROUTE_EVENT_ACK_V4

    def finish_construction_harness(
        self, exact_ledger_values: Mapping[str, int]
    ) -> None:
        with self._lock:
            self._check_thread()
            if (
                self._terminal is not None
                or self._mode is not _SessionModeV4.CONSTRUCTION
                or self._finished_values is not None
                or not isinstance(exact_ledger_values, Mapping)
                or set(exact_ledger_values) != _EXPECTED_PATHS
                or any(
                    type(value) is not int or value < 0
                    for value in exact_ledger_values.values()
                )
            ):
                self._abort("INVALID_CONSTRUCTION_FINISH")
                _fail("V4 construction finish lacks the exact seven ledger values")
            positive = {
                path: value for path, value in exact_ledger_values.items() if value > 0
            }
            if (
                dict(self._current_values()) != positive
                or len(self._events) != sum(positive.values())
            ):
                self._abort("LEDGER_TRANSCRIPT_DIVERGENCE")
                _fail("V4 exact ledger values diverge from the positive prefix")
            self._finished_values = MappingProxyType(dict(exact_ledger_values))

    def _current_values(self) -> Mapping[str, int]:
        values: dict[str, int] = {}
        for event in self._events:
            values[event.path] = values.get(event.path, 0) + event.amount
        return MappingProxyType(values)

    def complete(self) -> OwnedRouteSegmentTranscriptV4:
        with self._lock:
            self._check_thread()
            if (
                self._terminal is not None
                or self._mode is not _SessionModeV4.CONSTRUCTION
                or self._finished_values is None
                or dict(self._current_values())
                != {
                    path: value
                    for path, value in self._finished_values.items()
                    if value > 0
                }
            ):
                self._abort("UNVERIFIED_CONSTRUCTION_COMPLETION")
                _fail("V4 segment lacks an exact finished construction replay")
            self._mode = None
            event_ids = tuple(row.event_id for row in self._events)
            self._terminal = OwnedRouteSegmentTerminalV4(
                _ISSUER,
                self._start.start_id,
                RouteSegmentTerminalKindV4.COMPLETED,
                event_ids,
                self._predecessor(),
                None,
            )
            return self.transcript

    def _abort(self, reason: str) -> None:
        with self._lock:
            if self._terminal is not None:
                return
            self._mode = None
            event_ids = tuple(row.event_id for row in self._events)
            self._terminal = OwnedRouteSegmentTerminalV4(
                _ISSUER,
                self._start.start_id,
                RouteSegmentTerminalKindV4.ABORTED,
                event_ids,
                self._predecessor(),
                reason,
            )

    def abort(
        self, reason: str = "CALLER_REQUESTED_ABORT"
    ) -> OwnedRouteSegmentTranscriptV4:
        self._check_thread()
        if type(reason) is not str or not reason:
            _fail("abort reason must be nonempty")
        self._abort(reason)
        return self.transcript


_FROZEN_ROUTE_NODE_GLOBALS_V4 = globals()
_FROZEN_ROUTE_NODE_CODES_V4 = MappingProxyType(
    {
        "START": OwnedFallbackRouteSegmentSessionV4.__init__.__code__,
        "EVENT": OwnedFallbackRouteSegmentSessionV4._record.__code__,
        "TERMINAL": (
            OwnedFallbackRouteSegmentSessionV4.complete.__code__,
            OwnedFallbackRouteSegmentSessionV4._abort.__code__,
        ),
        "TRANSCRIPT": OwnedFallbackRouteSegmentSessionV4.transcript.fget.__code__,
    }
)


OWNED_ROUTE_EVENT_ACK_V4 = object()
_ACTIVE_ROUTE_SEGMENT_V4: ContextVar[OwnedFallbackRouteSegmentSessionV4 | None] = (
    ContextVar("acfqp_owned_fallback_route_runtime_v4", default=None)
)


@contextmanager
def activate_construction_route_segment_v4(
    session: OwnedFallbackRouteSegmentSessionV4,
) -> Iterator[OwnedFallbackRouteSegmentSessionV4]:
    if type(session) is not OwnedFallbackRouteSegmentSessionV4:
        _fail("V4 construction activation requires the exact session")
    session._check_thread()
    if _ACTIVE_ROUTE_SEGMENT_V4.get() is not None:
        _fail("nested V4 route segments are forbidden")
    session.enter_construction_harness()
    token: Token[Any] = _ACTIVE_ROUTE_SEGMENT_V4.set(session)
    try:
        yield session
    except BaseException:
        if not session.is_terminal:
            session._abort("ACTIVE_SCOPE_EXCEPTION")
        raise
    else:
        if not session.is_terminal:
            session._abort("INCOMPLETE_SCOPE_EXIT")
            _fail("V4 construction scope exited without terminalization")
    finally:
        _ACTIVE_ROUTE_SEGMENT_V4.reset(token)


@contextmanager
def activate_owned_route_segment_v4(
    session: OwnedFallbackRouteSegmentSessionV4,
) -> Iterator[OwnedFallbackRouteSegmentSessionV4]:
    """Future runtime entry; current sealed V3 owner deterministically blocks."""

    if type(session) is not OwnedFallbackRouteSegmentSessionV4:
        _fail("V4 owned activation requires the exact session")
    session._check_thread()
    if _ACTIVE_ROUTE_SEGMENT_V4.get() is not None:
        _fail("nested V4 route segments are forbidden")
    session.enter_owned_runtime()
    token: Token[Any] = _ACTIVE_ROUTE_SEGMENT_V4.set(session)
    try:
        yield session
    except BaseException:
        if not session.is_terminal:
            session._abort("ACTIVE_SCOPE_EXCEPTION")
        raise
    finally:
        _ACTIVE_ROUTE_SEGMENT_V4.reset(token)


def emit_verified_construction_operation_v4(
    dispatch_key: Any, amount: Any = 1
) -> object:
    session = _ACTIVE_ROUTE_SEGMENT_V4.get()
    if session is None:
        _fail("V4 construction event requires an active harness")
    return session._record(
        dispatch_key,
        amount,
        origin=RouteOperationOriginV4.CONSTRUCTION_VERIFIED_SOURCE_REPLAY,
    )


def emit_owned_route_operation_v4(dispatch_key: Any, amount: Any = 1) -> object:
    """Gateway reserved for a successor sealed-source owned engine."""

    session = _ACTIVE_ROUTE_SEGMENT_V4.get()
    if session is None:
        _fail("V4 source-owned event requires an active owned runtime")
    try:
        caller = __import__("sys")._getframe(1)  # noqa: SLF001
    except (AttributeError, ValueError) as error:
        session._abort("CALLER_FRAME_UNAVAILABLE")
        raise ConstructionAccountingRouteSegmentV4Error(
            "V4 source-owner frame is unavailable"
        ) from error
    return session._record(
        dispatch_key,
        amount,
        origin=RouteOperationOriginV4.SOURCE_OWNED_RUNTIME,
        caller_module=caller.f_globals.get("__name__"),
        caller_qualname=getattr(caller.f_code, "co_qualname", caller.f_code.co_name),
    )


__all__ = (
    "CONSTRUCTION_ONLY",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionAccountingRouteSegmentV4Error",
    "EXPECTED_BOUNDARY_COUNT",
    "EXPECTED_BOUNDARY_MANIFEST_DOCUMENT_SHA256",
    "EXPECTED_BOUNDARY_MANIFEST_ID",
    "EXPECTED_SOURCE_BYTE_COUNT",
    "EXPECTED_SOURCE_SHA256",
    "LEGACY_OWNER_GATEWAY",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OWNED_ROUTE_EVENT_ACK_V4",
    "OwnedFallbackRouteSegmentSessionV4",
    "OwnedRouteOperationEventV4",
    "OwnedRouteSegmentStartV4",
    "OwnedRouteSegmentTerminalV4",
    "OwnedRouteSegmentTranscriptV4",
    "OwnerRuntimeIntegrationBlockedV4",
    "OwnerRuntimeIntegrationBlockerV4",
    "PRODUCTION_CLOSURE_CLAIMED",
    "PRODUCTION_OWNER_SOURCE_INTEGRATED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUIRED_CONTRACT_VERSION",
    "REQUIRED_OWNER_GATEWAY",
    "RouteOperationOriginV4",
    "RouteSegmentTerminalKindV4",
    "SCHEMA_VERSION",
    "SOURCE_MODULE",
    "SOURCE_RELATIVE_PATH",
    "SealedSourceMemberAuthorityV4",
    "VerifiedOperationBoundaryManifestAuthorityV4",
    "VerifiedOperationBoundaryV4",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "activate_construction_route_segment_v4",
    "activate_owned_route_segment_v4",
    "emit_owned_route_operation_v4",
    "emit_verified_construction_operation_v4",
    "verify_sealed_operation_boundary_authority_v4",
)
