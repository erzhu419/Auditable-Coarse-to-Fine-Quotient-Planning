"""Registered-template candidates for the H1 shared-resource paths.

Contract 2.0.58-C records a finite hypothesis catalogue for the nine
shared-resource formulae.  It binds the preregistered serializer-template DAG,
but neither the DAG nor the derived site partitions come from the production
lifecycle.  Consequently this module is *not* a production structural source
authority: common multiplicities, I/O failure prefixes, mount intervals,
native physical identities, launch-ambiguity coverage, and numeric extents all
remain typed-unbound.  No missing row is interpreted as zero and no wildcard
or caller-supplied aggregate is accepted.

This module intentionally does not issue a numeric operand, route upper,
route decision, execution request, receipt, CounterRecord, or Gate result.
Byte extents and cgroup limits remain typed preexecution blockers.  The
retained peak readback is separately a post-run receipt blocker and may never
be used to authorize a preexecution route upper.  ``io.output_bytes`` remains
owned by the later joint production serializer/read fixed point.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hmac
from typing import Any, Iterable, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_h1_execution_topology_profile_v1 as topology_v1
from acfqp import construction_k7_h1_production_output_upper_v1 as output_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_LAUNCH_CATALOGUE_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_MEMORY_SCOPE_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PHYSICAL_MOUNT_CATALOGUE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_COMMON_CATALOGUE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_IO_CATALOGUE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SHARED_RESOURCE_BRANCH_PROGRAM_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.58"
PROFILE_KEY = "construction_k7_h1_shared_resource_catalogues_v1"

PREDECISION_STRUCTURAL_AUTHORITY = False
PREDECISION_STRUCTURAL_CATALOGUE_CANDIDATE_PRESENT = True
PRODUCTION_BRANCH_PROGRAM_AUTHORITY_PRESENT = False
NUMERIC_SHARED_OPERAND_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
ROUTE_EXECUTION_AUTHORIZED = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

BRANCH_PROGRAM_DOMAIN = (
    CONSTRUCTION_K7_H1_SHARED_RESOURCE_BRANCH_PROGRAM_V1_DOMAIN
)
COMMON_CATALOGUE_DOMAIN = CONSTRUCTION_K7_H1_SHARED_COMMON_CATALOGUE_V1_DOMAIN
IO_CATALOGUE_DOMAIN = CONSTRUCTION_K7_H1_SHARED_IO_CATALOGUE_V1_DOMAIN
MOUNT_CATALOGUE_DOMAIN = CONSTRUCTION_K7_H1_PHYSICAL_MOUNT_CATALOGUE_V1_DOMAIN
MEMORY_CANDIDATE_DOMAIN = CONSTRUCTION_K7_H1_MEMORY_SCOPE_CANDIDATE_V1_DOMAIN
LAUNCH_CANDIDATE_DOMAIN = CONSTRUCTION_K7_H1_LAUNCH_CATALOGUE_CANDIDATE_V1_DOMAIN

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    BRANCH_PROGRAM_DOMAIN,
    COMMON_CATALOGUE_DOMAIN,
    IO_CATALOGUE_DOMAIN,
    MOUNT_CATALOGUE_DOMAIN,
    MEMORY_CANDIDATE_DOMAIN,
    LAUNCH_CANDIDATE_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover - import-time central registry invariant
    raise RuntimeError("H1 structural-catalogue domains are not registered")

COMMON_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
)
READ_PATH = "io.read_bytes"
STAGE_PATH = "io.staged_bytes"
MOUNT_PATH = "io.mounted_bytes_peak"
OUTPUT_PATH = "io.output_bytes"
MEMORY_PATH = "memory.working_bytes_peak"
LAUNCH_PATH = "process.launches"
STRUCTURAL_PATHS = (*COMMON_PATHS, READ_PATH, STAGE_PATH, MOUNT_PATH, LAUNCH_PATH)

EXPECTED_CONTEXT_COUNT = 10
EXPECTED_BRANCH_COUNT = 90
EXPECTED_STAGE_SITE_COUNT = 10
EXPECTED_OUTPUT_ROLE_COUNT = 8
EXPECTED_LAUNCH_COUNT = 2
EXPECTED_OUTER_PID_MEMBERSHIP_MINIMUM = 3

# These names are forbidden as document keys at every nesting level.  The
# catalogue may describe that those later objects are absent, but cannot bind
# their identities or accept caller-provided future state.
FORBIDDEN_FUTURE_FIELDS = frozenset(
    {
        "decision_point_id",
        "DecisionPoint_id",
        "RouteDecisionContext_id",
        "route_decision_context_id",
        "route_upper_id",
        "route_upper",
        "route_upper_bound_envelope_id",
        "formal_v7_route_upper_id",
        "route_decision_id",
        "route_decision",
        "formal_v7_route_decision_id",
        "marginal_route_decision_id",
        "selected_route",
        "route_decision_freeze_attestation_id",
        "freeze_attestation_id",
        "postrun_result_id",
        "actual_work_vector_id",
        "actual_comparison_vector_id",
    }
)


class ConstructionK7H1SharedResourceCataloguesV1Error(ValueError):
    """A structural catalogue, branch partition, or identity failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1SharedResourceCataloguesV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1SharedResourceCataloguesV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{label} must be one nonempty exact string")
    return value


def _exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{label} must be one exact integer >= {minimum}")
    return value


def _unique_tuple(value: Any, label: str, *, allow_empty: bool = False) -> tuple[Any, ...]:
    if (
        type(value) is not tuple
        or (not allow_empty and not value)
        or len(value) != len(set(value))
    ):
        _fail(f"{label} must be one unique exact tuple")
    return value


def _domain_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("structural catalogue used an undeclared content domain")
    return content_id(domain, dict(payload))


def _reject_forbidden_keys(value: Any) -> None:
    if type(value) is dict:
        bad = FORBIDDEN_FUTURE_FIELDS & set(value)
        if bad:
            _fail(f"future authority field is forbidden: {sorted(bad)[0]}")
        for child in value.values():
            _reject_forbidden_keys(child)
    elif type(value) is list:
        for child in value:
            _reject_forbidden_keys(child)


def _structural_slot_id(kind: str, *parts: str) -> str:
    return _domain_id(
        MOUNT_CATALOGUE_DOMAIN,
        {
            "schema": "acfqp.h1_structural_resource_slot.v1",
            "slot_kind": _nonempty(kind, "slot kind"),
            "parts": [_nonempty(part, "slot part") for part in parts],
            "numeric_or_runtime_identity": False,
        },
    )


class H1AnchorKindV1(str, Enum):
    RUNTIME_EVENT = "RUNTIME_EVENT"
    OUTPUT_ROLE = "OUTPUT_ROLE"
    FINALIZATION_STATUS = "FINALIZATION_STATUS"


class H1IngressModeV1(str, Enum):
    COPY = "COPY"
    BIND = "BIND"


class H1PhysicalOriginV1(str, Enum):
    COPY_TARGET = "COPY_TARGET"
    BIND_ALIAS = "BIND_ALIAS"
    BIND_UNRESOLVED_TARGET = "BIND_UNRESOLVED_TARGET"
    CREATED_OUTPUT = "CREATED_OUTPUT"


class H1ExtentAuthorityKindV1(str, Enum):
    SEALED_INPUT_EXTENT = "SEALED_INPUT_EXTENT"
    BUSINESS_RESULT_EXTENT = "BUSINESS_RESULT_EXTENT"
    OUTPUT_ROLE_EXTENT = "OUTPUT_ROLE_EXTENT"
    CGROUP_CAP_READBACK = "CGROUP_CAP_READBACK"
    CGROUP_PEAK_READBACK = "CGROUP_PEAK_READBACK"
    CGROUP_PIDS_MAX_READBACK = "CGROUP_PIDS_MAX_READBACK"


class H1EvidenceAuthorityKindV1(str, Enum):
    INODE_OFD_ALIAS_REPLAY = "INODE_OFD_ALIAS_REPLAY"
    OUTER_CGROUP_PID_MEMBERSHIP_REPLAY = "OUTER_CGROUP_PID_MEMBERSHIP_REPLAY"


@dataclass(frozen=True, slots=True)
class H1TypedNumericBlockerV1:
    blocker_key: str
    authority_kind: H1ExtentAuthorityKindV1
    required_source_role: str
    numeric_value: None = None

    def __post_init__(self) -> None:
        _nonempty(self.blocker_key, "numeric blocker key")
        try:
            object.__setattr__(
                self, "authority_kind", H1ExtentAuthorityKindV1(self.authority_kind)
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1SharedResourceCataloguesV1Error(
                "numeric blocker authority kind is invalid"
            ) from error
        _nonempty(self.required_source_role, "numeric blocker source role")
        if self.numeric_value is not None:
            _fail("predecision structural blocker cannot carry a numeric value")

    def to_document(self) -> dict[str, Any]:
        return {
            "blocker_key": self.blocker_key,
            "authority_kind": self.authority_kind.value,
            "required_source_role": self.required_source_role,
            "numeric_value": None,
            "status": "REQUIRED_UNBOUND",
            "missing_value_is_zero": False,
        }


def _blocker(
    key: str, kind: H1ExtentAuthorityKindV1, source: str
) -> H1TypedNumericBlockerV1:
    return H1TypedNumericBlockerV1(key, kind, source)


@dataclass(frozen=True, slots=True)
class H1TypedEvidenceBlockerV1:
    blocker_key: str
    authority_kind: H1EvidenceAuthorityKindV1
    required_source_role: str
    evidence_id: None = None

    def __post_init__(self) -> None:
        _nonempty(self.blocker_key, "evidence blocker key")
        try:
            object.__setattr__(
                self,
                "authority_kind",
                H1EvidenceAuthorityKindV1(self.authority_kind),
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1SharedResourceCataloguesV1Error(
                "evidence blocker authority kind is invalid"
            ) from error
        _nonempty(self.required_source_role, "evidence blocker source role")
        if self.evidence_id is not None:
            _fail("predecision structural blocker cannot carry runtime evidence")

    def to_document(self) -> dict[str, Any]:
        return {
            "blocker_key": self.blocker_key,
            "authority_kind": self.authority_kind.value,
            "required_source_role": self.required_source_role,
            "evidence_id": None,
            "status": "REQUIRED_UNBOUND",
        }


@dataclass(frozen=True, slots=True)
class H1CommonSiteV1:
    site_key: str
    path: str
    anchor_kind: H1AnchorKindV1
    anchor_key: str

    def __post_init__(self) -> None:
        _nonempty(self.site_key, "common site key")
        if self.path not in COMMON_PATHS:
            _fail("common site names a non-common path")
        try:
            object.__setattr__(self, "anchor_kind", H1AnchorKindV1(self.anchor_kind))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1SharedResourceCataloguesV1Error(
                "common-site anchor kind is invalid"
            ) from error
        _nonempty(self.anchor_key, "common-site anchor")

    def to_document(self) -> dict[str, Any]:
        return {
            "site_key": self.site_key,
            "path": self.path,
            "anchor_kind": self.anchor_kind.value,
            "anchor_key": self.anchor_key,
            "multiplicity_semantics": "PRODUCTION_MULTIPLICITY_REQUIRED_UNBOUND",
            "registered_template_candidate_multiplicity_upper": 1,
            "native_source_symbol_multiplicity_authority_present": False,
            "status": "REGISTERED_TEMPLATE_CANDIDATE_ONLY",
            "wildcard": False,
        }


_COMMON_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1SharedCommonCatalogueV1:
    _issuer: InitVar[object]
    output_branch_dag_id: str
    sites: tuple[H1CommonSiteV1, ...]
    _catalogue_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _COMMON_ISSUER:
            _fail("shared common catalogue candidate is caller-minted")
        dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
        if self.output_branch_dag_id != dag.dag_id:
            _fail("shared common catalogue crossed the preregistered output DAG")
        expected = _common_sites(dag)
        if self.sites != expected:
            _fail("shared common catalogue omitted, reordered, or invented a site")
        object.__setattr__(
            self,
            "_catalogue_id",
            _domain_id(COMMON_CATALOGUE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_shared_common_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_production_output_branch_dag_id": self.output_branch_dag_id,
            "paths": list(COMMON_PATHS),
            "sites": [row.to_document() for row in self.sites],
            "formula_schema_candidate": (
                "MAX_BRANCH_SUM_SOURCE_OWNED_EVENT_MULTIPLICITIES"
            ),
            "formula_authority_present": False,
            "admission_schema_candidate": (
                "ONE_UPPER_ADMISSION_PER_REGISTERED_TEMPLATE_EVENT_SITE"
            ),
            "production_source_symbol_multiplicity_authority_present": False,
            "caller_aggregate_allowed": False,
            "wildcard_allowed": False,
            "missing_as_zero_allowed": False,
            "numeric_operand_issued": False,
            "predecision_structural_authority": False,
            "predecision_structural_catalogue_candidate_present": True,
        }

    @property
    def catalogue_id(self) -> str:
        if _domain_id(COMMON_CATALOGUE_DOMAIN, self._payload()) != self._catalogue_id:
            _fail("shared common catalogue changed")
        return self._catalogue_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_shared_common_catalogue_id": self.catalogue_id}

    @property
    def by_key(self) -> dict[str, H1CommonSiteV1]:
        return {row.site_key: row for row in self.sites}


def _ordered_runtime_anchors(
    dag: output_v1.H1ProductionOutputBranchDAGV1,
) -> tuple[str, ...]:
    rows: list[str] = []
    for context in dag.contexts:
        for event in context.runtime_path:
            if event not in rows:
                rows.append(event)
    return tuple(rows)


def _common_sites(
    dag: output_v1.H1ProductionOutputBranchDAGV1,
) -> tuple[H1CommonSiteV1, ...]:
    anchors = (
        *((H1AnchorKindV1.RUNTIME_EVENT, key) for key in _ordered_runtime_anchors(dag)),
        *((H1AnchorKindV1.OUTPUT_ROLE, key) for key in output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES),
        *((H1AnchorKindV1.FINALIZATION_STATUS, key.value) for key in output_v1.H1OutputFinalizationStatusV1),
    )
    rows = []
    for anchor_kind, anchor_key in anchors:
        for path in COMMON_PATHS:
            rows.append(
                H1CommonSiteV1(
                    f"{path}:{anchor_kind.value}:{anchor_key}",
                    path,
                    anchor_kind,
                    anchor_key,
                )
            )
    return tuple(rows)


_ALIAS_ISSUER = object()
_LIVE_ALIASES: dict[int, tuple[object, bytes]] = {}


@dataclass(frozen=True, slots=True)
class H1TypedInodeOFDAliasCandidateV1:
    _issuer: InitVar[object]
    alias_key: str
    source_slot_id: str
    inode_identity_slot_id: str
    open_file_description_slot_id: str
    target_keys: tuple[str, ...]
    runtime_evidence_blocker: H1TypedEvidenceBlockerV1
    _alias_candidate_id: str = field(init=False, repr=False)
    _candidate_shared_instance_slot_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ALIAS_ISSUER:
            _fail("typed inode/OFD alias candidate is caller-minted")
        _nonempty(self.alias_key, "BIND alias key")
        _cid(self.source_slot_id, "BIND source slot")
        _cid(self.inode_identity_slot_id, "BIND inode slot")
        _cid(self.open_file_description_slot_id, "BIND OFD slot")
        _unique_tuple(self.target_keys, "BIND target keys")
        if len(self.target_keys) < 2:
            _fail("typed BIND alias candidate must cover at least two exact targets")
        if type(self.runtime_evidence_blocker) is not H1TypedEvidenceBlockerV1:
            _fail("typed BIND alias lacks runtime inode/OFD evidence blocker")
        payload = self._payload()
        alias_id = _domain_id(MOUNT_CATALOGUE_DOMAIN, payload)
        object.__setattr__(self, "_alias_candidate_id", alias_id)
        object.__setattr__(
            self,
            "_candidate_shared_instance_slot_id",
            _domain_id(
                MOUNT_CATALOGUE_DOMAIN,
                {
                    "schema": "acfqp.h1_bind_candidate_shared_instance_slot.v1",
                    "typed_inode_ofd_alias_candidate_id": alias_id,
                    "source_slot_id": self.source_slot_id,
                    "inode_identity_slot_id": self.inode_identity_slot_id,
                    "open_file_description_slot_id": self.open_file_description_slot_id,
                    "native_inode_ofd_evidence_bound": False,
                    "native_physical_instance_authority_present": False,
                },
            ),
        )
        _LIVE_ALIASES[id(self)] = (self, canonical_json_bytes(self.to_document()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_typed_inode_ofd_alias_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "alias_key": self.alias_key,
            "source_slot_id": self.source_slot_id,
            "inode_identity_slot_id": self.inode_identity_slot_id,
            "open_file_description_slot_id": self.open_file_description_slot_id,
            "target_keys": list(self.target_keys),
            "runtime_evidence_blocker": self.runtime_evidence_blocker.to_document(),
            "same_source_inode_and_open_file_description_required": True,
            "native_inode_ofd_evidence_bound": False,
            "shared_physical_instance_authorized": False,
            "status": "REQUIRED_UNBOUND_ALIAS_CANDIDATE",
            "content_digest_alone_authorizes_alias": False,
            "caller_supplied_alias_id_allowed": False,
        }

    @property
    def alias_authority_id(self) -> str:
        """Deprecated unsafe alias; V1 only freezes an alias candidate."""

        _fail(
            "deprecated alias_authority_id is unavailable: use alias_candidate_id"
        )

    @property
    def alias_candidate_id(self) -> str:
        return self._alias_candidate_id

    @property
    def candidate_shared_instance_slot_id(self) -> str:
        """Return a typed candidate slot, never a native physical identity."""

        return self._candidate_shared_instance_slot_id

    @property
    def physical_instance_id(self) -> str:
        """Deprecated unsafe alias: a candidate cannot expose a physical ID."""

        _fail(
            "deprecated BIND physical_instance_id is unavailable: use "
            "candidate_shared_instance_slot_id and bind native inode/OFD evidence "
            "in a later production authority"
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "typed_inode_ofd_alias_candidate_id": self.alias_candidate_id,
            "candidate_shared_instance_slot_id": self.candidate_shared_instance_slot_id,
            "native_physical_instance_authority_present": False,
        }


def H1TypedInodeOFDAliasAuthorityV1(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Deprecated authority constructor; V1 has only an alias candidate."""

    _fail(
        "deprecated H1TypedInodeOFDAliasAuthorityV1 is unavailable: "
        "use the issuer-owned alias candidate"
    )


def derive_copy_structural_target_slot_id_v1(
    *,
    source_content_sha256: str,
    target_role: str,
    target_key: str,
    copy_ordinal: int,
) -> str:
    """Derive a target-distinct structural COPY slot, never physical evidence."""

    if (
        type(source_content_sha256) is not str
        or len(source_content_sha256) != 64
        or any(ch not in "0123456789abcdef" for ch in source_content_sha256)
    ):
        _fail("COPY source digest must be one lowercase sha256")
    _nonempty(target_role, "COPY target role")
    _nonempty(target_key, "COPY target key")
    _exact_int(copy_ordinal, "COPY ordinal", minimum=1)
    return _domain_id(
        MOUNT_CATALOGUE_DOMAIN,
        {
            "schema": "acfqp.h1_copy_structural_target_slot.v1",
            "source_content_sha256": source_content_sha256,
            "target_role": target_role,
            "target_key": target_key,
            "copy_ordinal": copy_ordinal,
            "content_digest_deduplication": False,
            "native_bytes_or_fd_evidence_bound": False,
            "native_physical_instance_authority_present": False,
        },
    )


def derive_copy_physical_instance_id_v1(
    *,
    source_content_sha256: str,
    target_role: str,
    target_key: str,
    copy_ordinal: int,
) -> str:
    """Deprecated unsafe alias; candidate inputs cannot mint physical evidence."""

    # Validate the legacy arguments so malformed calls still fail deterministically,
    # but never return the structural slot under a physical-instance name.
    derive_copy_structural_target_slot_id_v1(
        source_content_sha256=source_content_sha256,
        target_role=target_role,
        target_key=target_key,
        copy_ordinal=copy_ordinal,
    )
    _fail(
        "deprecated COPY physical-instance derivation is unavailable: use "
        "derive_copy_structural_target_slot_id_v1 for candidate topology only"
    )


def derive_unresolved_bind_target_slot_id_v1(
    *, source_slot_id: str, target_role: str, target_key: str
) -> str:
    """Return a target-distinct BIND slot until native inode/OFD replay exists."""

    _cid(source_slot_id, "unresolved BIND source slot")
    _nonempty(target_role, "unresolved BIND target role")
    _nonempty(target_key, "unresolved BIND target key")
    return _domain_id(
        MOUNT_CATALOGUE_DOMAIN,
        {
            "schema": "acfqp.h1_bind_unresolved_target_slot.v1",
            "source_slot_id": source_slot_id,
            "target_role": target_role,
            "target_key": target_key,
            "native_inode_ofd_evidence_bound": False,
            "cross_target_deduplication_authorized": False,
        },
    )


def derive_bind_physical_instance_id_v1(
    *,
    alias_authority: H1TypedInodeOFDAliasCandidateV1,
    target_key: str,
) -> str:
    """Deprecated physical-ID API; V1 always fails without native evidence."""

    if type(alias_authority) is not H1TypedInodeOFDAliasCandidateV1:
        _fail("BIND sharing requires the exact typed inode/OFD alias candidate")
    retained = _LIVE_ALIASES.get(id(alias_authority))
    if (
        retained is None
        or retained[0] is not alias_authority
        or not hmac.compare_digest(
            retained[1], canonical_json_bytes(alias_authority.to_document())
        )
    ):
        _fail("BIND sharing requires one live issuer-retained alias candidate")
    _nonempty(target_key, "BIND target key")
    if target_key not in alias_authority.target_keys:
        _fail("BIND target is outside the typed inode/OFD alias candidate")
    if alias_authority.runtime_evidence_blocker.evidence_id is None:
        _fail(
            "BIND sharing is forbidden while native inode/OFD evidence remains "
            "REQUIRED_UNBOUND"
        )
    _fail("V1 has no native BIND evidence binder")  # pragma: no cover


@dataclass(frozen=True, slots=True)
class H1PhysicalPayloadV1:
    target_key: str
    target_role: str
    source_slot_id: str
    origin: H1PhysicalOriginV1
    candidate_instance_slot_id: str
    alias_candidate_id: str | None
    extent_blocker: H1TypedNumericBlockerV1

    def __post_init__(self) -> None:
        _nonempty(self.target_key, "physical payload target")
        _nonempty(self.target_role, "physical payload role")
        _cid(self.source_slot_id, "physical payload source slot")
        try:
            object.__setattr__(self, "origin", H1PhysicalOriginV1(self.origin))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1SharedResourceCataloguesV1Error(
                "physical payload origin is invalid"
            ) from error
        _cid(self.candidate_instance_slot_id, "candidate instance slot")
        if self.alias_candidate_id is not None:
            _cid(self.alias_candidate_id, "physical payload alias candidate")
        if type(self.extent_blocker) is not H1TypedNumericBlockerV1:
            _fail("physical payload lacks one typed extent blocker")
        bind_origin = self.origin in {
            H1PhysicalOriginV1.BIND_ALIAS,
            H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET,
        }
        if bind_origin != (self.alias_candidate_id is not None):
            _fail("only a typed BIND payload may carry an alias candidate")
        if self.origin is H1PhysicalOriginV1.BIND_ALIAS:
            _fail("V1 cannot emit a BIND_ALIAS without bound native inode/OFD evidence")

    def to_document(self) -> dict[str, Any]:
        alias_candidate: Any = (
            self.alias_candidate_id
            if self.alias_candidate_id is not None
            else {"kind": "NOT_APPLICABLE", "reason": "NOT_A_BIND_TARGET"}
        )
        bound_alias: Any = (
            {
                "kind": "REQUIRED_UNBOUND",
                "reason": "NATIVE_INODE_OFD_REPLAY_ABSENT",
            }
            if self.origin is H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET
            else {"kind": "NOT_APPLICABLE", "reason": "NOT_A_BIND_TARGET"}
        )
        identity_semantics = {
            H1PhysicalOriginV1.COPY_TARGET: "STRUCTURAL_COPY_TARGET_SLOT_ONLY",
            H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET: (
                "DISTINCT_UNRESOLVED_BIND_TARGET_SLOT"
            ),
            H1PhysicalOriginV1.CREATED_OUTPUT: "STRUCTURAL_OUTPUT_TARGET_SLOT_ONLY",
            H1PhysicalOriginV1.BIND_ALIAS: "NATIVE_ALIAS",  # unreachable in V1
        }[self.origin]
        return {
            "target_key": self.target_key,
            "target_role": self.target_role,
            "source_slot_id": self.source_slot_id,
            "physical_origin": self.origin.value,
            "candidate_instance_slot_id": self.candidate_instance_slot_id,
            "candidate_instance_slot_only": True,
            "typed_inode_ofd_alias_candidate_id": alias_candidate,
            "native_inode_ofd_alias_binding": bound_alias,
            "extent_blocker": self.extent_blocker.to_document(),
            "physical_identity_semantics": identity_semantics,
            "native_physical_instance_authority_present": False,
        }

    @property
    def physical_instance_id(self) -> str:
        """Deprecated unsafe alias; candidate payloads have structural slots."""

        _fail(
            "deprecated payload physical_instance_id is unavailable: use "
            "candidate_instance_slot_id for candidate topology only"
        )

    @property
    def alias_authority_id(self) -> str | None:
        """Deprecated unsafe alias; V1 payloads bind alias candidates only."""

        _fail(
            "deprecated payload alias_authority_id is unavailable: use "
            "alias_candidate_id"
        )


_MOUNT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1PhysicalMountCatalogueV1:
    _issuer: InitVar[object]
    execution_topology_profile_id: str
    output_branch_dag_id: str
    aliases: tuple[H1TypedInodeOFDAliasCandidateV1, ...]
    payloads: tuple[H1PhysicalPayloadV1, ...]
    _catalogue_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _MOUNT_ISSUER:
            _fail("physical mount catalogue candidate is caller-minted")
        topology = topology_v1.official_h1_execution_topology_profile_v1()
        dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
        if (
            self.execution_topology_profile_id != topology.profile_id
            or self.output_branch_dag_id != dag.dag_id
        ):
            _fail("physical mount catalogue crossed topology/output identities")
        expected_aliases, expected_payloads = _mount_inventory(topology)
        if self.aliases != expected_aliases or self.payloads != expected_payloads:
            _fail("physical mount catalogue omitted or changed a target")
        if (
            len({row.target_key for row in self.payloads}) != len(self.payloads)
            or len(self.payloads)
            != EXPECTED_STAGE_SITE_COUNT + EXPECTED_OUTPUT_ROLE_COUNT
        ):
            _fail("physical mount targets must be complete and unique")
        alias_by_id = {row.alias_candidate_id: row for row in self.aliases}
        for payload in self.payloads:
            if payload.origin is H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET:
                alias = alias_by_id.get(payload.alias_candidate_id)
                if (
                    alias is None
                    or payload.target_key not in alias.target_keys
                    or payload.candidate_instance_slot_id
                    == alias.candidate_shared_instance_slot_id
                    or payload.candidate_instance_slot_id
                    != derive_unresolved_bind_target_slot_id_v1(
                        source_slot_id=payload.source_slot_id,
                        target_role=payload.target_role,
                        target_key=payload.target_key,
                    )
                ):
                    _fail("unresolved BIND payload lost its target-distinct slot")
        unresolved_binds = [
            row
            for row in self.payloads
            if row.origin is H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET
        ]
        if len({row.candidate_instance_slot_id for row in unresolved_binds}) != len(
            unresolved_binds
        ):
            _fail("unresolved BIND targets must remain physically distinct")
        copies = [
            row for row in self.payloads if row.origin is H1PhysicalOriginV1.COPY_TARGET
        ]
        if len({row.candidate_instance_slot_id for row in copies}) != len(copies):
            _fail("COPY targets must always have distinct candidate instance slots")
        object.__setattr__(
            self,
            "_catalogue_id",
            _domain_id(MOUNT_CATALOGUE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_physical_mount_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "h1_production_output_branch_dag_id": self.output_branch_dag_id,
            "typed_inode_ofd_alias_candidates": [
                row.to_document() for row in self.aliases
            ],
            "physical_payload_targets": [row.to_document() for row in self.payloads],
            "mount_formula_schema_candidate": (
                "MAX_OVER_BRANCH_TIME_OF_SUM_EXTENTS_BY_DISTINCT_PHYSICAL_INSTANCE"
            ),
            "mount_formula_authority_present": False,
            "admission_schema_candidate": (
                "ONE_UPPER_ADMISSION_PER_TEMPLATE_OPEN_ATTEMPT"
            ),
            "copy_structural_target_slots_are_distinct": True,
            "copy_native_physical_instance_authority_present": False,
            "bind_targets_remain_distinct_until_native_inode_ofd_replay": True,
            "bind_sharing_authorized": False,
            "content_digest_deduplication_allowed": False,
            "interval_sweep_key": "candidate_instance_slot_id",
            "wildcard_allowed": False,
            "missing_as_zero_allowed": False,
            "numeric_extent_authority_present": False,
            "native_physical_instance_authority_present": False,
            "production_mount_interval_authority_present": False,
            "owner_lifecycle_compatible": False,
            "numeric_operand_issued": False,
            "predecision_structural_authority": False,
            "predecision_structural_catalogue_candidate_present": True,
        }

    @property
    def catalogue_id(self) -> str:
        if _domain_id(MOUNT_CATALOGUE_DOMAIN, self._payload()) != self._catalogue_id:
            _fail("physical mount catalogue changed")
        return self._catalogue_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_physical_mount_catalogue_id": self.catalogue_id}

    @property
    def by_target(self) -> dict[str, H1PhysicalPayloadV1]:
        return {row.target_key: row for row in self.payloads}


def _mount_inventory(
    topology: topology_v1.H1ExecutionTopologyProfileV1,
) -> tuple[
    tuple[H1TypedInodeOFDAliasCandidateV1, ...],
    tuple[H1PhysicalPayloadV1, ...],
]:
    runtime_targets = tuple(
        f"sealed-input:{row.role.value}:{row.input_role}"
        for row in topology.sealed_inputs
        if row.input_role == "sealed_runtime_archive"
    )
    runtime_slot = _structural_slot_id("SEALED_INPUT_SOURCE", "sealed_runtime_archive")
    alias = H1TypedInodeOFDAliasCandidateV1(
        _ALIAS_ISSUER,
        "sealed-runtime-archive-same-inode-ofd",
        runtime_slot,
        _structural_slot_id("INODE_IDENTITY", "sealed_runtime_archive"),
        _structural_slot_id("OPEN_FILE_DESCRIPTION", "sealed_runtime_archive"),
        runtime_targets,
        H1TypedEvidenceBlockerV1(
            "bind-alias:sealed-runtime-archive",
            H1EvidenceAuthorityKindV1.INODE_OFD_ALIAS_REPLAY,
            "TYPED_RUNTIME_INODE_OFD_ALIAS_REPLAY",
        ),
    )
    aliases = (alias,)
    rows: list[H1PhysicalPayloadV1] = []
    copy_ordinal = 0
    for grant in topology.sealed_inputs:
        role = grant.role.value
        target_key = f"sealed-input:{role}:{grant.input_role}"
        if grant.input_role == "sealed_runtime_archive":
            source_slot = runtime_slot
            origin = H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET
            physical = derive_unresolved_bind_target_slot_id_v1(
                source_slot_id=source_slot,
                target_role=role,
                target_key=target_key,
            )
            alias_id: str | None = alias.alias_candidate_id
        else:
            copy_ordinal += 1
            source_slot = _structural_slot_id(
                "SEALED_INPUT_SOURCE", role, grant.input_role
            )
            origin = H1PhysicalOriginV1.COPY_TARGET
            # No native bytes or FD exist at catalogue-build time.  This is a
            # target-distinct structural slot, not a content/instance proof.
            physical = _structural_slot_id(
                "COPY_TARGET", role, target_key, str(copy_ordinal)
            )
            alias_id = None
        rows.append(
            H1PhysicalPayloadV1(
                target_key,
                role,
                source_slot,
                origin,
                physical,
                alias_id,
                _blocker(
                    f"extent:{target_key}",
                    H1ExtentAuthorityKindV1.SEALED_INPUT_EXTENT,
                    f"SEALED_INPUT_BYTES:{role}:{grant.input_role}",
                ),
            )
        )
    for role in output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES:
        target_key = f"output-role:{role}"
        source_slot = _structural_slot_id("OUTPUT_ROLE_SLOT", role)
        physical = _domain_id(
            MOUNT_CATALOGUE_DOMAIN,
            {
                "schema": "acfqp.h1_created_output_physical_instance.v1",
                "output_role": role,
                "source_slot_id": source_slot,
            },
        )
        rows.append(
            H1PhysicalPayloadV1(
                target_key,
                "BUSINESS" if role == output_v1.BUSINESS_RESULT_ROLE else "BROKER",
                source_slot,
                H1PhysicalOriginV1.CREATED_OUTPUT,
                physical,
                None,
                _blocker(
                    f"extent:{target_key}",
                    (
                        H1ExtentAuthorityKindV1.BUSINESS_RESULT_EXTENT
                        if role == output_v1.BUSINESS_RESULT_ROLE
                        else H1ExtentAuthorityKindV1.OUTPUT_ROLE_EXTENT
                    ),
                    f"JOINT_OUTPUT_READ_FIXED_POINT_ROLE_EXTENT_REQUIRED:{role}",
                ),
            )
        )
    return aliases, tuple(rows)


class H1IOSiteKindV1(str, Enum):
    SEALED_INPUT_STAGE = "SEALED_INPUT_STAGE"
    SEALED_INPUT_READ = "SEALED_INPUT_READ"
    BUSINESS_RESULT_READ = "BUSINESS_RESULT_READ"
    OUTPUT_ROLE_READBACK = "OUTPUT_ROLE_READBACK"


@dataclass(frozen=True, slots=True)
class H1IOOperationSiteV1:
    site_key: str
    path: str
    kind: H1IOSiteKindV1
    owner_role: str
    target_key: str
    candidate_instance_slot_id: str
    activation_anchor: str
    extent_blocker: H1TypedNumericBlockerV1
    ingress_mode: H1IngressModeV1 | None = None

    def __post_init__(self) -> None:
        _nonempty(self.site_key, "I/O site key")
        if self.path not in {READ_PATH, STAGE_PATH}:
            _fail("I/O site names a non-read/stage path")
        try:
            object.__setattr__(self, "kind", H1IOSiteKindV1(self.kind))
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1SharedResourceCataloguesV1Error(
                "I/O site kind is invalid"
            ) from error
        _nonempty(self.owner_role, "I/O owner role")
        _nonempty(self.target_key, "I/O target key")
        _cid(self.candidate_instance_slot_id, "I/O candidate instance slot")
        _nonempty(self.activation_anchor, "I/O activation anchor")
        if type(self.extent_blocker) is not H1TypedNumericBlockerV1:
            _fail("I/O site lacks one typed extent blocker")
        if self.path == STAGE_PATH:
            try:
                object.__setattr__(self, "ingress_mode", H1IngressModeV1(self.ingress_mode))
            except (TypeError, ValueError) as error:
                raise ConstructionK7H1SharedResourceCataloguesV1Error(
                    "stage site lacks exact COPY/BIND mode"
                ) from error
        elif self.ingress_mode is not None:
            _fail("read site cannot carry a sandbox ingress mode")

    def to_document(self) -> dict[str, Any]:
        mode: Any = (
            self.ingress_mode.value
            if self.ingress_mode is not None
            else {"kind": "NOT_APPLICABLE", "reason": "READ_OPERATION"}
        )
        return {
            "site_key": self.site_key,
            "path": self.path,
            "site_kind": self.kind.value,
            "owner_role": self.owner_role,
            "target_key": self.target_key,
            "candidate_instance_slot_id": self.candidate_instance_slot_id,
            "native_physical_instance_authority_present": False,
            "activation_anchor": self.activation_anchor,
            "sandbox_ingress_mode": mode,
            "extent_blocker": self.extent_blocker.to_document(),
            "multiplicity_semantics": "PRODUCTION_MULTIPLICITY_REQUIRED_UNBOUND",
            "registered_template_candidate_multiplicity_upper": 1,
            "production_activation_authority_present": False,
            "status": "REGISTERED_TEMPLATE_CANDIDATE_ONLY",
        }

    @property
    def physical_instance_id(self) -> str:
        """Deprecated unsafe alias; I/O sites carry candidate slots only."""

        _fail(
            "deprecated I/O physical_instance_id is unavailable: use "
            "candidate_instance_slot_id for candidate topology only"
        )


_IO_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1SharedIOCatalogueV1:
    _issuer: InitVar[object]
    execution_topology_profile_id: str
    output_branch_dag_id: str
    physical_mount_catalogue_id: str
    stage_sites: tuple[H1IOOperationSiteV1, ...]
    read_sites: tuple[H1IOOperationSiteV1, ...]
    _catalogue_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _IO_ISSUER:
            _fail("shared I/O catalogue candidate is caller-minted")
        topology = topology_v1.official_h1_execution_topology_profile_v1()
        dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
        mount = _OFFICIAL_MOUNT
        if (
            self.execution_topology_profile_id != topology.profile_id
            or self.output_branch_dag_id != dag.dag_id
            or self.physical_mount_catalogue_id != mount.catalogue_id
        ):
            _fail("shared I/O catalogue crossed topology/output/mount identities")
        expected_stage, expected_read = _io_sites(topology, mount)
        if self.stage_sites != expected_stage or self.read_sites != expected_read:
            _fail("shared I/O catalogue omitted, reordered, or invented a site")
        if (
            len(self.stage_sites) != EXPECTED_STAGE_SITE_COUNT
            or any(row.path != STAGE_PATH for row in self.stage_sites)
            or any(row.path != READ_PATH for row in self.read_sites)
            or len({row.site_key for row in (*self.stage_sites, *self.read_sites)})
            != len(self.stage_sites) + len(self.read_sites)
        ):
            _fail("shared I/O site universe is incomplete or duplicated")
        object.__setattr__(
            self,
            "_catalogue_id",
            _domain_id(IO_CATALOGUE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_shared_io_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "h1_production_output_branch_dag_id": self.output_branch_dag_id,
            "h1_physical_mount_catalogue_id": self.physical_mount_catalogue_id,
            "stage_sites": [row.to_document() for row in self.stage_sites],
            "read_sites": [row.to_document() for row in self.read_sites],
            "read_formula_schema_candidate": (
                "MAX_BRANCH_SUM_SOURCE_MULTIPLICITY_TIMES_EXTENT"
            ),
            "stage_formula_schema_candidate": (
                "MAX_BRANCH_SUM_SOURCE_MULTIPLICITY_TIMES_EXTENT"
            ),
            "formula_authority_present": False,
            "output_readback_extent_source": "JOINT_OUTPUT_READ_FIXED_POINT",
            "caller_aggregate_allowed": False,
            "wildcard_allowed": False,
            "missing_as_zero_allowed": False,
            "numeric_extent_authority_present": False,
            "production_io_prefix_complete": False,
            "native_activation_source_authority_present": False,
            "numeric_operand_issued": False,
            "predecision_structural_authority": False,
            "predecision_structural_catalogue_candidate_present": True,
        }

    @property
    def catalogue_id(self) -> str:
        if _domain_id(IO_CATALOGUE_DOMAIN, self._payload()) != self._catalogue_id:
            _fail("shared I/O catalogue changed")
        return self._catalogue_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_shared_io_catalogue_id": self.catalogue_id}

    @property
    def stage_by_key(self) -> dict[str, H1IOOperationSiteV1]:
        return {row.site_key: row for row in self.stage_sites}

    @property
    def read_by_key(self) -> dict[str, H1IOOperationSiteV1]:
        return {row.site_key: row for row in self.read_sites}


def _io_sites(
    topology: topology_v1.H1ExecutionTopologyProfileV1,
    mount: H1PhysicalMountCatalogueV1,
) -> tuple[tuple[H1IOOperationSiteV1, ...], tuple[H1IOOperationSiteV1, ...]]:
    stage: list[H1IOOperationSiteV1] = []
    read: list[H1IOOperationSiteV1] = []
    for grant in topology.sealed_inputs:
        role = grant.role.value
        target_key = f"sealed-input:{role}:{grant.input_role}"
        payload = mount.by_target[target_key]
        stage.append(
            H1IOOperationSiteV1(
                f"stage:{role}:{grant.input_role}",
                STAGE_PATH,
                H1IOSiteKindV1.SEALED_INPUT_STAGE,
                "BROKER",
                target_key,
                payload.candidate_instance_slot_id,
                f"BEFORE_{role}_LAUNCH_ATTEMPT",
                payload.extent_blocker,
                (
                    H1IngressModeV1.BIND
                    if payload.origin
                    in {
                        H1PhysicalOriginV1.BIND_ALIAS,
                        H1PhysicalOriginV1.BIND_UNRESOLVED_TARGET,
                    }
                    else H1IngressModeV1.COPY
                ),
            )
        )
        read.append(
            H1IOOperationSiteV1(
                f"read:{role}:{grant.input_role}",
                READ_PATH,
                H1IOSiteKindV1.SEALED_INPUT_READ,
                role,
                target_key,
                payload.candidate_instance_slot_id,
                (
                    "WORKER_READY_AND_BUSINESS_REQUEST_SIGNAL"
                    if role == "WORKER"
                    else "BUSINESS_REQUEST_REPLAYED"
                ),
                payload.extent_blocker,
            )
        )
    result_payload = mount.by_target[f"output-role:{output_v1.BUSINESS_RESULT_ROLE}"]
    result_reads = (
        ("BUSINESS", "BUSINESS_RESULT_COMMITTED"),
        ("BROKER", "BUSINESS_EXITED_AND_REAPED_RESULT_PINNED"),
        ("WORKER", "BUSINESS_RESULT_RELAYED_AND_WORKER_ACKED"),
    )
    for role, anchor in result_reads:
        read.append(
            H1IOOperationSiteV1(
                f"read:business-result:{role}",
                READ_PATH,
                H1IOSiteKindV1.BUSINESS_RESULT_READ,
                role,
                result_payload.target_key,
                result_payload.candidate_instance_slot_id,
                anchor,
                result_payload.extent_blocker,
            )
        )
    for role in output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES:
        payload = mount.by_target[f"output-role:{role}"]
        read.append(
            H1IOOperationSiteV1(
                f"readback:output-role:{role}",
                READ_PATH,
                H1IOSiteKindV1.OUTPUT_ROLE_READBACK,
                payload.target_role,
                payload.target_key,
                payload.candidate_instance_slot_id,
                role,
                payload.extent_blocker,
            )
        )
    return tuple(stage), tuple(read)


@dataclass(frozen=True, slots=True)
class H1SameOFDPeakPlanV1:
    descriptor_role: str
    physical_object: str
    open_file_description: str
    owner_role: str
    open_before_scope_members_join: bool
    read_after_all_descendants_reaped: bool
    _plan_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for name, value in (
            ("descriptor role", self.descriptor_role),
            ("physical object", self.physical_object),
            ("open file description", self.open_file_description),
            ("owner role", self.owner_role),
        ):
            _nonempty(value, name)
        if (
            self.owner_role != "BROKER"
            or self.open_before_scope_members_join is not True
            or self.read_after_all_descendants_reaped is not True
        ):
            _fail("memory peak plan must retain one BROKER-owned OFD end to end")
        object.__setattr__(
            self,
            "_plan_id",
            _domain_id(MEMORY_CANDIDATE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_same_ofd_peak_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "descriptor_role": self.descriptor_role,
            "physical_object": self.physical_object,
            "open_file_description": self.open_file_description,
            "owner_role": self.owner_role,
            "open_before_scope_members_join": self.open_before_scope_members_join,
            "read_after_all_descendants_reaped": (
                self.read_after_all_descendants_reaped
            ),
            "broker_remains_live_to_read_retained_ofd": True,
            "same_open_file_description_required": True,
        }

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_same_ofd_peak_plan_id": self.plan_id}


_MEMORY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1MemoryScopeCandidateV1:
    _issuer: InitVar[object]
    execution_topology_profile_id: str
    members: tuple[str, ...]
    continuous_scope_start: str
    continuous_scope_end: str
    outer_pid_membership_minimum: int
    same_ofd_peak_plan: H1SameOFDPeakPlanV1
    preexecution_numeric_blockers: tuple[H1TypedNumericBlockerV1, ...]
    preexecution_evidence_blockers: tuple[H1TypedEvidenceBlockerV1, ...]
    postrun_actual_blockers: tuple[H1TypedNumericBlockerV1, ...]
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _MEMORY_ISSUER:
            _fail("memory scope candidate is caller-minted")
        topology = topology_v1.official_h1_execution_topology_profile_v1()
        if self.execution_topology_profile_id != topology.profile_id:
            _fail("memory scope candidate crossed the registered execution topology")
        if self.members != ("BROKER", "WORKER", "BUSINESS"):
            _fail("memory scope must continuously cover BROKER+WORKER+BUSINESS")
        if (
            self.continuous_scope_start != "PREDECISION_RESOURCE_SCOPE_ESTABLISHED"
            or self.continuous_scope_end != "FORMAL_ACCOUNTING_CLOSED"
            or self.outer_pid_membership_minimum
            != EXPECTED_OUTER_PID_MEMBERSHIP_MINIMUM
        ):
            _fail("memory scope interval or outer PID floor changed")
        if type(self.same_ofd_peak_plan) is not H1SameOFDPeakPlanV1:
            _fail("memory scope lacks one retained same-OFD peak plan")
        expected_preexecution_keys = (
            "memory-hard-cap",
            "outer-route-wide-cap",
            "broker-parent-cap",
            "worker-role-cap",
            "business-role-cap",
            "outer-pids-max",
        )
        if (
            type(self.preexecution_numeric_blockers) is not tuple
            or tuple(row.blocker_key for row in self.preexecution_numeric_blockers)
            != expected_preexecution_keys
            or any(
                type(row) is not H1TypedNumericBlockerV1
                for row in self.preexecution_numeric_blockers
            )
        ):
            _fail("memory scope preexecution numeric blockers are incomplete")
        if (
            type(self.preexecution_evidence_blockers) is not tuple
            or tuple(row.blocker_key for row in self.preexecution_evidence_blockers)
            != ("outer-cgroup-pid-membership",)
            or any(
                type(row) is not H1TypedEvidenceBlockerV1
                for row in self.preexecution_evidence_blockers
            )
        ):
            _fail("memory scope membership evidence blockers are incomplete")
        if (
            type(self.postrun_actual_blockers) is not tuple
            or tuple(row.blocker_key for row in self.postrun_actual_blockers)
            != ("retained-outer-peak-readback",)
            or any(
                type(row) is not H1TypedNumericBlockerV1
                for row in self.postrun_actual_blockers
            )
        ):
            _fail("memory scope postrun actual blockers are incomplete")
        object.__setattr__(
            self,
            "_candidate_id",
            _domain_id(MEMORY_CANDIDATE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_memory_scope_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "continuous_scope_members": list(self.members),
            "continuous_scope_start": self.continuous_scope_start,
            "continuous_scope_end": self.continuous_scope_end,
            "outer_pid_membership_minimum_candidate": (
                self.outer_pid_membership_minimum
            ),
            "outer_pid_membership_authority_present": False,
            "broker_parent_inside_outer_scope_required_by_candidate": True,
            "worker_business_join_before_native_launch_required_by_candidate": True,
            "descendants_retained_until_trusted_reap_or_cleanup_required_by_candidate": True,
            "broker_retained_through_peak_read_and_accounting_close_required_by_candidate": True,
            "memory_scope_plan_only": True,
            "same_ofd_peak_plan": self.same_ofd_peak_plan.to_document(),
            "formula_schema_when_bound": (
                "MIN_MEMORY_HARD_CAP_OUTER_ROUTE_WIDE_CAP_AND_SUM_BROKER_WORKER_BUSINESS_CAPS"
            ),
            "child_only_outer_scope_is_authoritative": False,
            "child_only_scope_result": "TYPED_BLOCKER_NO_ROUTE_WIDE_AUTHORITY",
            "preexecution_numeric_blockers": [
                row.to_document() for row in self.preexecution_numeric_blockers
            ],
            "preexecution_evidence_blockers": [
                row.to_document() for row in self.preexecution_evidence_blockers
            ],
            "postrun_actual_blockers": [
                row.to_document() for row in self.postrun_actual_blockers
            ],
            "postrun_actual_may_authorize_preexecution_upper": False,
            "numeric_caps_authoritative": False,
            "postrun_peak_receipt_authoritative": False,
            "missing_numeric_value_is_zero": False,
            "numeric_operand_issued": False,
            "predecision_structural_authority": False,
            "predecision_memory_scope_candidate_present": True,
        }

    @property
    def candidate_id(self) -> str:
        if _domain_id(MEMORY_CANDIDATE_DOMAIN, self._payload()) != self._candidate_id:
            _fail("memory scope candidate changed")
        return self._candidate_id

    @property
    def authority_id(self) -> str:
        """Deprecated authority identity; this object is candidate-only."""

        _fail("deprecated memory authority_id is unavailable: use candidate_id")

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_memory_scope_candidate_id": self.candidate_id}


def _memory_candidate(
    topology: topology_v1.H1ExecutionTopologyProfileV1,
) -> H1MemoryScopeCandidateV1:
    peaks = tuple(
        row
        for row in topology.fd_grants
        if row.role.value == "BROKER" and row.descriptor_role == "memory_peak"
    )
    if len(peaks) != 1:
        _fail("execution topology lacks one retained BROKER memory-peak descriptor")
    peak = peaks[0]
    plan = H1SameOFDPeakPlanV1(
        peak.descriptor_role,
        peak.physical_object,
        peak.open_file_description,
        "BROKER",
        True,
        True,
    )
    cap_kind = H1ExtentAuthorityKindV1.CGROUP_CAP_READBACK
    return H1MemoryScopeCandidateV1(
        _MEMORY_ISSUER,
        topology.profile_id,
        ("BROKER", "WORKER", "BUSINESS"),
        "PREDECISION_RESOURCE_SCOPE_ESTABLISHED",
        "FORMAL_ACCOUNTING_CLOSED",
        EXPECTED_OUTER_PID_MEMBERSHIP_MINIMUM,
        plan,
        (
            _blocker("memory-hard-cap", cap_kind, "SHARED_CAP_PROFILE_V2"),
            _blocker("outer-route-wide-cap", cap_kind, "OUTER_CGROUP_MEMORY_MAX_READBACK"),
            _blocker("broker-parent-cap", cap_kind, "BROKER_PARENT_MEMORY_CAP"),
            _blocker("worker-role-cap", cap_kind, "WORKER_CGROUP_MEMORY_CAP"),
            _blocker("business-role-cap", cap_kind, "BUSINESS_CGROUP_MEMORY_CAP"),
            _blocker(
                "outer-pids-max",
                H1ExtentAuthorityKindV1.CGROUP_PIDS_MAX_READBACK,
                "OUTER_CGROUP_PIDS_MAX_READBACK",
            ),
        ),
        (
            H1TypedEvidenceBlockerV1(
                "outer-cgroup-pid-membership",
                H1EvidenceAuthorityKindV1.OUTER_CGROUP_PID_MEMBERSHIP_REPLAY,
                "OUTER_CGROUP_PID_MEMBERSHIP_REPLAY",
            ),
        ),
        (
            _blocker(
                "retained-outer-peak-readback",
                H1ExtentAuthorityKindV1.CGROUP_PEAK_READBACK,
                "RETAINED_SAME_OFD_OUTER_MEMORY_PEAK_READBACK",
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class H1LaunchSiteV1:
    ordinal: int
    role: str
    predecessor_role: str | None
    positive_anchor: str
    ambiguous_anchor: str | None

    def __post_init__(self) -> None:
        _exact_int(self.ordinal, "launch ordinal", minimum=1)
        if self.role not in {"WORKER", "BUSINESS"}:
            _fail("launch site must name WORKER or BUSINESS")
        if self.predecessor_role is not None and self.predecessor_role not in {
            "WORKER",
            "BUSINESS",
        }:
            _fail("launch predecessor role is invalid")
        _nonempty(self.positive_anchor, "positive launch anchor")
        if self.ambiguous_anchor is not None:
            _nonempty(self.ambiguous_anchor, "ambiguous launch anchor")

    @property
    def site_key(self) -> str:
        return f"launch:{self.role}"

    def to_document(self) -> dict[str, Any]:
        ambiguous: Any = (
            self.ambiguous_anchor
            if self.ambiguous_anchor is not None
            else {"kind": "NOT_APPLICABLE", "reason": "NO_REGISTERED_AMBIGUOUS_EDGE"}
        )
        predecessor: Any = (
            self.predecessor_role
            if self.predecessor_role is not None
            else {"kind": "NOT_APPLICABLE", "reason": "FIRST_CHILD_ROLE"}
        )
        return {
            "site_key": self.site_key,
            "ordinal": self.ordinal,
            "role": self.role,
            "predecessor_role": predecessor,
            "positive_anchor": self.positive_anchor,
            "ambiguous_anchor": ambiguous,
            "multiplicity_semantics": "PRODUCTION_LAUNCH_PREFIX_REQUIRED_UNBOUND",
            "registered_template_candidate_multiplicity_upper": 1,
            "native_existence_resolution_authority_status": "REQUIRED_UNBOUND",
            "status": "REGISTERED_LAUNCH_SITE_CANDIDATE_ONLY",
        }


_LAUNCH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1LaunchCatalogueCandidateV1:
    _issuer: InitVar[object]
    execution_topology_profile_id: str
    launch_sites: tuple[H1LaunchSiteV1, ...]
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _LAUNCH_ISSUER:
            _fail("launch catalogue candidate is caller-minted")
        topology = topology_v1.official_h1_execution_topology_profile_v1()
        expected = (
            H1LaunchSiteV1(
                1,
                "WORKER",
                None,
                "WORKER_LAUNCHED",
                "WORKER_LAUNCH_EXISTENCE_AMBIGUOUS",
            ),
            H1LaunchSiteV1(
                2,
                "BUSINESS",
                "WORKER",
                "BUSINESS_LAUNCHED",
                "BUSINESS_LAUNCH_EXISTENCE_AMBIGUOUS",
            ),
        )
        if (
            self.execution_topology_profile_id != topology.profile_id
            or self.launch_sites != expected
            or topology_v1.EXPECTED_CHILD_PROCESS_LAUNCHES != EXPECTED_LAUNCH_COUNT
        ):
            _fail(
                "launch catalogue candidate differs from the registered "
                "WORKER then BUSINESS topology"
            )
        object.__setattr__(
            self,
            "_candidate_id",
            _domain_id(LAUNCH_CANDIDATE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_launch_catalogue_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "launch_sites": [row.to_document() for row in self.launch_sites],
            "registered_child_role_order": ["WORKER", "BUSINESS"],
            "broker_is_parent_and_not_a_child_launch": True,
            "registered_child_launch_count_upper": EXPECTED_LAUNCH_COUNT,
            "production_launch_prefix_authority_present": False,
            "worker_ambiguity_template_context_present": True,
            "business_ambiguity_template_context_present": False,
            "production_ambiguity_context_coverage_complete": False,
            "missing_production_contexts": [
                "BUSINESS_LAUNCH_EXISTENCE_AMBIGUOUS"
            ],
            "caller_launch_total_allowed": False,
            "wildcard_allowed": False,
            "missing_as_zero_allowed": False,
            "numeric_route_operand_issued": False,
            "predecision_structural_authority": False,
            "predecision_launch_catalogue_candidate_present": True,
        }

    @property
    def candidate_id(self) -> str:
        if _domain_id(LAUNCH_CANDIDATE_DOMAIN, self._payload()) != self._candidate_id:
            _fail("launch catalogue candidate changed")
        return self._candidate_id

    @property
    def authority_id(self) -> str:
        """Deprecated authority identity; this object is candidate-only."""

        _fail("deprecated launch authority_id is unavailable: use candidate_id")

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_launch_catalogue_candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class H1ExplicitSitePartitionV1:
    path: str
    reachable_site_prefix: tuple[str, ...]
    typed_unreachable_site_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.path not in STRUCTURAL_PATHS:
            _fail("branch site partition names an unknown structural path")
        _unique_tuple(
            self.reachable_site_prefix,
            "reachable site prefix",
            allow_empty=True,
        )
        _unique_tuple(
            self.typed_unreachable_site_keys,
            "typed unreachable site keys",
            allow_empty=True,
        )
        if set(self.reachable_site_prefix) & set(self.typed_unreachable_site_keys):
            _fail("branch site cannot be both reachable and typed unreachable")

    def to_document(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "reachable_site_prefix": list(self.reachable_site_prefix),
            "typed_unreachable_site_keys": list(self.typed_unreachable_site_keys),
            "partition_semantics": "REGISTERED_TEMPLATE_CANDIDATE_ONLY",
            "production_reachability_authority_present": False,
            "candidate_reachable_multiplicity_upper": 1,
            "candidate_unreachable_multiplicity_lower": 0,
            "production_zero_authorized": False,
            "missing_as_zero_allowed": False,
            "wildcard_allowed": False,
        }


@dataclass(frozen=True, slots=True)
class H1BranchMountIntervalV1:
    interval_key: str
    target_key: str
    candidate_instance_slot_id: str
    open_sequence: int
    close_sequence: int
    extent_blocker_key: str

    def __post_init__(self) -> None:
        _nonempty(self.interval_key, "mount interval key")
        _nonempty(self.target_key, "mount interval target")
        _cid(self.candidate_instance_slot_id, "mount interval candidate instance slot")
        _exact_int(self.open_sequence, "mount open sequence", minimum=1)
        _exact_int(self.close_sequence, "mount close sequence", minimum=1)
        if self.close_sequence <= self.open_sequence:
            _fail("mount interval must close strictly after it opens")
        _nonempty(self.extent_blocker_key, "mount interval extent blocker")

    def to_document(self) -> dict[str, Any]:
        return {
            "interval_key": self.interval_key,
            "target_key": self.target_key,
            "candidate_instance_slot_id": self.candidate_instance_slot_id,
            "native_physical_instance_authority_present": False,
            "open_sequence": self.open_sequence,
            "close_sequence": self.close_sequence,
            "extent_blocker_key": self.extent_blocker_key,
            "open_attempt_multiplicity_upper_candidate": 1,
            "production_interval_authority_present": False,
            "shared_cap_owner_lifecycle_compatible": False,
            "status": "HANDWRITTEN_TEMPLATE_INTERVAL_CANDIDATE_ONLY",
        }

    @property
    def physical_instance_id(self) -> str:
        """Deprecated unsafe alias; candidate intervals have slots only."""

        _fail(
            "deprecated interval physical_instance_id is unavailable: use "
            "candidate_instance_slot_id for candidate topology only"
        )


@dataclass(frozen=True, slots=True)
class H1MountSweepStateV1:
    sequence: int
    active_candidate_instance_slot_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _exact_int(self.sequence, "mount sweep sequence", minimum=1)
        _unique_tuple(
            self.active_candidate_instance_slot_ids,
            "active candidate instance slot IDs",
            allow_empty=True,
        )
        for value in self.active_candidate_instance_slot_ids:
            _cid(value, "active candidate instance slot")

    def to_document(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "active_candidate_instance_slot_ids": list(
                self.active_candidate_instance_slot_ids
            ),
            "same_candidate_slot_counted_once_at_sequence": True,
            "native_physical_instance_authority_present": False,
        }

    @property
    def active_physical_instance_ids(self) -> tuple[str, ...]:
        """Deprecated unsafe alias; the sweep has candidate slots only."""

        _fail(
            "deprecated active_physical_instance_ids is unavailable: use "
            "active_candidate_instance_slot_ids for candidate topology only"
        )


def sweep_physical_mount_intervals_v1(
    intervals: tuple[H1BranchMountIntervalV1, ...],
) -> tuple[H1MountSweepStateV1, ...]:
    """Sweep interval endpoints with reference counts keyed by physical ID."""

    if type(intervals) is not tuple or any(
        type(row) is not H1BranchMountIntervalV1 for row in intervals
    ):
        _fail("mount interval sweep requires one exact interval tuple")
    events: dict[int, list[tuple[int, str]]] = {}
    for row in intervals:
        events.setdefault(row.open_sequence, []).append(
            (1, row.candidate_instance_slot_id)
        )
        events.setdefault(row.close_sequence, []).append(
            (-1, row.candidate_instance_slot_id)
        )
    active: dict[str, int] = {}
    states: list[H1MountSweepStateV1] = []
    for sequence in sorted(events):
        # Half-open [open, close): close before open at the same sequence.
        for delta, physical in sorted(events[sequence], key=lambda item: item[0]):
            if delta < 0:
                count = active.get(physical, 0)
                if count <= 0:
                    _fail("mount interval sweep closed an inactive candidate slot")
                if count == 1:
                    active.pop(physical)
                else:
                    active[physical] = count - 1
            else:
                active[physical] = active.get(physical, 0) + 1
        states.append(H1MountSweepStateV1(sequence, tuple(sorted(active))))
    if active:
        _fail("mount interval sweep ended with active candidate slots")
    return tuple(states)


@dataclass(frozen=True, slots=True)
class H1BranchResourceProgramRowV1:
    branch_key: str
    context_kind: str
    runtime_event_prefix: tuple[str, ...]
    output_role_prefix: tuple[str, ...]
    finalization_status: str
    site_partitions: tuple[H1ExplicitSitePartitionV1, ...]
    mount_intervals: tuple[H1BranchMountIntervalV1, ...]
    mount_sweep: tuple[H1MountSweepStateV1, ...]
    output_admission_upper_candidate: int
    memory_admission_upper_candidate: int

    def __post_init__(self) -> None:
        _nonempty(self.branch_key, "branch key")
        _nonempty(self.context_kind, "branch context kind")
        _unique_tuple(self.runtime_event_prefix, "runtime event prefix")
        _unique_tuple(
            self.output_role_prefix, "output role prefix", allow_empty=True
        )
        _nonempty(self.finalization_status, "branch finalization status")
        if (
            type(self.site_partitions) is not tuple
            or tuple(row.path for row in self.site_partitions) != STRUCTURAL_PATHS
            or any(type(row) is not H1ExplicitSitePartitionV1 for row in self.site_partitions)
        ):
            _fail("branch must carry the exact seven structural path partitions")
        if type(self.mount_intervals) is not tuple or any(
            type(row) is not H1BranchMountIntervalV1 for row in self.mount_intervals
        ):
            _fail("branch mount intervals are malformed")
        if self.mount_sweep != sweep_physical_mount_intervals_v1(self.mount_intervals):
            _fail("branch mount sweep is not the candidate-slot interval replay")
        if (
            self.output_admission_upper_candidate != 1
            or self.memory_admission_upper_candidate != 1
        ):
            _fail("every H1 template branch carries 0..1 admission candidates")

    def to_document(self) -> dict[str, Any]:
        return {
            "branch_key": self.branch_key,
            "context_kind": self.context_kind,
            "runtime_event_prefix": list(self.runtime_event_prefix),
            "output_role_prefix": list(self.output_role_prefix),
            "finalization_status": self.finalization_status,
            "site_partitions": [row.to_document() for row in self.site_partitions],
            "mount_intervals": [row.to_document() for row in self.mount_intervals],
            "mount_sweep": [row.to_document() for row in self.mount_sweep],
            "mount_sweep_reducer": (
                "MAX_OVER_SEQUENCE_SUM_EXTENTS_OF_DISTINCT_PHYSICAL_INSTANCE_IDS"
            ),
            "mount_sweep_status": "HANDWRITTEN_TEMPLATE_CANDIDATE_ONLY",
            "owner_lifecycle_compatible": False,
            "output_admission_candidate": {
                "lower": 0,
                "upper": self.output_admission_upper_candidate,
                "status": "PRODUCTION_BRANCH_SOURCE_REQUIRED_UNBOUND",
            },
            "output_extent_source": "JOINT_OUTPUT_READ_FIXED_POINT_REQUIRED_UNBOUND",
            "memory_admission_candidate": {
                "lower": 0,
                "upper": self.memory_admission_upper_candidate,
                "status": "PRODUCTION_BRANCH_SOURCE_REQUIRED_UNBOUND",
            },
            "production_resource_prefix_complete": False,
            "numeric_operand_issued": False,
        }


def _partition(
    path: str,
    all_keys: tuple[str, ...],
    reachable: Iterable[str],
) -> H1ExplicitSitePartitionV1:
    reachable_set = set(reachable)
    if not reachable_set <= set(all_keys):
        _fail("branch reachability named a site outside its exact catalogue")
    yes = tuple(key for key in all_keys if key in reachable_set)
    no = tuple(key for key in all_keys if key not in reachable_set)
    if set(yes) | set(no) != set(all_keys) or len(yes) + len(no) != len(all_keys):
        _fail("branch site partition is not complete")
    return H1ExplicitSitePartitionV1(path, yes, no)


def _context_has_any(context: output_v1.H1ProductionOutputBranchContextV1, *events: str) -> bool:
    return bool(set(events) & set(context.runtime_path))


def _worker_stage_reached(context: output_v1.H1ProductionOutputBranchContextV1) -> bool:
    return _context_has_any(
        context,
        "WORKER_LAUNCHED",
        "WORKER_LAUNCH_EXISTENCE_AMBIGUOUS",
        "WORKER_READY_AND_BUSINESS_REQUEST_SIGNAL",
        "BUSINESS_LAUNCHED",
        "BUSINESS_REQUEST_REPLAYED",
        "OWNED_SEARCH_FINISHED",
        "BUSINESS_RESULT_COMMITTED",
    )


def _business_stage_reached(context: output_v1.H1ProductionOutputBranchContextV1) -> bool:
    return _context_has_any(
        context,
        "BUSINESS_LAUNCHED",
        "BUSINESS_REQUEST_REPLAYED",
        "OWNED_SEARCH_FINISHED",
        "BUSINESS_RESULT_COMMITTED",
        "BUSINESS_ADAPTER_FAILED_BEFORE_RESULT_COMMIT",
    )


def _stage_reached(
    site: H1IOOperationSiteV1,
    context: output_v1.H1ProductionOutputBranchContextV1,
) -> bool:
    payload_role = site.target_key.split(":", 2)[1]
    return (
        _worker_stage_reached(context)
        if payload_role == "WORKER"
        else _business_stage_reached(context)
    )


def _read_reached(
    site: H1IOOperationSiteV1,
    context: output_v1.H1ProductionOutputBranchContextV1,
    leaf: output_v1.H1ProductionOutputBranchLeafV1,
) -> bool:
    if site.kind is H1IOSiteKindV1.OUTPUT_ROLE_READBACK:
        return site.activation_anchor in leaf.present_roles
    return site.activation_anchor in context.runtime_path


def _launch_reached(
    site: H1LaunchSiteV1,
    context: output_v1.H1ProductionOutputBranchContextV1,
) -> bool:
    return site.positive_anchor in context.runtime_path or (
        site.ambiguous_anchor is not None
        and site.ambiguous_anchor in context.runtime_path
    )


def _common_reached(
    site: H1CommonSiteV1,
    context: output_v1.H1ProductionOutputBranchContextV1,
    leaf: output_v1.H1ProductionOutputBranchLeafV1,
) -> bool:
    if site.anchor_kind is H1AnchorKindV1.RUNTIME_EVENT:
        return site.anchor_key in context.runtime_path
    if site.anchor_kind is H1AnchorKindV1.OUTPUT_ROLE:
        return site.anchor_key in leaf.present_roles
    return site.anchor_key == leaf.finalization_status.value


def _branch_mount_intervals(
    context: output_v1.H1ProductionOutputBranchContextV1,
    leaf: output_v1.H1ProductionOutputBranchLeafV1,
    io: H1SharedIOCatalogueV1,
    mount: H1PhysicalMountCatalogueV1,
) -> tuple[H1BranchMountIntervalV1, ...]:
    rows: list[H1BranchMountIntervalV1] = []
    worker_ready = "WORKER_READY_AND_BUSINESS_REQUEST_SIGNAL" in context.runtime_path
    result_committed = "BUSINESS_RESULT_COMMITTED" in context.runtime_path
    worker_index = 0
    business_index = 0
    for site in io.stage_sites:
        if not _stage_reached(site, context):
            continue
        role = site.target_key.split(":", 2)[1]
        if role == "WORKER":
            worker_index += 1
            open_sequence = 10 + worker_index
            close_sequence = 100 if worker_ready else 900
        else:
            business_index += 1
            open_sequence = 200 + business_index
            close_sequence = 400 if result_committed else 900
        payload = mount.by_target[site.target_key]
        rows.append(
            H1BranchMountIntervalV1(
                f"{leaf.branch_key}:{payload.target_key}",
                payload.target_key,
                payload.candidate_instance_slot_id,
                open_sequence,
                close_sequence,
                payload.extent_blocker.blocker_key,
            )
        )
    for index, role in enumerate(output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES, start=1):
        if role not in leaf.present_roles:
            continue
        payload = mount.by_target[f"output-role:{role}"]
        rows.append(
            H1BranchMountIntervalV1(
                f"{leaf.branch_key}:{payload.target_key}",
                payload.target_key,
                payload.candidate_instance_slot_id,
                450 if role == output_v1.BUSINESS_RESULT_ROLE else 500 + index,
                1000,
                payload.extent_blocker.blocker_key,
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.open_sequence, row.target_key)))


def _branch_row(
    leaf: output_v1.H1ProductionOutputBranchLeafV1,
    dag: output_v1.H1ProductionOutputBranchDAGV1,
    common: H1SharedCommonCatalogueV1,
    io: H1SharedIOCatalogueV1,
    mount: H1PhysicalMountCatalogueV1,
    launch: H1LaunchCatalogueCandidateV1,
) -> H1BranchResourceProgramRowV1:
    context = dag.context_by_kind[leaf.context_kind]
    common_partitions = []
    for path in COMMON_PATHS:
        rows = tuple(row for row in common.sites if row.path == path)
        common_partitions.append(
            _partition(
                path,
                tuple(row.site_key for row in rows),
                tuple(
                    row.site_key
                    for row in rows
                    if _common_reached(row, context, leaf)
                ),
            )
        )
    read_keys = tuple(row.site_key for row in io.read_sites)
    stage_keys = tuple(row.site_key for row in io.stage_sites)
    launch_keys = tuple(row.site_key for row in launch.launch_sites)
    mount_keys = tuple(row.target_key for row in mount.payloads)
    intervals = _branch_mount_intervals(context, leaf, io, mount)
    partitions = (
        *common_partitions,
        _partition(
            READ_PATH,
            read_keys,
            tuple(
                row.site_key
                for row in io.read_sites
                if _read_reached(row, context, leaf)
            ),
        ),
        _partition(
            STAGE_PATH,
            stage_keys,
            tuple(
                row.site_key
                for row in io.stage_sites
                if _stage_reached(row, context)
            ),
        ),
        _partition(
            MOUNT_PATH,
            mount_keys,
            tuple(row.target_key for row in intervals),
        ),
        _partition(
            LAUNCH_PATH,
            launch_keys,
            tuple(
                row.site_key
                for row in launch.launch_sites
                if _launch_reached(row, context)
            ),
        ),
    )
    return H1BranchResourceProgramRowV1(
        leaf.branch_key,
        leaf.context_kind.value,
        context.runtime_path,
        leaf.present_roles,
        leaf.finalization_status.value,
        partitions,
        intervals,
        sweep_physical_mount_intervals_v1(intervals),
        1,
        1,
    )


_PROGRAM_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1SharedResourceBranchProgramV1:
    _issuer: InitVar[object]
    output_branch_dag_id: str
    execution_topology_profile_id: str
    counter_registry_id: str
    stage_profile_id: str
    common_catalogue: H1SharedCommonCatalogueV1
    io_catalogue: H1SharedIOCatalogueV1
    mount_catalogue: H1PhysicalMountCatalogueV1
    memory_candidate: H1MemoryScopeCandidateV1
    launch_candidate: H1LaunchCatalogueCandidateV1
    branches: tuple[H1BranchResourceProgramRowV1, ...]
    _program_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROGRAM_ISSUER:
            _fail("shared-resource branch-program candidate is caller-minted")
        dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
        topology = topology_v1.official_h1_execution_topology_profile_v1()
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        if (
            self.output_branch_dag_id != dag.dag_id
            or self.execution_topology_profile_id != topology.profile_id
            or self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
            or len(dag.contexts) != EXPECTED_CONTEXT_COUNT
            or len(dag.leaves) != EXPECTED_BRANCH_COUNT
        ):
            _fail("shared-resource candidate crossed its registered source identities")
        if (
            self.common_catalogue is not _OFFICIAL_COMMON
            or self.io_catalogue is not _OFFICIAL_IO
            or self.mount_catalogue is not _OFFICIAL_MOUNT
            or self.memory_candidate is not _REGISTERED_MEMORY_CANDIDATE
            or self.launch_candidate is not _REGISTERED_LAUNCH_CANDIDATE
        ):
            _fail("shared-resource candidate requires issuer-owned catalogues")
        expected = tuple(
            _branch_row(
                leaf,
                dag,
                self.common_catalogue,
                self.io_catalogue,
                self.mount_catalogue,
                self.launch_candidate,
            )
            for leaf in dag.leaves
        )
        if (
            self.branches != expected
            or tuple(row.branch_key for row in self.branches)
            != tuple(leaf.branch_key for leaf in dag.leaves)
            or len({row.branch_key for row in self.branches}) != EXPECTED_BRANCH_COUNT
        ):
            _fail("shared-resource candidate omitted or changed a template DAG leaf")
        payload = self._payload()
        _reject_forbidden_keys(payload)
        object.__setattr__(
            self,
            "_program_id",
            _domain_id(BRANCH_PROGRAM_DOMAIN, payload),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_shared_resource_branch_program.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_production_output_branch_dag_id": self.output_branch_dag_id,
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "catalogues": {
                "common": self.common_catalogue.to_document(),
                "io": self.io_catalogue.to_document(),
                "mount": self.mount_catalogue.to_document(),
                "memory": self.memory_candidate.to_document(),
                "launch": self.launch_candidate.to_document(),
            },
            "branches": [row.to_document() for row in self.branches],
            "context_count": EXPECTED_CONTEXT_COUNT,
            "branch_count": EXPECTED_BRANCH_COUNT,
            "all_preregistered_serializer_template_leaves_bound_once": True,
            "native_branch_source_authority_present": False,
            "production_lifecycle_derived": False,
            "registered_template_partition_totality_present": True,
            "production_resource_prefix_complete": False,
            "production_branch_program_authority_present": False,
            "common_source_multiplicity_authority_present": False,
            "io_failure_prefix_authority_present": False,
            "mount_owner_lifecycle_compatible": False,
            "launch_ambiguity_coverage_complete": False,
            "native_physical_instance_authority_present": False,
            "typed_unbound_production_blockers": [
                "COMMON_SOURCE_SYMBOL_MULTIPLICITIES",
                "PER_ADMISSION_IO_FAILURE_PREFIXES",
                "OWNER_COMPATIBLE_MOUNT_INTERVALS",
                "NATIVE_COPY_AND_BIND_PHYSICAL_IDENTITIES",
                "BUSINESS_LAUNCH_EXISTENCE_AMBIGUITY",
                "PREEXECUTION_EXTENTS_AND_CAPS",
                "OUTER_CGROUP_PIDS_MAX_AND_MEMBERSHIP",
                "JOINT_OUTPUT_READ_FIXED_POINT",
                "POSTRUN_SAME_OFD_PEAK_RECEIPT",
            ],
            "caller_aggregate_allowed": False,
            "wildcard_allowed": False,
            "missing_as_zero_allowed": False,
            "numeric_shared_operand_issued": False,
            "predecision_structural_authority": False,
            "predecision_structural_catalogue_candidate_present": True,
            "formal_v7_authority_present": False,
            "route_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def program_id(self) -> str:
        if _domain_id(BRANCH_PROGRAM_DOMAIN, self._payload()) != self._program_id:
            _fail("shared-resource branch program changed")
        return self._program_id

    def to_document(self) -> dict[str, Any]:
        document = {
            **self._payload(),
            "h1_shared_resource_branch_program_id": self.program_id,
        }
        _reject_forbidden_keys(document)
        return document

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    @property
    def by_branch_key(self) -> dict[str, H1BranchResourceProgramRowV1]:
        return {row.branch_key: row for row in self.branches}


_DAG = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
_TOPOLOGY = topology_v1.official_h1_execution_topology_profile_v1()
_REGISTRY = registry_v6.official_counter_registry_v6()
_STAGE = registry_v6.official_stage_profile_v6(_REGISTRY)

_OFFICIAL_COMMON = H1SharedCommonCatalogueV1(
    _COMMON_ISSUER, _DAG.dag_id, _common_sites(_DAG)
)
_ALIASES, _PAYLOADS = _mount_inventory(_TOPOLOGY)
_OFFICIAL_MOUNT = H1PhysicalMountCatalogueV1(
    _MOUNT_ISSUER,
    _TOPOLOGY.profile_id,
    _DAG.dag_id,
    _ALIASES,
    _PAYLOADS,
)
_STAGE_SITES, _READ_SITES = _io_sites(_TOPOLOGY, _OFFICIAL_MOUNT)
_OFFICIAL_IO = H1SharedIOCatalogueV1(
    _IO_ISSUER,
    _TOPOLOGY.profile_id,
    _DAG.dag_id,
    _OFFICIAL_MOUNT.catalogue_id,
    _STAGE_SITES,
    _READ_SITES,
)
_REGISTERED_MEMORY_CANDIDATE = _memory_candidate(_TOPOLOGY)
_REGISTERED_LAUNCH_CANDIDATE = H1LaunchCatalogueCandidateV1(
    _LAUNCH_ISSUER,
    _TOPOLOGY.profile_id,
    (
        H1LaunchSiteV1(
            1,
            "WORKER",
            None,
            "WORKER_LAUNCHED",
            "WORKER_LAUNCH_EXISTENCE_AMBIGUOUS",
        ),
        H1LaunchSiteV1(
            2,
            "BUSINESS",
            "WORKER",
            "BUSINESS_LAUNCHED",
            "BUSINESS_LAUNCH_EXISTENCE_AMBIGUOUS",
        ),
    ),
)
_BRANCHES = tuple(
    _branch_row(
        leaf,
        _DAG,
        _OFFICIAL_COMMON,
        _OFFICIAL_IO,
        _OFFICIAL_MOUNT,
        _REGISTERED_LAUNCH_CANDIDATE,
    )
    for leaf in _DAG.leaves
)
_OFFICIAL_PROGRAM = H1SharedResourceBranchProgramV1(
    _PROGRAM_ISSUER,
    _DAG.dag_id,
    _TOPOLOGY.profile_id,
    _REGISTRY.registry_id,
    _STAGE.stage_profile_id,
    _OFFICIAL_COMMON,
    _OFFICIAL_IO,
    _OFFICIAL_MOUNT,
    _REGISTERED_MEMORY_CANDIDATE,
    _REGISTERED_LAUNCH_CANDIDATE,
    _BRANCHES,
)


def registered_h1_shared_common_catalogue_candidate_v1() -> H1SharedCommonCatalogueV1:
    _ = _OFFICIAL_COMMON.catalogue_id
    return _OFFICIAL_COMMON


def registered_h1_shared_io_catalogue_candidate_v1() -> H1SharedIOCatalogueV1:
    _ = _OFFICIAL_IO.catalogue_id
    return _OFFICIAL_IO


def registered_h1_physical_mount_catalogue_candidate_v1() -> H1PhysicalMountCatalogueV1:
    _ = _OFFICIAL_MOUNT.catalogue_id
    return _OFFICIAL_MOUNT


def registered_h1_memory_scope_candidate_v1() -> H1MemoryScopeCandidateV1:
    _ = _REGISTERED_MEMORY_CANDIDATE.candidate_id
    return _REGISTERED_MEMORY_CANDIDATE


def registered_h1_launch_catalogue_candidate_v1() -> H1LaunchCatalogueCandidateV1:
    _ = _REGISTERED_LAUNCH_CANDIDATE.candidate_id
    return _REGISTERED_LAUNCH_CANDIDATE


def registered_h1_shared_resource_branch_program_candidate_v1(
) -> H1SharedResourceBranchProgramV1:
    _ = _OFFICIAL_PROGRAM.program_id
    return _OFFICIAL_PROGRAM


def verify_h1_shared_resource_branch_program_candidate_bytes_v1(
    raw: bytes,
) -> H1SharedResourceBranchProgramV1:
    """Accept only the exact canonical registered-template candidate bytes."""

    if type(raw) is not bytes or not raw:
        _fail("shared-resource branch program must be nonempty exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1SharedResourceCataloguesV1Error(
            "shared-resource branch program is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("shared-resource branch program is not one canonical object")
    _reject_forbidden_keys(document)
    expected = _OFFICIAL_PROGRAM.canonical_bytes
    if not hmac.compare_digest(raw, expected):
        _fail("shared-resource branch program differs from the registered candidate")
    return _OFFICIAL_PROGRAM


def _deprecated_authority_api(name: str) -> NoReturn:
    _fail(
        f"deprecated authority API {name} is unavailable; use an explicit "
        "registered_*_candidate_v1 API"
    )


def H1MemoryScopeAuthorityV1(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Deprecated authority constructor; V1 has a memory candidate only."""

    _deprecated_authority_api("H1MemoryScopeAuthorityV1")


def H1LaunchAuthorityV1(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Deprecated authority constructor; V1 has a launch candidate only."""

    _deprecated_authority_api("H1LaunchAuthorityV1")


# Compatibility names fail closed.  Returning a candidate through an
# authority-shaped or ``official_*`` API would erase the semantic demotion.
def official_h1_shared_common_catalogue_v1() -> NoReturn:
    """Deprecated official API; it never returns a candidate."""

    _deprecated_authority_api("official_h1_shared_common_catalogue_v1")


def official_h1_shared_io_catalogue_v1() -> NoReturn:
    """Deprecated official API; it never returns a candidate."""

    _deprecated_authority_api("official_h1_shared_io_catalogue_v1")


def official_h1_physical_mount_catalogue_v1() -> NoReturn:
    """Deprecated official API; it never returns a candidate."""

    _deprecated_authority_api("official_h1_physical_mount_catalogue_v1")


def official_h1_memory_scope_authority_v1() -> NoReturn:
    """Deprecated authority API; it never returns a candidate."""

    _deprecated_authority_api("official_h1_memory_scope_authority_v1")


def official_h1_launch_authority_v1() -> NoReturn:
    """Deprecated authority API; it never returns a candidate."""

    _deprecated_authority_api("official_h1_launch_authority_v1")


def official_h1_shared_resource_branch_program_v1() -> NoReturn:
    """Deprecated official API; it never returns a candidate."""

    _deprecated_authority_api("official_h1_shared_resource_branch_program_v1")


def verify_h1_shared_resource_branch_program_bytes_v1(
    raw: bytes,
) -> NoReturn:
    """Deprecated verifier API; it never promotes candidate bytes."""

    if type(raw) is not bytes:
        _fail("deprecated verifier requires exact bytes before failing closed")
    _deprecated_authority_api("verify_h1_shared_resource_branch_program_bytes_v1")


__all__ = (
    "COMMON_PATHS",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7H1SharedResourceCataloguesV1Error",
    "EXPECTED_BRANCH_COUNT",
    "EXPECTED_CONTEXT_COUNT",
    "EXPECTED_LAUNCH_COUNT",
    "EXPECTED_OUTER_PID_MEMBERSHIP_MINIMUM",
    "EXPECTED_OUTPUT_ROLE_COUNT",
    "EXPECTED_STAGE_SITE_COUNT",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "FORBIDDEN_FUTURE_FIELDS",
    "H1AnchorKindV1",
    "H1BranchMountIntervalV1",
    "H1BranchResourceProgramRowV1",
    "H1ExplicitSitePartitionV1",
    "H1EvidenceAuthorityKindV1",
    "H1ExtentAuthorityKindV1",
    "H1IngressModeV1",
    "H1IOOperationSiteV1",
    "H1IOSiteKindV1",
    "H1LaunchCatalogueCandidateV1",
    "H1LaunchAuthorityV1",
    "H1LaunchSiteV1",
    "H1MemoryScopeCandidateV1",
    "H1MemoryScopeAuthorityV1",
    "H1MountSweepStateV1",
    "H1PhysicalMountCatalogueV1",
    "H1PhysicalOriginV1",
    "H1PhysicalPayloadV1",
    "H1SameOFDPeakPlanV1",
    "H1SharedCommonCatalogueV1",
    "H1SharedIOCatalogueV1",
    "H1SharedResourceBranchProgramV1",
    "H1TypedInodeOFDAliasCandidateV1",
    "H1TypedInodeOFDAliasAuthorityV1",
    "H1TypedEvidenceBlockerV1",
    "H1TypedNumericBlockerV1",
    "MOUNT_PATH",
    "MEMORY_CANDIDATE_DOMAIN",
    "LAUNCH_CANDIDATE_DOMAIN",
    "NUMERIC_SHARED_OPERAND_ISSUED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OUTPUT_PATH",
    "PREDECISION_STRUCTURAL_AUTHORITY",
    "PREDECISION_STRUCTURAL_CATALOGUE_CANDIDATE_PRESENT",
    "PRODUCTION_BRANCH_PROGRAM_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READ_PATH",
    "ROUTE_EXECUTION_AUTHORIZED",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "STAGE_PATH",
    "STRUCTURAL_PATHS",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "derive_bind_physical_instance_id_v1",
    "derive_copy_physical_instance_id_v1",
    "derive_copy_structural_target_slot_id_v1",
    "derive_unresolved_bind_target_slot_id_v1",
    "official_h1_launch_authority_v1",
    "official_h1_memory_scope_authority_v1",
    "official_h1_physical_mount_catalogue_v1",
    "official_h1_shared_common_catalogue_v1",
    "official_h1_shared_io_catalogue_v1",
    "official_h1_shared_resource_branch_program_v1",
    "registered_h1_launch_catalogue_candidate_v1",
    "registered_h1_memory_scope_candidate_v1",
    "registered_h1_physical_mount_catalogue_candidate_v1",
    "registered_h1_shared_common_catalogue_candidate_v1",
    "registered_h1_shared_io_catalogue_candidate_v1",
    "registered_h1_shared_resource_branch_program_candidate_v1",
    "sweep_physical_mount_intervals_v1",
    "verify_h1_shared_resource_branch_program_bytes_v1",
    "verify_h1_shared_resource_branch_program_candidate_bytes_v1",
)
