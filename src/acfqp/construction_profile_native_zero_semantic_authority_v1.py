"""Exact semantic authority for the 114 K7 profile-native-zero paths.

This module turns the schema-only rules in
``construction_profile_native_zero_rules_v1`` into positive, replayable zero
attestations.  A missing runtime event is never evidence.  Issuance requires
the independently replayed production occurrence/cutoff authority, the exact
89-site/71-path owner-window closure, the exact nine shared-resource context,
the real broker runtime/request identity, and the frozen source archive bytes.

The archive is scanned for *every* call to the sole production accounting
gateway.  The resulting inventory must equal the registered 89-site hook
inventory exactly.  Consequently an executed-stage zero is justified by a
closed owner window plus the absence of any source-level emission capability,
not by the absence of an event in a log.  Legacy replacements are resolved in
dependency order against an owner-path candidate or an earlier zero
attestation.  This layer still issues no CounterRecord or formal vector.
"""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import InitVar, dataclass, field
import hashlib
import io
from typing import Any, Mapping, NoReturn
import zipfile

from acfqp import construction_accounting_owner_event_candidates_v1 as owner_v1
from acfqp import construction_accounting_partial_native_v1 as partial_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
from acfqp import construction_profile_native_zero_rules_v1 as rules_v1
from acfqp import construction_shared_resource_verified_envelope_v1 as verified_v1
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_k7_production_broker_runtime_v2 as runtime_v2
from acfqp import v075_k7_production_role_manifest_v2 as role_manifest_v2
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3
from acfqp import v075_k7_successor_portable_replay_v1 as replay_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_NATIVE_ZERO_BRANCH_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_NATIVE_ZERO_OWNER_WINDOW_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_NATIVE_ZERO_REPLACEMENT_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_NATIVE_ZERO_SEMANTIC_VERIFIER_V1_DOMAIN,
    CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_HOOK_INVENTORY_V1_DOMAIN,
    CONSTRUCTION_K7_NATIVE_ZERO_STAGE_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_PROFILE_NATIVE_ZERO_ATTESTATION_V1_DOMAIN,
    CONSTRUCTION_K7_PROFILE_NATIVE_ZERO_ENVELOPE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.27"
PROFILE_KEY = "construction_profile_native_zero_semantic_authority_v1"
EXPECTED_ZERO_PATH_COUNT = 114
EXPECTED_OWNER_SITE_COUNT = 89
EXPECTED_OWNER_PATH_COUNT = 71
EXPECTED_GATEWAY_CALL_COUNT = 59
EXPECTED_OCCURRENCE_START_COUNT = 1
EXPECTED_STAGE_START_COUNT = len(partial_v1.ROOT_CAP_FIVE_STAGE_PLAN_V1)
EXPECTED_STAGE_COMPLETION_COUNT = len(partial_v1.ROOT_CAP_FIVE_STAGE_PLAN_V1)
EXPECTED_TERMINAL_CHAIN_NODE_COUNT = 1
EXPECTED_NON_EVENT_CHAIN_NODE_COUNT = (
    EXPECTED_STAGE_START_COUNT
    + EXPECTED_STAGE_COMPLETION_COUNT
    + EXPECTED_TERMINAL_CHAIN_NODE_COUNT
)

SOURCE_HOOK_INVENTORY_DOMAIN = CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_HOOK_INVENTORY_V1_DOMAIN
OWNER_WINDOW_CLOSURE_DOMAIN = CONSTRUCTION_K7_NATIVE_ZERO_OWNER_WINDOW_CLOSURE_V1_DOMAIN
STAGE_EVIDENCE_DOMAIN = CONSTRUCTION_K7_NATIVE_ZERO_STAGE_EVIDENCE_V1_DOMAIN
BRANCH_EVIDENCE_DOMAIN = CONSTRUCTION_K7_NATIVE_ZERO_BRANCH_EVIDENCE_V1_DOMAIN
REPLACEMENT_EVIDENCE_DOMAIN = CONSTRUCTION_K7_NATIVE_ZERO_REPLACEMENT_EVIDENCE_V1_DOMAIN
ZERO_VERIFIER_DOMAIN = CONSTRUCTION_K7_NATIVE_ZERO_SEMANTIC_VERIFIER_V1_DOMAIN
ZERO_ATTESTATION_DOMAIN = CONSTRUCTION_K7_PROFILE_NATIVE_ZERO_ATTESTATION_V1_DOMAIN
ZERO_ENVELOPE_DOMAIN = CONSTRUCTION_K7_PROFILE_NATIVE_ZERO_ENVELOPE_V1_DOMAIN

LOCAL_DOMAINS = frozenset(
    {
        SOURCE_HOOK_INVENTORY_DOMAIN,
        OWNER_WINDOW_CLOSURE_DOMAIN,
        STAGE_EVIDENCE_DOMAIN,
        BRANCH_EVIDENCE_DOMAIN,
        REPLACEMENT_EVIDENCE_DOMAIN,
        ZERO_VERIFIER_DOMAIN,
        ZERO_ATTESTATION_DOMAIN,
        ZERO_ENVELOPE_DOMAIN,
    }
)
if not LOCAL_DOMAINS.issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("K7 profile-native-zero domains must be centrally registered")

_ATTESTATION_ISSUER = object()
_ENVELOPE_ISSUER = object()


class ConstructionProfileNativeZeroSemanticAuthorityV1Error(ValueError):
    """A zero proof was incomplete, crossed, cyclic, or source-stale."""


def _fail(message: str) -> NoReturn:
    raise ConstructionProfileNativeZeroSemanticAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionProfileNativeZeroSemanticAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("native-zero authority used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


class _GatewayVisitor(ast.NodeVisitor):
    """Collect literal calls to the only production accounting gateway."""

    def __init__(self, module: str) -> None:
        self.module = module
        self.qualname: list[str] = []
        self.calls: list[tuple[str, str, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.qualname.append(node.name)
        self.generic_visit(node)
        self.qualname.pop()

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.qualname.append(node.name)
        self.generic_visit(node)
        self.qualname.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._function(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Attribute) and node.func.attr == "emit_owned_operation_v1":
            if (
                not node.args
                or not isinstance(node.args[0], ast.Constant)
                or type(node.args[0].value) is not str
                or not self.qualname
            ):
                _fail("source archive contains a dynamic accounting gateway call")
            self.calls.append(
                (self.module, ".".join(self.qualname), node.args[0].value)
            )
        self.generic_visit(node)


def _expected_gateway_inventory() -> Counter[tuple[str, str, str]]:
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    rows = tuple(
        row
        for row in manifest.boundaries
        if row.to_document()["emittable_in_this_fixture"] is True
    )
    expected = Counter(
        (
            row.operation_source_module,
            row.operation_source_symbol,
            row.dispatch_key,
        )
        for row in rows
    )
    # Some stage-neutral semantic sites have two distinct source expressions.
    return Counter(
        {
            key: 2 if key in owner_v1._DUPLICATED_SOURCE_HOOKS else 1  # noqa: SLF001
            for key in expected
        }
    )


def _scan_source_hook_inventory(
    *, source_archive_raw: bytes, execution_binding: owner_v1.OwnerEventExecutionBindingV1
) -> tuple[str, tuple[dict[str, Any], ...]]:
    if (
        type(source_archive_raw) is not bytes
        or not source_archive_raw
        or hashlib.sha256(source_archive_raw).hexdigest()
        != execution_binding.source_archive_sha256
        or len(source_archive_raw) != execution_binding.source_archive_byte_count
    ):
        _fail("source archive bytes crossed their exact execution binding")

    # Re-run the existing loaded-source, 89-site and bootstrap-control closure.
    # Its return value is not trusted as a zero: the global gateway scan below
    # independently proves that no unregistered emission capability exists.
    try:
        owner_v1._source_closure(  # noqa: SLF001
            archive_raw=source_archive_raw,
            binding=execution_binding,
        )
    except Exception as error:
        raise ConstructionProfileNativeZeroSemanticAuthorityV1Error(
            "loaded source/owner/control-flow closure failed"
        ) from error

    observed: Counter[tuple[str, str, str]] = Counter()
    member_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        with zipfile.ZipFile(io.BytesIO(source_archive_raw), "r") as archive:
            infos = archive.infolist()
            for info in infos:
                if (
                    info.filename in seen
                    or info.filename.startswith("/")
                    or ".." in info.filename.split("/")
                    or not info.filename.startswith("acfqp/")
                    or not info.filename.endswith(".py")
                    or info.compress_type != zipfile.ZIP_STORED
                    or info.date_time != (1980, 1, 1, 0, 0, 0)
                ):
                    _fail("source archive member is duplicated or noncanonical")
                seen.add(info.filename)
                raw = archive.read(info)
                # Parsing only possible gateway-bearing members keeps replay
                # exact while avoiding a full AST walk over the 20+ MiB tree.
                if b"emit_owned_operation_v1" not in raw:
                    continue
                module = info.filename[:-3].replace("/", ".")
                try:
                    tree = ast.parse(raw, filename=info.filename)
                except (SyntaxError, ValueError) as error:
                    raise ConstructionProfileNativeZeroSemanticAuthorityV1Error(
                        "accounting gateway source cannot be parsed"
                    ) from error
                visitor = _GatewayVisitor(module)
                visitor.visit(tree)
                observed.update(visitor.calls)
                member_rows.append(
                    {
                        "module": module,
                        "source_sha256": hashlib.sha256(raw).hexdigest(),
                        "source_byte_count": len(raw),
                        "gateway_calls": [
                            {"symbol": symbol, "dispatch_key": dispatch}
                            for _module, symbol, dispatch in visitor.calls
                        ],
                    }
                )
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise ConstructionProfileNativeZeroSemanticAuthorityV1Error(
            "source archive is unreadable"
        ) from error

    expected = _expected_gateway_inventory()
    if observed != expected or sum(observed.values()) != EXPECTED_GATEWAY_CALL_COUNT:
        _fail("global loaded-source accounting gateway inventory changed")
    rows = tuple(sorted(member_rows, key=lambda row: row["module"]))
    payload = {
        "schema": "acfqp.construction_k7_native_zero_source_hook_inventory.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_snapshot_id": execution_binding.source_snapshot_id,
        "source_archive_sha256": execution_binding.source_archive_sha256,
        "source_archive_byte_count": execution_binding.source_archive_byte_count,
        "gateway_call_count": sum(observed.values()),
        "distinct_gateway_binding_count": len(observed),
        "gateway_members": list(rows),
        "all_archive_python_members_scanned_for_gateway": True,
        "dynamic_gateway_calls_forbidden": True,
        "gateway_inventory_equals_exact_emittable_manifest": True,
        "event_absence_used_as_zero_evidence": False,
    }
    return _local_id(SOURCE_HOOK_INVENTORY_DOMAIN, payload), rows


def _topological_order(
    dependencies: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Return dependencies before dependents; reject missing nodes and cycles."""

    if type(dependencies) is not dict or not dependencies:
        _fail("native-zero dependency graph is missing")
    nodes = set(dependencies)
    state: dict[str, int] = {}
    result: list[str] = []

    def visit(path: str) -> None:
        marker = state.get(path, 0)
        if marker == 1:
            _fail("native-zero replacement dependency cycle detected")
        if marker == 2:
            return
        if path not in nodes:
            _fail("native-zero replacement dependency names a missing node")
        state[path] = 1
        for dependency in dependencies[path]:
            if dependency in nodes:
                visit(dependency)
        state[path] = 2
        result.append(path)

    for path in sorted(nodes):
        visit(path)
    if len(result) != len(nodes) or len(set(result)) != len(nodes):
        _fail("native-zero dependency order is incomplete or duplicated")
    return tuple(result)


@dataclass(frozen=True, slots=True)
class NativeZeroReplacementResolutionV1:
    replacement_path: str
    resolution_kind: str
    resolution_evidence_id: str
    resolved_value: int
    dependency_attestation_rank: int | None
    resolution_id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.resolution_kind not in {
            "OWNER_PATH_COUNTER_CANDIDATE",
            "PROFILE_NATIVE_ZERO_ATTESTATION",
        }:
            _fail("native-zero replacement resolution kind is invalid")
        _cid(self.resolution_evidence_id, "replacement resolution evidence")
        if type(self.resolved_value) is not int or self.resolved_value < 0:
            _fail("replacement resolution value is invalid")
        if self.resolution_kind == "PROFILE_NATIVE_ZERO_ATTESTATION":
            if (
                self.resolved_value != 0
                or type(self.dependency_attestation_rank) is not int
                or self.dependency_attestation_rank < 0
            ):
                _fail("zero replacement lacks an earlier zero attestation")
        elif self.dependency_attestation_rank is not None:
            _fail("owner-candidate replacement has a spurious dependency rank")
        object.__setattr__(
            self,
            "resolution_id",
            _local_id(REPLACEMENT_EVIDENCE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_native_zero_replacement_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "replacement_path": self.replacement_path,
            "resolution_kind": self.resolution_kind,
            "resolution_evidence_id": self.resolution_evidence_id,
            "resolved_value": self.resolved_value,
            "dependency_attestation_rank": self.dependency_attestation_rank,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replacement_resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class NativeZeroObligationEvidenceV1:
    kind: str
    obligation_key: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not str
            or type(self.obligation_key) is not str
            or not self.obligation_key
            or type(self.evidence_ids) is not tuple
            or not self.evidence_ids
            or tuple(sorted(set(self.evidence_ids))) != self.evidence_ids
        ):
            _fail("native-zero obligation evidence is missing or duplicated")
        for value in self.evidence_ids:
            _cid(value, "native-zero obligation evidence")

    def to_document(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "obligation_key": self.obligation_key,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class K7ProfileNativeZeroAttestationV1:
    _issuer: InitVar[object]
    rule_id: str
    rule_registry_id: str
    path: str
    semantics_id: str
    owner: str
    unit: str
    scope: str
    reducer: str
    reason_code: str
    value: int
    issuance_rank: int
    occurrence_authority_id: str
    cutoff_authority_id: str
    verified_nine_envelope_id: str
    owner_candidate_set_id: str
    source_hook_inventory_id: str
    owner_window_closure_id: str
    stage_evidence_id: str
    branch_nonexecution_evidence_id: str
    zero_semantic_verifier_id: str
    replacements: tuple[NativeZeroReplacementResolutionV1, ...]
    obligations: tuple[NativeZeroObligationEvidenceV1, ...]
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("profile-native-zero attestation is caller-minted")
        for value, label in (
            (self.rule_id, "zero rule"),
            (self.rule_registry_id, "zero rule registry"),
            (self.occurrence_authority_id, "occurrence authority"),
            (self.cutoff_authority_id, "cutoff authority"),
            (self.verified_nine_envelope_id, "verified-nine envelope"),
            (self.owner_candidate_set_id, "owner candidate set"),
            (self.source_hook_inventory_id, "source hook inventory"),
            (self.owner_window_closure_id, "owner-window closure"),
            (self.stage_evidence_id, "stage evidence"),
            (self.branch_nonexecution_evidence_id, "branch evidence"),
            (self.zero_semantic_verifier_id, "zero verifier"),
        ):
            _cid(value, label)
        if (
            self.value != 0
            or type(self.issuance_rank) is not int
            or self.issuance_rank < 0
            or type(self.replacements) is not tuple
            or tuple(row.replacement_path for row in self.replacements)
            != tuple(sorted(row.replacement_path for row in self.replacements))
            or len({row.replacement_path for row in self.replacements})
            != len(self.replacements)
            or type(self.obligations) is not tuple
            or tuple(row.obligation_key for row in self.obligations)
            != tuple(sorted(row.obligation_key for row in self.obligations))
            or len({row.obligation_key for row in self.obligations})
            != len(self.obligations)
        ):
            _fail("profile-native-zero attestation is incomplete or duplicated")
        object.__setattr__(
            self,
            "_attestation_id",
            _local_id(ZERO_ATTESTATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_profile_native_zero_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "rule_id": self.rule_id,
            "rule_registry_id": self.rule_registry_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "scope": self.scope,
            "reducer": self.reducer,
            "reason_code": self.reason_code,
            "value": self.value,
            "observed": True,
            "issuance_rank": self.issuance_rank,
            "occurrence_authority_id": self.occurrence_authority_id,
            "cutoff_authority_id": self.cutoff_authority_id,
            "verified_nine_envelope_id": self.verified_nine_envelope_id,
            "owner_candidate_set_id": self.owner_candidate_set_id,
            "source_hook_inventory_id": self.source_hook_inventory_id,
            "owner_window_closure_id": self.owner_window_closure_id,
            "stage_evidence_id": self.stage_evidence_id,
            "branch_nonexecution_evidence_id": self.branch_nonexecution_evidence_id,
            "zero_semantic_verifier_id": self.zero_semantic_verifier_id,
            "replacement_resolutions": [row.to_document() for row in self.replacements],
            "obligation_evidence": [row.to_document() for row in self.obligations],
            "event_absence_used_as_zero_evidence": False,
            "counter_record_issued": False,
            "formal_vector_authorized": False,
        }

    @property
    def attestation_id(self) -> str:
        if _local_id(ZERO_ATTESTATION_DOMAIN, self._payload()) != self._attestation_id:
            _fail("profile-native-zero attestation changed after issuance")
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_native_zero_attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class K7ProfileNativeZeroEnvelopeV1:
    _issuer: InitVar[object]
    rule_registry_id: str
    counter_registry_id: str
    stage_profile_id: str
    boundary_manifest_id: str
    execution_profile_id: str
    occurrence_authority_id: str
    cutoff_authority_id: str
    verified_nine_envelope_id: str
    owner_candidate_set_id: str
    source_hook_inventory_id: str
    owner_window_closure_id: str
    source_archive_sha256: str
    source_archive_byte_count: int
    topological_path_order: tuple[str, ...]
    attestations: tuple[K7ProfileNativeZeroAttestationV1, ...]
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ENVELOPE_ISSUER:
            _fail("profile-native-zero envelope is caller-minted")
        for value, label in (
            (self.rule_registry_id, "zero rule registry"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.boundary_manifest_id, "boundary manifest"),
            (self.execution_profile_id, "execution profile"),
            (self.occurrence_authority_id, "occurrence authority"),
            (self.cutoff_authority_id, "cutoff authority"),
            (self.verified_nine_envelope_id, "verified-nine envelope"),
            (self.owner_candidate_set_id, "owner candidate set"),
            (self.source_hook_inventory_id, "source hook inventory"),
            (self.owner_window_closure_id, "owner-window closure"),
        ):
            _cid(value, label)
        if (
            type(self.source_archive_sha256) is not str
            or len(self.source_archive_sha256) != 64
            or type(self.source_archive_byte_count) is not int
            or self.source_archive_byte_count <= 0
            or type(self.topological_path_order) is not tuple
            or len(self.topological_path_order) != EXPECTED_ZERO_PATH_COUNT
            or len(set(self.topological_path_order)) != EXPECTED_ZERO_PATH_COUNT
            or type(self.attestations) is not tuple
            or len(self.attestations) != EXPECTED_ZERO_PATH_COUNT
            or tuple(row.path for row in self.attestations)
            != tuple(sorted(row.path for row in self.attestations))
            or len({row.attestation_id for row in self.attestations})
            != EXPECTED_ZERO_PATH_COUNT
            or {row.path for row in self.attestations}
            != set(self.topological_path_order)
        ):
            _fail("profile-native-zero envelope is incomplete or duplicated")
        rank = {path: index for index, path in enumerate(self.topological_path_order)}
        if any(row.issuance_rank != rank[row.path] for row in self.attestations):
            _fail("native-zero attestation rank differs from its dependency order")
        for row in self.attestations:
            for replacement in row.replacements:
                if (
                    replacement.resolution_kind == "PROFILE_NATIVE_ZERO_ATTESTATION"
                    and replacement.dependency_attestation_rank >= row.issuance_rank
                ):
                    _fail("native-zero replacement does not precede its dependent")
        object.__setattr__(
            self,
            "_envelope_id",
            _local_id(ZERO_ENVELOPE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_profile_native_zero_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "rule_registry_id": self.rule_registry_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "execution_profile_id": self.execution_profile_id,
            "occurrence_authority_id": self.occurrence_authority_id,
            "cutoff_authority_id": self.cutoff_authority_id,
            "verified_nine_envelope_id": self.verified_nine_envelope_id,
            "owner_candidate_set_id": self.owner_candidate_set_id,
            "source_hook_inventory_id": self.source_hook_inventory_id,
            "owner_window_closure_id": self.owner_window_closure_id,
            "source_archive_sha256": self.source_archive_sha256,
            "source_archive_byte_count": self.source_archive_byte_count,
            "topological_path_order": list(self.topological_path_order),
            "native_zero_path_count": len(self.attestations),
            "native_zero_paths": [row.path for row in self.attestations],
            "native_zero_attestations": [row.to_document() for row in self.attestations],
            "exact_114_path_set": True,
            "absence_is_zero_evidence": False,
            "replacement_dependency_dag_verified": True,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_materialization_allowed": False,
            "official_execution_allowed": False,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "central_domain_registration_pending": False,
        }

    @property
    def envelope_id(self) -> str:
        if _local_id(ZERO_ENVELOPE_DOMAIN, self._payload()) != self._envelope_id:
            _fail("profile-native-zero envelope changed after issuance")
        return self._envelope_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_native_zero_envelope_id": self.envelope_id}


def _validate_joined_context(
    *,
    occurrence_cutoff_authority: Any,
    owner_candidate_set: Any,
    verified_nine_envelope: Any,
    runtime_envelope: Any,
    request_replay: Any,
    role_manifest: Any,
    operational_output_bytes: Any,
    source_archive_raw: Any,
) -> tuple[Any, Any, Any, Any, Any]:
    if (
        type(occurrence_cutoff_authority)
        is not occurrence_v2.K7OccurrenceCutoffSemanticAuthorityBundleV2
        or type(owner_candidate_set) is not owner_v1.OwnerEventCandidateSetV1
        or type(verified_nine_envelope)
        is not verified_v1.K7VerifiedNineSharedResourceEnvelopeV1
        or type(runtime_envelope) is not runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2
        or type(request_replay) is not replay_v1.V075K7SuccessorPortableRequestReplayV1
        or type(role_manifest) is not role_manifest_v2.K7ProductionRoleManifestV2
        or type(operational_output_bytes) is not bytes
        or not operational_output_bytes
        or type(source_archive_raw) is not bytes
    ):
        _fail("native-zero issuance requires exact typed production authorities")
    try:
        occurrence_cutoff_authority.to_document()
        owner_v1.verify_owner_event_candidate_set_v1(owner_candidate_set)
        verified_nine_envelope.to_document()
        runtime_envelope.to_document()
        request_replay.request._assert_current()  # noqa: SLF001
        role_manifest.assert_current()
    except Exception as error:
        raise ConstructionProfileNativeZeroSemanticAuthorityV1Error(
            "one production prerequisite failed semantic replay"
        ) from error

    occurrence = occurrence_cutoff_authority.occurrence_authority
    cutoff = occurrence_cutoff_authority.cutoff_authority
    binding = owner_candidate_set.execution_binding
    source = verified_nine_envelope.source_envelope
    request = request_replay.request
    route = request.route_identity
    transport = request.profile.accounted_profile.transport_profile
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    rules = rules_v1.official_profile_native_zero_rule_registry_v1()
    coverage = rules_v1.official_owner_boundary_coverage_profile_v1()

    # Do not trust the candidate object's shape verifier as semantic closure.
    # Re-open the exact operational output, extract its canonical embedded
    # business bytes, and independently derive the owner authority from the
    # production role manifest/runtime/source archive chain.
    try:
        operational_output = worker_v1.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=operational_output_bytes,
            expected_request_replay=request_replay,
            expected_binding=runtime_envelope.binding,
        )
        business_document = operational_output.to_document()["business_result"]
        business_raw = canonical_json_bytes(business_document)
        expected_owner_candidates = owner_v1.derive_v075_k7_owner_event_candidates_v1(
            role_manifest=role_manifest,
            runtime_envelope=runtime_envelope,
            business_bundle_raw=business_raw,
        )
    except Exception as error:
        raise ConstructionProfileNativeZeroSemanticAuthorityV1Error(
            "production owner-event authority failed independent root replay"
        ) from error

    if (
        occurrence_cutoff_authority.cutoff_authority.occurrence_authority_id
        != occurrence.authority_id
        or occurrence.portable_request_replay_id != request_replay.replay_id
        or occurrence.request_id != request.request_id
        or occurrence.route_identity_id != route.route_identity_id
        or occurrence.production_runtime_envelope_id != runtime_envelope.envelope_id
        or occurrence.runtime_business_result_id != runtime_envelope.business_result_id
        or occurrence.partial_native_transcript_id
        != owner_candidate_set.partial_native_transcript_id
        or occurrence.transcript_terminal_id
        != owner_candidate_set.partial_native_terminal_id
        or occurrence.verified_nine_source_envelope_id
        != verified_nine_envelope.verified_envelope_id
        or occurrence.owner_event_candidate_set_id
        != owner_candidate_set.candidate_set_id
        or expected_owner_candidates.candidate_set_id
        != owner_candidate_set.candidate_set_id
        or expected_owner_candidates.to_document()
        != owner_candidate_set.to_document()
        or occurrence.owner_event_execution_binding_id != binding.binding_id
        or occurrence.production_role_manifest_id
        != binding.production_role_manifest_id
        or occurrence.source_snapshot_id != binding.source_snapshot_id
        or occurrence.source_archive_sha256 != binding.source_archive_sha256
        or occurrence.source_archive_byte_count != binding.source_archive_byte_count
        or occurrence.source_v3_envelope_id
        != verified_nine_envelope.source_v3_envelope_id
        or occurrence.scientific_occurrence_id != binding.scientific_occurrence_id
        or occurrence.logical_occurrence_id != binding.phase3e_logical_occurrence_id
        or occurrence.logical_occurrence_id != source.occurrence_id
        or occurrence.route_attempt_id != source.route_attempt_id
        or occurrence.decision_point_id != source.decision_point_id
        or occurrence.measurement_window_id != source.measurement_window_id
        or occurrence.terminal_closure_observation_id
        != source.terminal_closure_observation_id
        or occurrence.counter_registry_id != registry.registry_id
        or occurrence.stage_profile_id != stage_profile.stage_profile_id
        or occurrence.boundary_profile_id != manifest.manifest_id
        or rules.counter_registry_id != registry.registry_id
        or rules.stage_profile_id != stage_profile.stage_profile_id
        or rules.boundary_manifest_id != manifest.manifest_id
        or coverage.coverage_profile_id
        != rules_v1.official_owner_boundary_coverage_profile_v1().coverage_profile_id
        or binding.request_id != request.request_id
        or binding.route_identity_id != route.route_identity_id
        or binding.production_runtime_envelope_id != runtime_envelope.envelope_id
        or binding.production_role_manifest_id != runtime_envelope.manifest_id
        or role_manifest.manifest_id != runtime_envelope.manifest_id
        or role_manifest.request_id != request.request_id
        or role_manifest.route_identity_id != route.route_identity_id
        or role_manifest.source_snapshot_id != transport.source_snapshot_id
        or role_manifest.source_archive_sha256 != transport.source_archive_sha256
        or role_manifest.source_archive_byte_count != transport.source_archive_byte_count
        or binding.broker_transcript_id != runtime_envelope.transcript.transcript_id
        or binding.business_bundle_id != runtime_envelope.business_result_id
        or binding.source_snapshot_id != transport.source_snapshot_id
        or binding.source_archive_sha256 != transport.source_archive_sha256
        or binding.source_archive_byte_count != transport.source_archive_byte_count
        or hashlib.sha256(source_archive_raw).hexdigest()
        != transport.source_archive_sha256
        or len(source_archive_raw) != transport.source_archive_byte_count
        or source_archive_raw != transport._archive_bytes  # noqa: SLF001
        or len(owner_candidate_set.site_closures) != EXPECTED_OWNER_SITE_COUNT
        or len(owner_candidate_set.path_candidates) != EXPECTED_OWNER_PATH_COUNT
    ):
        _fail("native-zero production occurrence/profile/source context crossed")

    # Independently replay exact site, leaf and hash-chain conservation facts.
    boundary_by_key = {
        row.boundary_key: row
        for row in manifest.boundaries
        if row.to_document()["emittable_in_this_fixture"] is True
    }
    coverage_by_key = {row.boundary_key: row for row in coverage.sites}
    chain_order = {
        node_id: index for index, node_id in enumerate(occurrence.ordered_chain_node_ids)
    }
    all_events: list[str] = []
    for site in owner_candidate_set.site_closures:
        row = boundary_by_key.get(site.boundary_key)
        covered = coverage_by_key.get(site.boundary_key)
        if (
            row is None
            or covered is None
            or site.execution_binding_id != binding.binding_id
            or site.partial_native_transcript_id != occurrence.partial_native_transcript_id
            or site.boundary_id != row.boundary_id
            or site.dispatch_key != row.dispatch_key
            or site.stage != row.stage.value
            or site.path != row.target_path
            or site.operation_source_module != row.operation_source_module
            or site.operation_source_symbol != row.operation_source_symbol
            or site.stage_start_id not in chain_order
            or site.stage_completion_id not in chain_order
            or chain_order[site.stage_start_id] >= chain_order[site.stage_completion_id]
            or any(event_id not in chain_order for event_id in site.ordered_event_ids)
            or any(
                not (
                    chain_order[site.stage_start_id]
                    < chain_order[event_id]
                    < chain_order[site.stage_completion_id]
                )
                for event_id in site.ordered_event_ids
            )
        ):
            _fail("owner-window site closure crossed its source/stage/hash-chain binding")
        all_events.extend(site.ordered_event_ids)
    if len(all_events) != len(set(all_events)):
        _fail("one owner event appears in multiple site closures")
    # The independently replayed transcript binds one occurrence-start object
    # outside ``chain_nodes``.  Inside the ordered chain there are exactly five
    # stage starts, five stage completions, and one occurrence terminal; all
    # remaining nodes must be the site-bound operation events conserved above.
    if (
        EXPECTED_OCCURRENCE_START_COUNT != 1
        or EXPECTED_STAGE_START_COUNT != 5
        or EXPECTED_STAGE_COMPLETION_COUNT != 5
        or EXPECTED_TERMINAL_CHAIN_NODE_COUNT != 1
        or len(occurrence.ordered_chain_node_ids) < EXPECTED_NON_EVENT_CHAIN_NODE_COUNT
        or len(all_events)
        != len(occurrence.ordered_chain_node_ids) - EXPECTED_NON_EVENT_CHAIN_NODE_COUNT
    ):
        _fail("complete owner-window event conservation failed")

    candidate_by_path = {row.path: row for row in owner_candidate_set.path_candidates}
    if set(candidate_by_path) != {row.path for row in coverage.sites}:
        _fail("owner-path candidate set differs from exact 71-path coverage")
    candidate_events: list[str] = []
    closure_by_id = {row.site_closure_id: row for row in owner_candidate_set.site_closures}
    for path, candidate in candidate_by_path.items():
        leaf = registry.by_path[path]
        closures = [closure_by_id.get(value) for value in candidate.site_closure_ids]
        if (
            candidate.execution_binding_id != binding.binding_id
            or candidate.partial_native_transcript_id != occurrence.partial_native_transcript_id
            or candidate.semantics_id != leaf.semantics_id
            or candidate.owner != leaf.owner
            or candidate.unit != leaf.unit
            or candidate.lane != leaf.lane.value
            or candidate.scope != leaf.scope
            or candidate.reducer != leaf.reducer.value
            or candidate.comparison_axis != leaf.comparison_axis
            or any(row is None or row.path != path for row in closures)
            or candidate.value != len(candidate.ordered_event_ids)
        ):
            _fail("owner-path candidate crossed its exact leaf/site closure")
        candidate_events.extend(candidate.ordered_event_ids)
    if set(candidate_events) != set(all_events) or len(candidate_events) != len(all_events):
        _fail("owner-path candidates do not conserve the complete event stream")
    return registry, stage_profile, manifest, rules, candidate_by_path


def _issue(
    *,
    occurrence_cutoff_authority: Any,
    owner_candidate_set: Any,
    verified_nine_envelope: Any,
    runtime_envelope: Any,
    request_replay: Any,
    role_manifest: Any,
    operational_output_bytes: Any,
    source_archive_raw: Any,
) -> K7ProfileNativeZeroEnvelopeV1:
    registry, stage_profile, manifest, rule_registry, candidates = _validate_joined_context(
        occurrence_cutoff_authority=occurrence_cutoff_authority,
        owner_candidate_set=owner_candidate_set,
        verified_nine_envelope=verified_nine_envelope,
        runtime_envelope=runtime_envelope,
        request_replay=request_replay,
        role_manifest=role_manifest,
        operational_output_bytes=operational_output_bytes,
        source_archive_raw=source_archive_raw,
    )
    occurrence = occurrence_cutoff_authority.occurrence_authority
    cutoff = occurrence_cutoff_authority.cutoff_authority
    binding = owner_candidate_set.execution_binding
    inventory_id, inventory_rows = _scan_source_hook_inventory(
        source_archive_raw=source_archive_raw,
        execution_binding=binding,
    )
    owner_window_payload = {
        "schema": "acfqp.construction_k7_native_zero_owner_window_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "occurrence_authority_id": occurrence.authority_id,
        "cutoff_authority_id": cutoff.authority_id,
        "owner_candidate_set_id": owner_candidate_set.candidate_set_id,
        "owner_execution_binding_id": binding.binding_id,
        "partial_native_transcript_id": owner_candidate_set.partial_native_transcript_id,
        "partial_native_terminal_id": owner_candidate_set.partial_native_terminal_id,
        "site_closure_ids": [row.site_closure_id for row in owner_candidate_set.site_closures],
        "path_candidate_ids": [row.candidate_id for row in owner_candidate_set.path_candidates],
        "source_hook_inventory_id": inventory_id,
        "five_stage_plan": [row.value for row in partial_v1.ROOT_CAP_FIVE_STAGE_PLAN_V1],
        "occurrence_start_count_outside_chain": EXPECTED_OCCURRENCE_START_COUNT,
        "stage_start_count_inside_chain": EXPECTED_STAGE_START_COUNT,
        "stage_completion_count_inside_chain": EXPECTED_STAGE_COMPLETION_COUNT,
        "terminal_count_inside_chain": EXPECTED_TERMINAL_CHAIN_NODE_COUNT,
        "five_stage_terminal_complete": True,
        "all_89_owner_sites_closed": True,
        "all_71_owner_paths_resolved": True,
        "all_runtime_events_conserved": True,
        "production_low_level_test_api_disabled": True,
        "event_absence_used_as_zero_evidence": False,
    }
    owner_window_id = _local_id(OWNER_WINDOW_CLOSURE_DOMAIN, owner_window_payload)

    rules_by_path = rule_registry.by_path
    dependencies = {
        path: tuple(
            replacement
            for replacement in rule.replacement_paths
            if replacement in rules_by_path
        )
        for path, rule in rules_by_path.items()
    }
    order = _topological_order(dependencies)
    rank = {path: index for index, path in enumerate(order)}
    issued_by_path: dict[str, K7ProfileNativeZeroAttestationV1] = {}
    stage_plan = tuple(row.value for row in partial_v1.ROOT_CAP_FIVE_STAGE_PLAN_V1)
    gateway_capable_paths = {
        row.target_path
        for row in manifest.boundaries
        if row.to_document()["emittable_in_this_fixture"] is True
    }
    if (
        len(gateway_capable_paths) != EXPECTED_OWNER_PATH_COUNT
        or gateway_capable_paths != set(candidates)
        or gateway_capable_paths & set(rules_by_path)
    ):
        _fail("gateway-capable path set differs from the exact 71/114 partition")

    for path in order:
        rule = rules_by_path[path]
        path_has_gateway_capability = path in gateway_capable_paths
        if path in candidates or path_has_gateway_capability:
            _fail("native-zero path unexpectedly has an owner-emittable candidate")
        entered = tuple(stage for stage in rule.applicable_stages if stage in stage_plan)
        unentered = tuple(stage for stage in rule.applicable_stages if stage not in stage_plan)
        if (
            rule.reason_code
            is rules_v1.ProfileNativeZeroReasonCodeV1.FORBIDDEN_STAGE_NOT_EXECUTED
            and entered
        ):
            _fail("forbidden-stage zero entered the exact five-stage plan")

        replacements: list[NativeZeroReplacementResolutionV1] = []
        for replacement_path in rule.replacement_paths:
            if replacement_path in candidates:
                candidate = candidates[replacement_path]
                replacements.append(
                    NativeZeroReplacementResolutionV1(
                        replacement_path,
                        "OWNER_PATH_COUNTER_CANDIDATE",
                        candidate.candidate_id,
                        candidate.value,
                        None,
                    )
                )
            elif replacement_path in issued_by_path:
                dependency = issued_by_path[replacement_path]
                replacements.append(
                    NativeZeroReplacementResolutionV1(
                        replacement_path,
                        "PROFILE_NATIVE_ZERO_ATTESTATION",
                        dependency.attestation_id,
                        0,
                        dependency.issuance_rank,
                    )
                )
            else:
                _fail("legacy replacement lacks a prior exact candidate/zero resolution")
        replacements_tuple = tuple(
            sorted(replacements, key=lambda row: row.replacement_path)
        )

        stage_payload = {
            "schema": "acfqp.construction_k7_native_zero_stage_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "rule_id": rule.rule_id,
            "path": path,
            "occurrence_authority_id": occurrence.authority_id,
            "terminal_closure_observation_id": occurrence.terminal_closure_observation_id,
            "partial_native_terminal_id": occurrence.transcript_terminal_id,
            "five_stage_plan": list(stage_plan),
            "applicable_stages": list(rule.applicable_stages),
            "entered_applicable_stages": list(entered),
            "unentered_applicable_stages": list(unentered),
            "exact_terminal_completion_required": True,
        }
        stage_id = _local_id(STAGE_EVIDENCE_DOMAIN, stage_payload)
        branch_payload = {
            "schema": "acfqp.construction_k7_native_zero_branch_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "rule_id": rule.rule_id,
            "path": path,
            "reason_code": rule.reason_code.value,
            "stage_evidence_id": stage_id,
            "source_hook_inventory_id": inventory_id,
            "owner_window_closure_id": owner_window_id,
            "path_has_registered_gateway_capability": path_has_gateway_capability,
            "entered_applicable_stages": list(entered),
            "unentered_applicable_stages": list(unentered),
            "source_level_emission_capability_absent": True,
            "complete_owner_control_flow_closed": True,
            "event_absence_used_as_zero_evidence": False,
        }
        branch_id = _local_id(BRANCH_EVIDENCE_DOMAIN, branch_payload)
        verifier_payload = {
            "schema": "acfqp.construction_k7_native_zero_semantic_verifier.v1",
            "schema_version": SCHEMA_VERSION,
            "rule_id": rule.rule_id,
            "path": path,
            "asserted_value": 0,
            "occurrence_authority_id": occurrence.authority_id,
            "cutoff_authority_id": cutoff.authority_id,
            "verified_nine_envelope_id": verified_nine_envelope.verified_envelope_id,
            "owner_candidate_set_id": owner_candidate_set.candidate_set_id,
            "stage_evidence_id": stage_id,
            "branch_nonexecution_evidence_id": branch_id,
            "replacement_resolution_ids": [row.resolution_id for row in replacements_tuple],
            "event_absence_used_as_zero_evidence": False,
        }
        verifier_id = _local_id(ZERO_VERIFIER_DOMAIN, verifier_payload)

        evidence_by_kind = {
            rules_v1.ProfileNativeZeroEvidenceKindV1.BRANCH_NONEXECUTION.value: (
                branch_id,
            ),
            rules_v1.ProfileNativeZeroEvidenceKindV1.EXECUTION_IDENTITY.value: tuple(
                sorted(
                    {
                        occurrence.authority_id,
                        cutoff.authority_id,
                        runtime_envelope.envelope_id,
                        request_replay.replay_id,
                    }
                )
            ),
            rules_v1.ProfileNativeZeroEvidenceKindV1.LOADED_CODE_IDENTITY.value: tuple(
                sorted(
                    {
                        inventory_id,
                        owner_window_id,
                        binding.binding_id,
                        owner_candidate_set.candidate_set_id,
                    }
                )
            ),
            rules_v1.ProfileNativeZeroEvidenceKindV1.STAGE_EXECUTION.value: (stage_id,),
            rules_v1.ProfileNativeZeroEvidenceKindV1.ZERO_SEMANTIC_VERIFIER.value: (
                verifier_id,
            ),
            rules_v1.ProfileNativeZeroEvidenceKindV1.REPLACEMENT_PATH_RESOLUTION.value: tuple(
                sorted(row.resolution_id for row in replacements_tuple)
            ),
        }
        obligations = []
        for requirement in rule.evidence_requirements:
            evidence_ids = evidence_by_kind.get(requirement.kind.value, ())
            if not evidence_ids:
                _fail("native-zero rule obligation lacks exact semantic evidence")
            obligations.append(
                NativeZeroObligationEvidenceV1(
                    requirement.kind.value,
                    requirement.obligation_key,
                    evidence_ids,
                )
            )
        leaf = registry.by_path[path]
        attestation = K7ProfileNativeZeroAttestationV1(
            _ATTESTATION_ISSUER,
            rule.rule_id,
            rule_registry.registry_id,
            path,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.scope,
            leaf.reducer.value,
            rule.reason_code.value,
            0,
            rank[path],
            occurrence.authority_id,
            cutoff.authority_id,
            verified_nine_envelope.verified_envelope_id,
            owner_candidate_set.candidate_set_id,
            inventory_id,
            owner_window_id,
            stage_id,
            branch_id,
            verifier_id,
            replacements_tuple,
            tuple(sorted(obligations, key=lambda row: row.obligation_key)),
        )
        issued_by_path[path] = attestation

    attestations = tuple(issued_by_path[path] for path in sorted(issued_by_path))
    result = K7ProfileNativeZeroEnvelopeV1(
        _ENVELOPE_ISSUER,
        rule_registry.registry_id,
        registry.registry_id,
        stage_profile.stage_profile_id,
        manifest.manifest_id,
        rule_registry.execution_profile_id,
        occurrence.authority_id,
        cutoff.authority_id,
        verified_nine_envelope.verified_envelope_id,
        owner_candidate_set.candidate_set_id,
        inventory_id,
        owner_window_id,
        binding.source_archive_sha256,
        binding.source_archive_byte_count,
        order,
        attestations,
    )
    return result


def issue_k7_profile_native_zero_semantic_authority_v1(
    **kwargs: Any,
) -> K7ProfileNativeZeroEnvelopeV1:
    """Issue exactly 114 zero attestations from positive production roots."""

    return _issue(**kwargs)


def replay_k7_profile_native_zero_semantic_authority_v1(
    claimed: Any,
    **kwargs: Any,
) -> K7ProfileNativeZeroEnvelopeV1:
    """Re-derive a typed envelope and reject mutation or transplantation."""

    if type(claimed) is not K7ProfileNativeZeroEnvelopeV1:
        _fail("native-zero replay requires one exact typed envelope")
    expected = _issue(**kwargs)
    if claimed.envelope_id != expected.envelope_id or claimed.to_document() != expected.to_document():
        _fail("native-zero envelope differs from independent semantic replay")
    return expected


def verify_k7_profile_native_zero_semantic_authority_bytes_v1(
    *, raw: bytes, **kwargs: Any
) -> K7ProfileNativeZeroEnvelopeV1:
    """Verify portable bytes by reissuing all 114 proofs from held roots."""

    if type(raw) is not bytes or not raw:
        _fail("native-zero envelope bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionProfileNativeZeroSemanticAuthorityV1Error(
            "native-zero envelope bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("native-zero envelope bytes are noncanonical")
    claimed_id = document.get("profile_native_zero_envelope_id")
    payload = dict(document)
    payload.pop("profile_native_zero_envelope_id", None)
    if (
        type(claimed_id) is not str
        or _local_id(ZERO_ENVELOPE_DOMAIN, payload) != claimed_id
    ):
        _fail("native-zero envelope content identity changed")
    expected = _issue(**kwargs)
    if document != expected.to_document():
        _fail("native-zero envelope bytes differ from independent semantic replay")
    return expected


__all__ = (
    "ConstructionProfileNativeZeroSemanticAuthorityV1Error",
    "EXPECTED_ZERO_PATH_COUNT",
    "K7ProfileNativeZeroAttestationV1",
    "K7ProfileNativeZeroEnvelopeV1",
    "NativeZeroObligationEvidenceV1",
    "NativeZeroReplacementResolutionV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "issue_k7_profile_native_zero_semantic_authority_v1",
    "replay_k7_profile_native_zero_semantic_authority_v1",
    "verify_k7_profile_native_zero_semantic_authority_bytes_v1",
)
