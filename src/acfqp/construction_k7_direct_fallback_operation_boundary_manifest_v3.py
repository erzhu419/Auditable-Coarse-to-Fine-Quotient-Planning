"""Exact seven-site manifest for the real owned fallback ledger.

Unlike the V2 construction shim, this manifest binds the literal unit calls in
``_OwnedFallbackLedgerV2`` itself.  It freezes complete source bytes, method
ASTs, call ASTs and call locations.  The manifest remains construction-only:
it does not by itself prove that a route was selected or issue V6 records.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
import hashlib
import marshal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_direct_fallback_operation_boundary_manifest_v2 as parent_v2
from acfqp import phase3e_fallback_owned_v2 as owned_v2
from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "3.0.0"
PROFILE_KEY = "construction_k7_direct_fallback_operation_boundary_manifest_v3"
SOURCE_MODULE = "acfqp.phase3e_fallback_owned_v2"
SOURCE_RELATIVE_PATH = "phase3e_fallback_owned_v2.py"
HOOK_SYMBOL = "emit_owned_route_operation_v3"
EXPECTED_BOUNDARY_COUNT = 7
EXPECTED_SOURCE_MEMBER_COUNT = 1
CONSTRUCTION_ONLY = True
PRODUCTION_SOURCE_INTEGRATED = True
PRODUCTION_CLOSURE_CLAIMED = False

EXPECTED_PARENT_V2_MANIFEST_ID = (
    "2aec008f25248f65755983ebebb06e15df04bd45677dc2892e01ad975c1df874"
)
EXPECTED_PARENT_V2_MANIFEST_DOCUMENT_SHA256 = (
    "a8dcc09841287966d4120804e0fdeca32e7913561325700adaa9b85f885a5700"
)

_SOURCE_BYTE_COUNT = 24965
_SOURCE_SHA256 = "ed1b6f6dbc186552f33363da55f6fbeb1727f84f1b598d15939c63cbba0ce3b4"

_BOUNDARY_DOMAIN = "acfqp:construction-k7-direct-fallback-operation-boundary:v3"
_MANIFEST_DOMAIN = "acfqp:construction-k7-direct-fallback-operation-manifest:v3"
_ARCHIVE_DOMAIN = "acfqp:construction-k7-direct-fallback-source-archive:v3"
_REPLAY_DOMAIN = "acfqp:construction-k7-direct-fallback-source-replay:v3"
_BLOCKER_DOMAIN = "acfqp:construction-k7-direct-fallback-source-blocker:v3"
_LIVE_BINDING_DOMAIN = "acfqp:construction-k7-direct-fallback-live-binding:v3"
_ISSUER = object()

_FROZEN_OWNER_BINDING_VALIDATOR_V3 = (
    owned_v2.require_frozen_owned_fallback_source_binding_v2
)
_FROZEN_OWNER_BINDING_VALIDATOR_GLOBALS_V3 = (
    _FROZEN_OWNER_BINDING_VALIDATOR_V3.__globals__
)
_FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3 = (
    _FROZEN_OWNER_BINDING_VALIDATOR_V3.__code__
)
_FROZEN_OWNER_BINDING_V3 = _FROZEN_OWNER_BINDING_VALIDATOR_V3()
_FROZEN_OWNER_METHOD_CODE_SHA256_V3 = tuple(
    (name, hashlib.sha256(marshal.dumps(code)).hexdigest())
    for name, _function, code in _FROZEN_OWNER_BINDING_V3.method_bindings
)
_FROZEN_OWNER_GATEWAY_CODE_SHA256_V3 = hashlib.sha256(
    marshal.dumps(_FROZEN_OWNER_BINDING_V3.gateway_code)
).hexdigest()


class ConstructionK7DirectFallbackOperationBoundaryManifestV3Error(ValueError):
    """The real owner source or its exact seven-site inventory changed."""


class DirectFallbackBoundaryReplayOutcomeV3(str, Enum):
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DirectFallbackOperationBoundaryManifestV3Error(message)


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
        raise ConstructionK7DirectFallbackOperationBoundaryManifestV3Error(
            f"{label} must be one full content ID"
        ) from error


@dataclass(frozen=True, slots=True, order=True)
class DirectFallbackBoundaryBlockerV3:
    code: str
    site_key: str
    detail: str

    def __post_init__(self) -> None:
        if not all(type(value) is str and value for value in (self.code, self.site_key, self.detail)):
            _fail("V3 source blocker text is invalid")

    @property
    def blocker_id(self) -> str:
        return _content_id(
            _BLOCKER_DOMAIN,
            {
                "schema": "acfqp.direct_fallback_source_blocker.v3",
                "schema_version": SCHEMA_VERSION,
                "code": self.code,
                "site_key": self.site_key,
                "detail": self.detail,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_fallback_source_blocker.v3",
            "schema_version": SCHEMA_VERSION,
            "code": self.code,
            "site_key": self.site_key,
            "detail": self.detail,
            "blocker_id": self.blocker_id,
        }


@dataclass(frozen=True, slots=True)
class _BoundarySpecV3:
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


_SPECS: tuple[_BoundarySpecV3, ...] = (
    _BoundarySpecV3(
        "direct-fallback.action-evaluated",
        "direct-fallback.action.evaluated",
        "fallback.actions_evaluated",
        "_OwnedFallbackLedgerV2.evaluate_action",
        144, 12, 144, 80,
        "11e4990dfc5776b9c53ead402018284c2d5ef2018b3442e7e306bb8f8a02a11f",
        "cc23a92de3835e953c059b98cb383df431600b517cc5f91413133c958af72d88",
    ),
    _BoundarySpecV3(
        "direct-fallback.bellman-backup",
        "direct-fallback.bellman.backup",
        "fallback.bellman_backups",
        "_OwnedFallbackLedgerV2.compose_candidate",
        209, 12, 209, 78,
        "fe631faa3325f7d5dfd8f6347549da3cf876b0ce2588166e83340321847fd638",
        "aa4e5c964dee8adb61d739b338226208070df6848493514a0b37d25f5c71aabb",
    ),
    _BoundarySpecV3(
        "direct-fallback.cap-check",
        "direct-fallback.control.cap-check",
        "control.cap_checks",
        "_OwnedFallbackLedgerV2._guard",
        92, 12, 94, 13,
        "bc5017c8af6969f85ddc83113334e661cc85c5e9bdf17100034fd47cf648fd32",
        "283d5bda9842d663cb5b1784d529f16be7718a97d2771dc1cf55f4757512a439",
    ),
    _BoundarySpecV3(
        "direct-fallback.cap-rejection",
        "direct-fallback.control.cap-rejection",
        "control.cap_rejections",
        "_OwnedFallbackLedgerV2._reject",
        107, 12, 109, 13,
        "1bca27647c16d0a6479cdb56ae6c63e06a5535307b3f39922a61b573767546ed",
        "99821974b956feef08a12769a15e9bd63d16edb3790366b2bad09461fc496a77",
    ),
    _BoundarySpecV3(
        "direct-fallback.ground-step",
        "direct-fallback.kernel.transition",
        "fallback.ground_steps",
        "_OwnedFallbackLedgerV2.reserve_transition",
        166, 12, 166, 81,
        "5e4250c996997e642c01bdfa42e92a493495e6595ba958487a481ec2ec7a0eb8",
        "9fe895b53bf054c265a2a828c2756c50ef28e0953ec4e8ed4e5057a023a3c075",
    ),
    _BoundarySpecV3(
        "direct-fallback.outcome-row",
        "direct-fallback.outcome.row",
        "fallback.outcome_rows",
        "_OwnedFallbackLedgerV2.record_outcomes",
        181, 16, 181, 79,
        "a29c7f0661eed5725031083d716d50ef9a89d3ae1527bfb56a8465053778b1ef",
        "0a4f860002cc1b736d1c4c5733de65f356eb15cb74496f7e5b689514b58deba1",
    ),
    _BoundarySpecV3(
        "direct-fallback.state-expanded",
        "direct-fallback.state.expanded",
        "fallback.states_expanded",
        "_OwnedFallbackLedgerV2.expand_state",
        127, 12, 127, 78,
        "988fdcc9747bb2366093f065d5cd590af6675dd86f4f56bab5f8adeed6c177ed",
        "f33131c9de961701144dc808dfc0ca03b60f47c18d046baa7c348372ac341407",
    ),
)


@dataclass(frozen=True, slots=True)
class DirectFallbackOperationBoundaryV3:
    _issuer: object
    boundary_key: str
    dispatch_key: str
    target_path: str
    owner: str
    reducer: ReducerEnum
    operation_source_module: str
    operation_source_symbol: str
    source_sha256: str
    source_byte_count: int
    symbol_ast_sha256: str
    call_ast_sha256: str
    call_lineno: int
    call_col_offset: int
    call_end_lineno: int
    call_end_col_offset: int

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("V3 boundary is caller-minted")
        try:
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackOperationBoundaryManifestV3Error(
                "V3 boundary reducer is invalid"
            ) from error
        if self.reducer is not ReducerEnum.SUM:
            _fail("V3 fallback boundaries must use SUM")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_fallback_operation_boundary.v3",
            "schema_version": SCHEMA_VERSION,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "stage_kind": registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK.value,
            "target_path": self.target_path,
            "owner": self.owner,
            "reducer": self.reducer.value,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "source_sha256": self.source_sha256,
            "source_byte_count": self.source_byte_count,
            "symbol_ast_sha256": self.symbol_ast_sha256,
            "call_ast_sha256": self.call_ast_sha256,
            "call_location": [
                self.call_lineno, self.call_col_offset,
                self.call_end_lineno, self.call_end_col_offset,
            ],
            "literal_dispatch": True,
            "unit_amount": True,
            "real_ledger_primitive_site": True,
            "construction_only": True,
        }

    @property
    def boundary_id(self) -> str:
        return _content_id(_BOUNDARY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "boundary_id": self.boundary_id}


@dataclass(frozen=True, slots=True)
class DirectFallbackOperationBoundaryManifestV3:
    _issuer: object
    counter_registry_id: str
    stage_profile_id: str
    parent_v2_manifest_id: str
    source_archive_id: str
    live_owner_binding_id: str
    boundaries: tuple[DirectFallbackOperationBoundaryV3, ...]
    stage_kind: registry_v6.ConstructionStageKindV6 = (
        registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
    )

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("V3 manifest is caller-minted")
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.parent_v2_manifest_id, "parent V2 manifest"),
            (self.source_archive_id, "source archive"),
            (self.live_owner_binding_id, "live owner binding"),
        ):
            _cid(value, label)
        object.__setattr__(self, "stage_kind", registry_v6.ConstructionStageKindV6(self.stage_kind))
        if (
            self.stage_kind is not registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
            or type(self.boundaries) is not tuple
            or len(self.boundaries) != EXPECTED_BOUNDARY_COUNT
            or tuple(sorted(self.boundaries, key=lambda row: row.boundary_key)) != self.boundaries
            or len({row.dispatch_key for row in self.boundaries}) != EXPECTED_BOUNDARY_COUNT
            or len({row.target_path for row in self.boundaries}) != EXPECTED_BOUNDARY_COUNT
        ):
            _fail("V3 manifest lacks its exact seven-site inventory")

    @property
    def by_dispatch(self) -> Mapping[str, DirectFallbackOperationBoundaryV3]:
        return MappingProxyType({row.dispatch_key: row for row in self.boundaries})

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_fallback_operation_boundary_manifest.v3",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "stage_kind": self.stage_kind.value,
            "parent_v2_manifest_id": self.parent_v2_manifest_id,
            "parent_v2_manifest_document_sha256": EXPECTED_PARENT_V2_MANIFEST_DOCUMENT_SHA256,
            "source_archive_id": self.source_archive_id,
            "live_owner_binding_id": self.live_owner_binding_id,
            "source_members": [{
                "module_name": SOURCE_MODULE,
                "relative_path": SOURCE_RELATIVE_PATH,
                "source_sha256": _SOURCE_SHA256,
                "source_byte_count": _SOURCE_BYTE_COUNT,
            }],
            "boundaries": [row.to_document() for row in self.boundaries],
            "boundary_count": len(self.boundaries),
            "production_source_integrated": True,
            "runtime_evidence_issued": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "construction_only": True,
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


@dataclass(frozen=True, slots=True)
class DirectFallbackBoundaryReplayV3:
    outcome: DirectFallbackBoundaryReplayOutcomeV3
    source_archive_id: str | None
    manifest: DirectFallbackOperationBoundaryManifestV3 | None
    blockers: tuple[DirectFallbackBoundaryBlockerV3, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(
                self, "outcome", DirectFallbackBoundaryReplayOutcomeV3(self.outcome)
            )
            if self.source_archive_id is not None:
                _cid(self.source_archive_id, "source archive")
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackOperationBoundaryManifestV3Error(
                "V3 source replay identity is invalid"
            ) from error
        if (
            type(self.blockers) is not tuple
            or tuple(sorted(set(self.blockers))) != self.blockers
            or (
                self.outcome is DirectFallbackBoundaryReplayOutcomeV3.VERIFIED
                and (self.manifest is None or self.blockers)
            )
            or (
                self.outcome is DirectFallbackBoundaryReplayOutcomeV3.BLOCKED
                and (self.manifest is not None or not self.blockers)
            )
        ):
            _fail("V3 source replay outcome is inconsistent")

    @property
    def replay_id(self) -> str:
        return _content_id(
            _REPLAY_DOMAIN,
            {
                "schema": "acfqp.direct_fallback_source_replay.v3",
                "schema_version": SCHEMA_VERSION,
                "outcome": self.outcome.value,
                "source_archive_id": self.source_archive_id,
                "manifest_id": None if self.manifest is None else self.manifest.manifest_id,
                "blocker_ids": [row.blocker_id for row in self.blockers],
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.direct_fallback_source_replay.v3",
            "schema_version": SCHEMA_VERSION,
            "outcome": self.outcome.value,
            "source_archive_id": self.source_archive_id,
            "manifest_id": None if self.manifest is None else self.manifest.manifest_id,
            "blockers": [row.to_document() for row in self.blockers],
            "replay_id": self.replay_id,
        }


def load_direct_fallback_operation_source_archive_v3() -> dict[str, bytes]:
    return {
        SOURCE_MODULE: (Path(__file__).resolve().parent / SOURCE_RELATIVE_PATH).read_bytes()
    }


def _qualified_functions(tree: ast.AST) -> dict[str, ast.FunctionDef]:
    found: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "_OwnedFallbackLedgerV2":
            continue
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                found[f"{node.name}.{child.name}"] = child
    return found


def _call_dispatch(call: ast.Call) -> str | None:
    if not isinstance(call.func, ast.Name) or call.func.id != HOOK_SYMBOL:
        return None
    if len(call.args) != 2 or call.keywords:
        return None
    first, second = call.args
    if (
        not isinstance(first, ast.Constant)
        or type(first.value) is not str
        or not isinstance(second, ast.Constant)
        or type(second.value) is not int
        or second.value != 1
    ):
        return None
    return first.value


def _live_binding_id(
    binding: owned_v2.FrozenOwnedFallbackSourceBindingV2,
) -> str:
    frozen_code_sha = dict(_FROZEN_OWNER_METHOD_CODE_SHA256_V3)
    return _content_id(
        _LIVE_BINDING_DOMAIN,
        {
            "schema": "acfqp.direct_fallback_live_owner_binding.v3",
            "schema_version": SCHEMA_VERSION,
            "owner_class_module": binding.owner_class.__module__,
            "owner_class_qualname": binding.owner_class.__qualname__,
            "owner_module_name": binding.owner_globals.get("__name__"),
            "owner_module_file": str(Path(binding.owner_globals["__file__"]).resolve()),
            "methods": [
                {
                    "name": name,
                    "module": function.__module__,
                    "qualname": function.__qualname__,
                    "code_sha256": frozen_code_sha[name],
                    "code_firstlineno": code.co_firstlineno,
                    "code_filename": str(Path(code.co_filename).resolve()),
                }
                for name, function, code in binding.method_bindings
            ],
            "gateway_module": binding.gateway.__module__,
            "gateway_qualname": binding.gateway.__qualname__,
            "gateway_code_sha256": _FROZEN_OWNER_GATEWAY_CODE_SHA256_V3,
            "gateway_code_firstlineno": binding.gateway_code.co_firstlineno,
            "gateway_code_filename": str(
                Path(binding.gateway_code.co_filename).resolve()
            ),
            "identity_checked_at_replay": True,
        },
    )


def _is_import_time_binding(
    binding: owned_v2.FrozenOwnedFallbackSourceBindingV2,
) -> bool:
    return (
        binding.owner_class is _FROZEN_OWNER_BINDING_V3.owner_class
        and binding.owner_globals is _FROZEN_OWNER_BINDING_V3.owner_globals
        and binding.gateway is _FROZEN_OWNER_BINDING_V3.gateway
        and binding.gateway_globals is _FROZEN_OWNER_BINDING_V3.gateway_globals
        and binding.gateway_code is _FROZEN_OWNER_BINDING_V3.gateway_code
        and len(binding.method_bindings)
        == len(_FROZEN_OWNER_BINDING_V3.method_bindings)
        and all(
            left_name == right_name
            and left_function is right_function
            and left_code is right_code
            for (left_name, left_function, left_code), (
                right_name,
                right_function,
                right_code,
            ) in zip(
                binding.method_bindings,
                _FROZEN_OWNER_BINDING_V3.method_bindings,
            )
        )
    )


def replay_direct_fallback_operation_source_archive_v3(
    source_archive: Mapping[str, bytes],
) -> DirectFallbackBoundaryReplayV3:
    blockers: list[DirectFallbackBoundaryBlockerV3] = []

    def block(code: str, site: str, detail: str) -> None:
        blockers.append(DirectFallbackBoundaryBlockerV3(code, site, detail))

    if not isinstance(source_archive, Mapping) or set(source_archive) != {SOURCE_MODULE}:
        block("SOURCE_MEMBER_SET_CHANGED", "source.archive", "archive must contain exactly the owned fallback module")
    raw = source_archive.get(SOURCE_MODULE) if isinstance(source_archive, Mapping) else None
    if type(raw) is not bytes:
        block("SOURCE_MEMBER_NOT_BYTES", "source.module", "owned fallback source is absent or not bytes")
        return DirectFallbackBoundaryReplayV3(
            DirectFallbackBoundaryReplayOutcomeV3.BLOCKED, None, None,
            tuple(sorted(set(blockers))),
        )
    archive_id = _content_id(
        _ARCHIVE_DOMAIN,
        {
            "schema": "acfqp.direct_fallback_source_archive.v3",
            "schema_version": SCHEMA_VERSION,
            "members": [{
                "module_name": SOURCE_MODULE,
                "source_sha256": _sha256(raw),
                "source_byte_count": len(raw),
            }],
        },
    )
    try:
        tree = ast.parse(raw, filename=SOURCE_RELATIVE_PATH)
    except (SyntaxError, TypeError, ValueError):
        block("SOURCE_SYNTAX_INVALID", "source.module", "owned fallback source is invalid Python")
        return DirectFallbackBoundaryReplayV3(
            DirectFallbackBoundaryReplayOutcomeV3.BLOCKED, archive_id, None,
            tuple(sorted(set(blockers))),
        )
    try:
        if (
            owned_v2.require_frozen_owned_fallback_source_binding_v2
            is not _FROZEN_OWNER_BINDING_VALIDATOR_V3
            or _FROZEN_OWNER_BINDING_VALIDATOR_V3.__globals__
            is not _FROZEN_OWNER_BINDING_VALIDATOR_GLOBALS_V3
            or _FROZEN_OWNER_BINDING_VALIDATOR_V3.__code__
            is not _FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3
        ):
            raise ValueError("owned fallback binding validator was replaced")
        live_binding = _FROZEN_OWNER_BINDING_VALIDATOR_V3()
        if not _is_import_time_binding(live_binding):
            raise ValueError("owned fallback binding differs from manifest import")
        live_binding_id = _live_binding_id(live_binding)
    except (AttributeError, TypeError, ValueError) as error:
        block(
            "LIVE_OWNER_BINDING_CHANGED",
            "owner.runtime",
            f"import-time owned ledger class/method binding changed: {error}",
        )
        live_binding = None
        live_binding_id = None
    functions = _qualified_functions(tree)
    all_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == HOOK_SYMBOL
    ]
    dispatches = [_call_dispatch(call) for call in all_calls]
    expected_dispatches = sorted(row.dispatch_key for row in _SPECS)
    if len(all_calls) != EXPECTED_BOUNDARY_COUNT or sorted(dispatches, key=repr) != expected_dispatches:
        block("HOOK_INVENTORY_CHANGED", "hook.inventory", "literal seven-dispatch inventory changed")

    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    allowed = set(
        stage_profile.by_stage[
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ].allowed_nonzero_paths
    )
    boundaries: list[DirectFallbackOperationBoundaryV3] = []
    live_methods = (
        {}
        if live_binding is None
        else {
            name: (function, code)
            for name, function, code in live_binding.method_bindings
        }
    )
    source_path = (Path(__file__).resolve().parent / SOURCE_RELATIVE_PATH).resolve()
    for spec in _SPECS:
        leaf = registry.by_path.get(spec.target_path)
        symbol = functions.get(spec.operation_source_symbol)
        if leaf is None or spec.target_path not in allowed or leaf.reducer is not ReducerEnum.SUM:
            block("REGISTRY_BINDING_CHANGED", spec.boundary_key, "V6 leaf ownership changed")
            continue
        if symbol is None:
            block("SYMBOL_MISSING", spec.boundary_key, "owned ledger method is missing")
            continue
        method_name = spec.operation_source_symbol.rsplit(".", 1)[-1]
        live_method = live_methods.get(method_name)
        if live_method is None:
            block(
                "LIVE_METHOD_BINDING_MISSING",
                spec.boundary_key,
                "archived owner method lacks its import-time live identity",
            )
            continue
        live_function, live_code = live_method
        if (
            live_function is not getattr(live_binding.owner_class, method_name, None)
            or live_function.__code__ is not live_code
            or live_function.__globals__ is not live_binding.owner_globals
            or Path(live_code.co_filename).resolve() != source_path
            or live_code.co_firstlineno != symbol.lineno
            or live_function.__qualname__ != spec.operation_source_symbol
        ):
            block(
                "LIVE_METHOD_BINDING_CHANGED",
                spec.boundary_key,
                "archived AST is not bound to the import-time live method",
            )
            continue
        symbol_hash = _sha256(ast.dump(symbol, include_attributes=False).encode("utf-8"))
        matching = [call for call in ast.walk(symbol) if isinstance(call, ast.Call) and _call_dispatch(call) == spec.dispatch_key]
        if symbol_hash != spec.symbol_ast_sha256 or len(matching) != 1:
            block("SYMBOL_AST_CHANGED", spec.boundary_key, "owned ledger method AST changed")
            continue
        call = matching[0]
        location = (call.lineno, call.col_offset, call.end_lineno, call.end_col_offset)
        call_hash = _sha256(ast.dump(call, include_attributes=False).encode("utf-8"))
        if location != (
            spec.call_lineno, spec.call_col_offset,
            spec.call_end_lineno, spec.call_end_col_offset,
        ) or call_hash != spec.call_ast_sha256:
            block("CALL_SITE_CHANGED", spec.boundary_key, "literal owner call changed or moved")
            continue
        boundaries.append(
            DirectFallbackOperationBoundaryV3(
                _ISSUER,
                spec.boundary_key,
                spec.dispatch_key,
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
            )
        )
    try:
        parent = parent_v2.freeze_direct_fallback_operation_boundary_manifest_v2()
    except Exception:
        parent = None
    if (
        parent is None
        or parent.manifest_id != EXPECTED_PARENT_V2_MANIFEST_ID
        or _sha256(canonical_json_bytes(parent.to_document()))
        != EXPECTED_PARENT_V2_MANIFEST_DOCUMENT_SHA256
    ):
        block("PARENT_V2_CHANGED", "parent.manifest", "frozen V2 parent changed")
    if len(raw) != _SOURCE_BYTE_COUNT or _sha256(raw) != _SOURCE_SHA256:
        block("SOURCE_BYTES_CHANGED", "source.module", "complete owned fallback source bytes changed")
    if blockers:
        return DirectFallbackBoundaryReplayV3(
            DirectFallbackBoundaryReplayOutcomeV3.BLOCKED,
            archive_id,
            None,
            tuple(sorted(set(blockers))),
        )
    assert parent is not None
    assert live_binding_id is not None
    manifest = DirectFallbackOperationBoundaryManifestV3(
        _ISSUER,
        registry.registry_id,
        stage_profile.stage_profile_id,
        parent.manifest_id,
        archive_id,
        live_binding_id,
        tuple(sorted(boundaries, key=lambda row: row.boundary_key)),
    )
    return DirectFallbackBoundaryReplayV3(
        DirectFallbackBoundaryReplayOutcomeV3.VERIFIED,
        archive_id,
        manifest,
        (),
    )


def freeze_direct_fallback_operation_boundary_manifest_v3() -> DirectFallbackOperationBoundaryManifestV3:
    replay = replay_direct_fallback_operation_source_archive_v3(
        load_direct_fallback_operation_source_archive_v3()
    )
    if replay.manifest is None:
        error = ConstructionK7DirectFallbackOperationBoundaryManifestV3Error(
            "owned fallback V3 source replay is blocked"
        )
        error.blockers = replay.blockers  # type: ignore[attr-defined]
        raise error
    return replay.manifest


def require_frozen_live_owner_binding_v3(
    manifest: DirectFallbackOperationBoundaryManifestV3,
) -> owned_v2.FrozenOwnedFallbackSourceBindingV2:
    """Require the manifest's archived source to retain import-time live IDs."""

    if type(manifest) is not DirectFallbackOperationBoundaryManifestV3:
        _fail("live owner binding requires the exact V3 manifest")
    try:
        if (
            owned_v2.require_frozen_owned_fallback_source_binding_v2
            is not _FROZEN_OWNER_BINDING_VALIDATOR_V3
            or _FROZEN_OWNER_BINDING_VALIDATOR_V3.__globals__
            is not _FROZEN_OWNER_BINDING_VALIDATOR_GLOBALS_V3
            or _FROZEN_OWNER_BINDING_VALIDATOR_V3.__code__
            is not _FROZEN_OWNER_BINDING_VALIDATOR_CODE_V3
        ):
            raise ValueError("owned fallback binding validator was replaced")
        binding = _FROZEN_OWNER_BINDING_VALIDATOR_V3()
    except (AttributeError, TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackOperationBoundaryManifestV3Error(
            "owned fallback import-time live binding changed"
        ) from error
    if (
        not _is_import_time_binding(binding)
        or _live_binding_id(binding) != manifest.live_owner_binding_id
    ):
        _fail("owned fallback live binding ID differs from the V3 manifest")
    return binding


_FROZEN_LIVE_OWNER_VALIDATOR_OBJECT_V3 = require_frozen_live_owner_binding_v3
_FROZEN_LIVE_OWNER_VALIDATOR_GLOBALS_V3 = (
    require_frozen_live_owner_binding_v3.__globals__
)
_FROZEN_LIVE_OWNER_VALIDATOR_CODE_V3 = require_frozen_live_owner_binding_v3.__code__


def verify_direct_fallback_operation_boundary_manifest_document_v3(
    document: Mapping[str, Any],
    source_archive: Mapping[str, bytes],
) -> DirectFallbackBoundaryReplayV3:
    replay = replay_direct_fallback_operation_source_archive_v3(source_archive)
    if replay.manifest is None:
        return replay
    if type(document) is not dict or canonical_json_bytes(document) != canonical_json_bytes(replay.manifest.to_document()):
        blocker = DirectFallbackBoundaryBlockerV3(
            "MANIFEST_DOCUMENT_CHANGED",
            "manifest.document",
            "supplied V3 manifest differs from exact source replay",
        )
        return DirectFallbackBoundaryReplayV3(
            DirectFallbackBoundaryReplayOutcomeV3.BLOCKED,
            replay.source_archive_id,
            None,
            (blocker,),
        )
    return replay


__all__ = (
    "CONSTRUCTION_ONLY",
    "ConstructionK7DirectFallbackOperationBoundaryManifestV3Error",
    "DirectFallbackBoundaryBlockerV3",
    "DirectFallbackBoundaryReplayOutcomeV3",
    "DirectFallbackBoundaryReplayV3",
    "DirectFallbackOperationBoundaryManifestV3",
    "DirectFallbackOperationBoundaryV3",
    "EXPECTED_BOUNDARY_COUNT",
    "EXPECTED_PARENT_V2_MANIFEST_DOCUMENT_SHA256",
    "EXPECTED_PARENT_V2_MANIFEST_ID",
    "EXPECTED_SOURCE_MEMBER_COUNT",
    "HOOK_SYMBOL",
    "PRODUCTION_CLOSURE_CLAIMED",
    "PRODUCTION_SOURCE_INTEGRATED",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SOURCE_MODULE",
    "SOURCE_RELATIVE_PATH",
    "freeze_direct_fallback_operation_boundary_manifest_v3",
    "load_direct_fallback_operation_source_archive_v3",
    "require_frozen_live_owner_binding_v3",
    "replay_direct_fallback_operation_source_archive_v3",
    "verify_direct_fallback_operation_boundary_manifest_document_v3",
)
