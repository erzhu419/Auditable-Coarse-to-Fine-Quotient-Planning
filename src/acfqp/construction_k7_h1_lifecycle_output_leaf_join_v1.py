"""Construction-only join from H1 output leaves to lifecycle readback sites.

Contract 2.0.59-D closes one structural gap left by the anchored 62-site
lifecycle dispatcher.  The registered production-output candidate contains
ten terminal contexts and ninety leaves, while lifecycle sites 53--60 contain
one ``OUTPUT_ROLE_READBACK`` transition for each of the eight registered
durable roles.  This module derives and content-addresses the exact Cartesian
join between those two *candidate* objects.

The join is intentionally not an output authority.  It says which lifecycle
readback site would be selected for each role that is present in a registered
leaf, and records an explicit typed skip for every absent role.  It does not
observe a durable commit, choose the runtime terminal context, bind live
callbacks, prove parser/serializer semantics, or close the coupled
``(io.output_bytes, io.read_bytes)`` fixed point.  Those absences remain
machine-readable locks rather than being inferred from the ninety-row table.
The current linear dispatcher also has no leaf-bound skip/advance event for an
absent role, so the typed skips are not executable lifecycle transitions.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hmac
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_anchored_lifecycle_dispatch_v1 as dispatch_v1
from acfqp import construction_k7_h1_production_output_upper_v1 as output_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_LIFECYCLE_OUTPUT_LEAF_JOIN_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-D"
PROFILE_KEY = "construction_k7_h1_lifecycle_output_leaf_join_v1"

OUTPUT_LEAF_JOIN_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_OUTPUT_LEAF_JOIN_V1_DOMAIN
if OUTPUT_LEAF_JOIN_DOMAIN not in PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("H1 lifecycle output-leaf join domain is not registered")

EXPECTED_CONTEXT_COUNT = 10
EXPECTED_LEAF_COUNT = 90
EXPECTED_OUTPUT_ROLE_COUNT = 8
EXPECTED_ROLE_PRESENCE_SET_COUNT = 16
EXPECTED_READBACK_ORDINALS = tuple(range(53, 61))

REGISTERED_ROLE_PRESENCE_READBACK_JOIN_COMPLETE = True
OUTPUT_TERMINAL_CONTEXT_JOIN_COMPLETE = False
PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_COMMIT_EVIDENCE_PRESENT = False
PRODUCTION_OUTPUT_READBACK_EVIDENCE_PRESENT = False
CONDITIONAL_ABSENT_ROLE_SKIP_DISPATCH_SEMANTICS_PRESENT = False
PRODUCTION_LIFECYCLE_SOURCE_AUTHORITY_PRESENT = False
PRODUCTION_LIVE_HOOKS_COMPLETE = False
CURRENT_ACCESS_ATOMIC_BRIDGE_PRESENT = False
JOINT_OUTPUT_READ_FIXED_POINT_PRESENT = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

_ROW_ISSUER = object()
_JOIN_ISSUER = object()


class ConstructionK7H1LifecycleOutputLeafJoinV1Error(ValueError):
    """An output leaf/readback projection was crossed, incomplete, or stale."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1LifecycleOutputLeafJoinV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecycleOutputLeafJoinV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _typed_skip(role: str, site_key: str, ordinal: int) -> dict[str, Any]:
    return {
        "kind": "SKIPPED_NOT_APPLICABLE",
        "reason": "ROLE_ABSENT_IN_REGISTERED_OUTPUT_LEAF",
        "role": role,
        "lifecycle_output_role_readback_site_key": site_key,
        "lifecycle_ordinal": ordinal,
    }


def _freeze_document(value: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(dict(value))


def _thaw_document(value: bytes) -> dict[str, Any]:
    document = loads_canonical_json(value)
    if type(document) is not dict:  # pragma: no cover - issuer invariant
        _fail("frozen output-leaf join row changed type")
    return document


def _readback_map(
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
) -> tuple[tuple[str, int, str], ...]:
    if type(bundle) is not dispatch_v1.H1AnchoredLifecycleDispatchBundleV1:
        _fail("output-leaf join requires one exact anchored lifecycle bundle")
    rows = tuple(
        row
        for row in bundle.program.transitions
        if row["operation"] == "OUTPUT_ROLE_READBACK"
    )
    if (
        len(rows) != EXPECTED_OUTPUT_ROLE_COUNT
        or tuple(row["ordinal"] for row in rows) != EXPECTED_READBACK_ORDINALS
        or any(
            row["resource_path"] != "io.read_bytes"
            or row["owner_role"] != "BROKER"
            or row["reservation_edge"] is not True
            for row in rows
        )
    ):
        _fail("anchored lifecycle lost the exact eight output readback sites")
    role_rows: list[tuple[str, int, str]] = []
    prefix = "readback:output-role:"
    for row in rows:
        site_key = row["site_key"]
        if type(site_key) is not str or not site_key.startswith(prefix):
            _fail("output readback site does not encode its registered role")
        role_rows.append((site_key[len(prefix) :], row["ordinal"], site_key))
    result = tuple(role_rows)
    if tuple(role for role, _, _ in result) != tuple(
        output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
    ):
        _fail("lifecycle output-readback role order crossed the output DAG")
    return result


@dataclass(frozen=True, slots=True)
class H1LifecycleOutputLeafJoinRowV1:
    """One exact registered output leaf projected onto eight lifecycle sites."""

    _issuer: InitVar[object]
    _document_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROW_ISSUER:
            _fail("output-leaf join row is verifier-issued only")
        document = _thaw_document(self._document_bytes)
        if canonical_json_bytes(document) != self._document_bytes:
            _fail("output-leaf join row bytes are not canonical")

    @property
    def document(self) -> dict[str, Any]:
        return _thaw_document(self._document_bytes)

    @property
    def branch_key(self) -> str:
        return self.document["branch_key"]

    @property
    def present_roles(self) -> tuple[str, ...]:
        return tuple(self.document["present_roles"])

    @property
    def absent_roles(self) -> tuple[str, ...]:
        return tuple(self.document["absent_roles"])

    @property
    def selected_readback_site_keys(self) -> tuple[str, ...]:
        return tuple(self.document["selected_readback_site_keys"])

    def to_document(self) -> dict[str, Any]:
        return self.document


def _join_row(
    leaf: output_v1.H1ProductionOutputBranchLeafV1,
    readback_rows: tuple[tuple[str, int, str], ...],
) -> H1LifecycleOutputLeafJoinRowV1:
    registered_roles = tuple(output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES)
    if (
        type(leaf) is not output_v1.H1ProductionOutputBranchLeafV1
        or tuple(role for role in registered_roles if role in leaf.present_roles)
        != leaf.present_roles
        or tuple(role for role in registered_roles if role not in leaf.present_roles)
        != leaf.absent_roles
    ):
        _fail("registered output leaf has a malformed role partition")
    by_role = {role: (ordinal, site_key) for role, ordinal, site_key in readback_rows}
    selected = tuple(by_role[role][1] for role in leaf.present_roles)
    skipped = tuple(
        _typed_skip(role, by_role[role][1], by_role[role][0])
        for role in leaf.absent_roles
    )
    if (
        len(selected) + len(skipped) != EXPECTED_OUTPUT_ROLE_COUNT
        or set(selected) & {row["lifecycle_output_role_readback_site_key"] for row in skipped}
        or {
            *selected,
            *(row["lifecycle_output_role_readback_site_key"] for row in skipped),
        }
        != {site_key for _, _, site_key in readback_rows}
    ):
        _fail("output leaf does not partition the eight lifecycle readback sites")
    reaches_finalize = (
        leaf.finalization_status
        is not output_v1.H1OutputFinalizationStatusV1.STOPPED_BEFORE_NEXT_ROLE
    )
    document = {
        "branch_key": leaf.branch_key,
        "context_kind": leaf.context_kind.value,
        "broker_prefix_count": leaf.broker_prefix_count,
        "finalization_status": leaf.finalization_status.value,
        "present_roles": list(leaf.present_roles),
        "absent_roles": list(leaf.absent_roles),
        "selected_readback_site_keys": list(selected),
        "selected_readback_site_count": len(selected),
        "skipped_readback_sites": list(skipped),
        "skipped_readback_site_count": len(skipped),
        "all_eight_lifecycle_readback_sites_partitioned_exactly_once": True,
        "ordinary_output_finalize_site_reached_by_leaf": reaches_finalize,
        "output_owner_close_obligation_present": True,
        "invalidates_official_run": leaf.invalidates_official_run,
        "certificate_coverage_satisfied": leaf.certificate_coverage_satisfied,
        "effective_terminal_class": leaf.effective_terminal_class,
        "effective_terminal_code": leaf.effective_terminal_code,
        "terminal_artifact_matches_effective_closure": (
            leaf.terminal_artifact_matches_effective_closure
        ),
        "registered_candidate_projection_only": True,
        "durable_role_commit_observed": False,
        "native_readback_observed": False,
        "production_output_leaf_authority_present": False,
    }
    return H1LifecycleOutputLeafJoinRowV1(
        _ROW_ISSUER,
        _freeze_document(document),
    )


@dataclass(frozen=True, slots=True)
class H1LifecycleOutputLeafJoinV1:
    """Content-addressed ninety-row candidate projection."""

    _issuer: InitVar[object]
    anchor_id: str
    provenance_id: str
    snapshot_id: str
    lifecycle_program_id: str
    lifecycle_branch_analysis_id: str
    anchored_program_id: str
    handler_registry_id: str
    lifecycle_source_manifest_id: str
    execution_topology_profile_id: str
    output_branch_dag_id: str
    output_serializer_universe_id: str
    rows: tuple[H1LifecycleOutputLeafJoinRowV1, ...]
    _join_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _JOIN_ISSUER:
            _fail("lifecycle output-leaf join is verifier-issued only")
        for name in (
            "anchor_id",
            "provenance_id",
            "snapshot_id",
            "lifecycle_program_id",
            "lifecycle_branch_analysis_id",
            "anchored_program_id",
            "handler_registry_id",
            "lifecycle_source_manifest_id",
            "execution_topology_profile_id",
            "output_branch_dag_id",
            "output_serializer_universe_id",
        ):
            _cid(getattr(self, name), name)
        documents = tuple(row.to_document() for row in self.rows)
        if (
            len(documents) != EXPECTED_LEAF_COUNT
            or len({row["branch_key"] for row in documents}) != EXPECTED_LEAF_COUNT
            or len({tuple(row["present_roles"]) for row in documents})
            != EXPECTED_ROLE_PRESENCE_SET_COUNT
            or any(
                type(row) is not H1LifecycleOutputLeafJoinRowV1 for row in self.rows
            )
        ):
            _fail("lifecycle output-leaf join is incomplete or reordered")
        object.__setattr__(
            self,
            "_join_id",
            content_id(OUTPUT_LEAF_JOIN_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        readback_sites = []
        first_row = self.rows[0].to_document()
        all_sites = {
            *first_row["selected_readback_site_keys"],
            *(
                row["lifecycle_output_role_readback_site_key"]
                for row in first_row["skipped_readback_sites"]
            ),
        }
        # The first leaf may have no present roles; restore the exact anchored
        # order from the role name encoded in each registered site key.
        for ordinal, role in zip(
            EXPECTED_READBACK_ORDINALS,
            output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES,
        ):
            site_key = f"readback:output-role:{role}"
            if site_key not in all_sites:
                _fail("first output leaf no longer covers all readback sites")
            readback_sites.append(
                {"role": role, "ordinal": ordinal, "site_key": site_key}
            )
        return {
            "schema": "acfqp.k7_h1_lifecycle_output_leaf_join.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_lifecycle_local_main_anchor_id": self.anchor_id,
            "h1_caller_pinned_lifecycle_provenance_id": self.provenance_id,
            "lifecycle_program_snapshot_id": self.snapshot_id,
            "lifecycle_program_id": self.lifecycle_program_id,
            "lifecycle_branch_analysis_id": self.lifecycle_branch_analysis_id,
            "h1_anchored_lifecycle_program_id": self.anchored_program_id,
            "h1_anchored_lifecycle_handler_registry_id": self.handler_registry_id,
            "h1_production_lifecycle_source_manifest_id": (
                self.lifecycle_source_manifest_id
            ),
            "h1_execution_topology_profile_id": self.execution_topology_profile_id,
            "h1_production_output_branch_dag_id": self.output_branch_dag_id,
            "h1_production_output_serializer_universe_id": (
                self.output_serializer_universe_id
            ),
            "registered_output_roles": list(
                output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
            ),
            "lifecycle_output_role_readback_sites": readback_sites,
            "lifecycle_output_role_readback_site_count": len(readback_sites),
            "context_count": EXPECTED_CONTEXT_COUNT,
            "terminal_leaf_count": len(self.rows),
            "role_presence_set_count": len(
                {row.present_roles for row in self.rows}
            ),
            "leaf_rows": [row.to_document() for row in self.rows],
            "registered_role_presence_readback_join_complete": True,
            "each_present_role_maps_to_one_readback_site": True,
            "each_absent_role_has_one_typed_skip": True,
            "every_registered_readback_site_is_partitioned_per_leaf": True,
            "output_terminal_context_join_complete": False,
            "production_output_leaf_authority_present": False,
            "production_output_commit_evidence_present": False,
            "production_output_readback_evidence_present": False,
            "conditional_absent_role_skip_dispatch_semantics_present": False,
            "production_lifecycle_source_authority_present": False,
            "production_live_hooks_complete": False,
            "current_access_atomic_bridge_present": False,
            "joint_output_read_fixed_point_present": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
        }

    @property
    def join_id(self) -> str:
        current = content_id(OUTPUT_LEAF_JOIN_DOMAIN, self._payload())
        if not hmac.compare_digest(current, self._join_id):
            _fail("lifecycle output-leaf join changed")
        return self._join_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    @property
    def by_branch_key(self) -> dict[str, H1LifecycleOutputLeafJoinRowV1]:
        return {row.branch_key: row for row in self.rows}

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_lifecycle_output_leaf_join_id": self.join_id,
        }


def build_h1_lifecycle_output_leaf_join_v1(
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
) -> H1LifecycleOutputLeafJoinV1:
    """Derive the exact candidate leaf/readback projection from pinned inputs."""

    if type(bundle) is not dispatch_v1.H1AnchoredLifecycleDispatchBundleV1:
        _fail("output-leaf join requires one exact anchored lifecycle bundle")
    output_dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
    serializer_universe = (
        output_v1.registered_h1_production_output_serializer_universe_candidate_v1()
    )
    program = bundle.program
    if (
        len(output_dag.contexts) != EXPECTED_CONTEXT_COUNT
        or len(output_dag.leaves) != EXPECTED_LEAF_COUNT
        or program.output_branch_dag_id != output_dag.dag_id
        or serializer_universe.to_document()["h1_production_output_branch_dag_id"]
        != output_dag.dag_id
    ):
        _fail("anchored lifecycle and registered output candidates are crossed")
    readback_rows = _readback_map(bundle)
    rows = tuple(_join_row(leaf, readback_rows) for leaf in output_dag.leaves)
    join = H1LifecycleOutputLeafJoinV1(
        _JOIN_ISSUER,
        program.anchor_id,
        program.provenance_id,
        program.snapshot_id,
        program.program_id,
        program.branch_analysis_id,
        program.anchored_program_id,
        program.handler_registry_id,
        program.source_manifest_id,
        program.execution_topology_profile_id,
        program.output_branch_dag_id,
        serializer_universe.universe_id,
        rows,
    )
    if (
        len(join.rows) != EXPECTED_LEAF_COUNT
        or len(join.by_branch_key) != EXPECTED_LEAF_COUNT
        or len({row.present_roles for row in join.rows})
        != EXPECTED_ROLE_PRESENCE_SET_COUNT
    ):
        _fail("constructed lifecycle output-leaf join failed exact cardinalities")
    return join


def verify_h1_lifecycle_output_leaf_join_bytes_v1(
    raw: bytes,
    *,
    bundle: dispatch_v1.H1AnchoredLifecycleDispatchBundleV1,
) -> H1LifecycleOutputLeafJoinV1:
    """Independently rederive the join and reject any re-signed mutation."""

    if type(raw) is not bytes:
        _fail("output-leaf join verifier requires exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecycleOutputLeafJoinV1Error(
            "output-leaf join bytes are not exact canonical JSON"
        ) from error
    if type(document) is not dict:
        _fail("output-leaf join document must be one object")
    expected = build_h1_lifecycle_output_leaf_join_v1(bundle)
    if not hmac.compare_digest(raw, expected.canonical_bytes):
        _fail("output-leaf join differs from the independently derived object")
    supplied_id = _cid(
        document.get("h1_lifecycle_output_leaf_join_id"),
        "output-leaf join ID",
    )
    payload = dict(document)
    payload.pop("h1_lifecycle_output_leaf_join_id", None)
    if (
        not hmac.compare_digest(supplied_id, expected.join_id)
        or not hmac.compare_digest(
            supplied_id, content_id(OUTPUT_LEAF_JOIN_DOMAIN, payload)
        )
    ):
        _fail("output-leaf join ID does not match its exact payload")
    return expected


__all__ = [
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "CONDITIONAL_ABSENT_ROLE_SKIP_DISPATCH_SEMANTICS_PRESENT",
    "CURRENT_ACCESS_ATOMIC_BRIDGE_PRESENT",
    "ConstructionK7H1LifecycleOutputLeafJoinV1Error",
    "EXPECTED_CONTEXT_COUNT",
    "EXPECTED_LEAF_COUNT",
    "EXPECTED_OUTPUT_ROLE_COUNT",
    "EXPECTED_READBACK_ORDINALS",
    "EXPECTED_ROLE_PRESENCE_SET_COUNT",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "H1LifecycleOutputLeafJoinRowV1",
    "H1LifecycleOutputLeafJoinV1",
    "JOINT_OUTPUT_READ_FIXED_POINT_PRESENT",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OUTPUT_LEAF_JOIN_DOMAIN",
    "OUTPUT_TERMINAL_CONTEXT_JOIN_COMPLETE",
    "PRODUCTION_LIVE_HOOKS_COMPLETE",
    "PRODUCTION_OUTPUT_LEAF_AUTHORITY_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_ROLE_PRESENCE_READBACK_JOIN_COMPLETE",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "build_h1_lifecycle_output_leaf_join_v1",
    "verify_h1_lifecycle_output_leaf_join_bytes_v1",
]
