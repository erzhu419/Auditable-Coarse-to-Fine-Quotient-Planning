"""Predecision H1 output serializer-template candidate.

Contract 2.0.58-B replaces the Contract-2.0.51 fixture payloads with a
serializer template.  The template contains the exact eight
durable roles and explicitly accounts for the broker trace, nine shared
receipts, 202 V6 CounterRecords, the WorkVector, 182 projection rows and the
eight-axis ComparisonVector, terminal, and output manifest.  It is an upper
serializer: its witness documents are not durable operational outputs.

The branch catalogue is a preregistered candidate constrained by the H1
topology and protocol profiles, not a production-lifecycle derivation and not
the historical 72-case fixture.  For each registered runtime/finalization leaf
the module solves the monotone
candidate-byte recurrence exactly, replays it twice, and then takes the exact
maximum over all leaves.  The result is predecision only and remains a
candidate until source-owned lifecycle, cardinality, hard-cap and formal
serializer/parser authorities are joined.  It is not the final tight
``io.output_bytes`` operand:
production output readback can couple ``io.read_bytes`` back to the output
extent and requires a later jointly verified ``(output, read)`` closure.  It
does not issue a DecisionPoint, route upper/decision, execution request,
CounterRecord, terminal, or official-run authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from functools import lru_cache
import hashlib
import hmac
import threading
from typing import Any, Mapping, NoReturn

from acfqp import accounting_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_h1_broker_ipc_v1 as ipc_v1
from acfqp import construction_k7_h1_business_adapter_v1 as adapter_v1
from acfqp import construction_k7_h1_current_access_authority_v1 as access_v1
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp import construction_k7_h1_execution_topology_profile_v1 as topology_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_BRANCH_DAG_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_BRANCH_FIXED_POINT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_FIXED_POINT_ITERATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_CONTEXT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_ROLE_UPPER_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_SERIALIZER_UNIVERSE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.58"
PROFILE_KEY = "construction_k7_h1_production_output_upper_v1"

PRODUCTION_SEMANTIC_SERIALIZER_UNIVERSE_PRESENT = False
SERIALIZER_TEMPLATE_UNIVERSE_CANDIDATE_PRESENT = True
PRODUCTION_OUTPUT_OPERAND_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_SERIALIZER_UPPER_AUTHORITY_PRESENT = False
PRODUCTION_OUTPUT_SERIALIZER_TEMPLATE_CANDIDATE_PRESENT = True
JOINT_OUTPUT_READ_FIXED_POINT_PRESENT = False
LEGACY_72_CASE_FIXTURE_IMPORTED = False
LEGACY_FIXTURE_NUMERIC_VALUE_USED = False
PREDECISION_ONLY = True
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
ROUTE_EXECUTION_AUTHORIZED = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

BRANCH_DAG_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_BRANCH_DAG_V1_DOMAIN
SERIALIZER_UNIVERSE_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_SERIALIZER_UNIVERSE_V1_DOMAIN
)
OPERAND_CONTEXT_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_CONTEXT_V1_DOMAIN
)
ROLE_UPPER_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_ROLE_UPPER_V1_DOMAIN
ITERATION_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_FIXED_POINT_ITERATION_V1_DOMAIN
)
BRANCH_FIXED_POINT_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_BRANCH_FIXED_POINT_V1_DOMAIN
)
OPERAND_CANDIDATE_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_CANDIDATE_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    BRANCH_DAG_DOMAIN,
    SERIALIZER_UNIVERSE_DOMAIN,
    OPERAND_CONTEXT_DOMAIN,
    ROLE_UPPER_DOMAIN,
    ITERATION_DOMAIN,
    BRANCH_FIXED_POINT_DOMAIN,
    OPERAND_CANDIDATE_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover - import-time registry invariant
    raise RuntimeError("H1 production output-upper domains are not registered")


REGISTERED_OPERATIONAL_OUTPUT_ROLES = (
    "BUSINESS_RESULT",
    "OPERATIONAL_TRACE",
    "TERMINAL_ARTIFACT",
    "COUNTER_RECORD_SET",
    "WORK_VECTOR",
    "COMPARISON_VECTOR",
    "ACTUAL_PROJECTION_PROOF",
    "OUTPUT_MANIFEST",
)
BUSINESS_RESULT_ROLE = REGISTERED_OPERATIONAL_OUTPUT_ROLES[0]
BROKER_OUTPUT_ROLE_ORDER = REGISTERED_OPERATIONAL_OUTPUT_ROLES[1:]
OUTPUT_MANIFEST_ROLE = REGISTERED_OPERATIONAL_OUTPUT_ROLES[-1]
_ROLE_SCHEMA_IDS = {
    "BUSINESS_RESULT": "acfqp.h1.production_business_result.width_witness.v1",
    "OPERATIONAL_TRACE": "acfqp.h1.production_operational_trace.width_witness.v1",
    "TERMINAL_ARTIFACT": "acfqp.terminal_artifact.width_witness.v1",
    "COUNTER_RECORD_SET": "acfqp.h1.production_counter_record_set.width_witness.v1",
    "WORK_VECTOR": "acfqp.work_vector.width_witness.v1",
    "COMPARISON_VECTOR": "acfqp.comparison_vector.width_witness.v1",
    "ACTUAL_PROJECTION_PROOF": (
        "acfqp.h1.production_actual_projection_proof.width_witness.v1"
    ),
    "OUTPUT_MANIFEST": "acfqp.h1.production_output_manifest.width_witness.v1",
}

SHARED_RECEIPT_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.read_bytes",
    "io.staged_bytes",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)

EXPECTED_COUNTER_RECORD_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_PROJECTION_TERM_COUNT = registry_v6.EXPECTED_V6_OPERATIONAL_LEAF_COUNT
EXPECTED_COMPARISON_AXIS_COUNT = len(accounting_v1.SHARED_AXES)

# These are serializer-width ceilings, not route caps and not claimed actuals.
# Every later route cap must be no larger.  Decimal JSON encoding is monotone
# for nonnegative integers, so one maximum-width witness bounds every smaller
# actual value without pretending the witness is an actual CounterRecord.
MAX_COUNTER_VALUE_FOR_SERIALIZATION = (1 << 63) - 1
MAX_COMPARISON_VALUE_FOR_SERIALIZATION = (
    EXPECTED_PROJECTION_TERM_COUNT * MAX_COUNTER_VALUE_FOR_SERIALIZATION
)
MAX_FRONTIER_POINTS_FOR_SERIALIZATION = 128
MAX_TERMINAL_ATTESTATIONS_FOR_SERIALIZATION = 32
MAX_BROKER_TRACE_EVENTS_FOR_SERIALIZATION = 64
MAX_ROLE_BYTES = 256 * 1024
MAX_TOTAL_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_FIXED_POINT_ITERATIONS = 32
TERMINAL_REPLAY_COUNT = 2


class ConstructionK7H1ProductionOutputUpperV1Error(ValueError):
    """A production branch, serializer envelope, or fixed point failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1ProductionOutputUpperV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ProductionOutputUpperV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{label} must be one exact integer >= {minimum}")
    return value


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _placeholder(label: str, ordinal: int = 0) -> str:
    return hashlib.sha256(f"{PROFILE_KEY}:{label}:{ordinal}".encode("utf-8")).hexdigest()


def _domain_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("output-upper object used an undeclared content domain")
    return content_id(domain, dict(payload))


@lru_cache(maxsize=1)
def _official_v6_profiles() -> tuple[Any, Any, Any, Any]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    registry.validate_official_catalogue()
    stage.validate(registry)
    comparison.validate(registry)
    projection.validate(registry, comparison)
    if (
        len(registry.required_paths) != EXPECTED_COUNTER_RECORD_COUNT
        or len(registry.operational_leaves) != EXPECTED_PROJECTION_TERM_COUNT
        or len(comparison.axes) != EXPECTED_COMPARISON_AXIS_COUNT
    ):
        _fail("V6 accounting serializer cardinalities changed")
    return registry, stage, comparison, projection


class H1BusinessResultVariantV1(str, Enum):
    ABSENT = "ABSENT"
    EXACT_INFEASIBLE = "EXACT_INFEASIBLE"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"


class H1ProductionOutputContextKindV1(str, Enum):
    EXACT_INFEASIBLE = "EXACT_INFEASIBLE"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"
    SHARED_CAP_EXHAUSTED_PRE_BUSINESS = "SHARED_CAP_EXHAUSTED_PRE_BUSINESS"
    SHARED_CAP_EXHAUSTED_POST_BUSINESS = "SHARED_CAP_EXHAUSTED_POST_BUSINESS"
    PROTOCOL_PRE_BUSINESS = "PROTOCOL_PRE_BUSINESS"
    PROTOCOL_POST_BUSINESS = "PROTOCOL_POST_BUSINESS"
    INTEGRITY_PRE_BUSINESS = "INTEGRITY_PRE_BUSINESS"
    INTEGRITY_POST_BUSINESS = "INTEGRITY_POST_BUSINESS"
    AMBIGUOUS_NATIVE_LAUNCH = "AMBIGUOUS_NATIVE_LAUNCH"
    BUSINESS_ADAPTER_FAILURE = "BUSINESS_ADAPTER_FAILURE"


class H1OutputFinalizationStatusV1(str, Enum):
    STOPPED_BEFORE_NEXT_ROLE = "STOPPED_BEFORE_NEXT_ROLE"
    FINALIZED = "FINALIZED"
    POST_MANIFEST_CLOSURE_FAILURE = "POST_MANIFEST_CLOSURE_FAILURE"


@dataclass(frozen=True, slots=True)
class H1ProductionOutputBranchContextV1:
    kind: H1ProductionOutputContextKindV1
    runtime_path: tuple[str, ...]
    business_variants: tuple[H1BusinessResultVariantV1, ...]
    terminal_class: str
    terminal_code: str
    primary_failure: bool

    def __post_init__(self) -> None:
        if type(self.kind) is not H1ProductionOutputContextKindV1:
            _fail("production branch context kind is not exact")
        if (
            type(self.runtime_path) is not tuple
            or not self.runtime_path
            or len(self.runtime_path) != len(set(self.runtime_path))
            or any(type(item) is not str or not item for item in self.runtime_path)
        ):
            _fail("production branch runtime path is malformed")
        if (
            type(self.business_variants) is not tuple
            or any(type(item) is not H1BusinessResultVariantV1 for item in self.business_variants)
            or H1BusinessResultVariantV1.ABSENT in self.business_variants
        ):
            _fail("production branch business variants are malformed")
        expected = _expected_context_rows()[self.kind]
        if self._row() != expected:
            _fail("production branch context differs from the registered DAG")

    def _row(self) -> tuple[Any, ...]:
        return (
            self.runtime_path,
            self.business_variants,
            self.terminal_class,
            self.terminal_code,
            self.primary_failure,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "context_kind": self.kind.value,
            "runtime_path": list(self.runtime_path),
            "business_result_variants": [item.value for item in self.business_variants],
            "business_result_committed": bool(self.business_variants),
            "terminal_class": self.terminal_class,
            "terminal_code": self.terminal_code,
            "primary_failure": self.primary_failure,
        }


def _expected_context_rows() -> dict[H1ProductionOutputContextKindV1, tuple[Any, ...]]:
    base = (
        "ROUTE_DECISION_FROZEN",
        "WORKER_LAUNCHED",
        "WORKER_READY_AND_BUSINESS_REQUEST_SIGNAL",
    )
    business = (*base, "BUSINESS_LAUNCHED", "BUSINESS_REQUEST_REPLAYED")
    result = (*business, "OWNED_SEARCH_FINISHED", "BUSINESS_RESULT_COMMITTED")
    post = (
        *result,
        "BUSINESS_EXITED_AND_REAPED_RESULT_PINNED",
        "BUSINESS_RESULT_RELAYED_AND_WORKER_ACKED",
        "WORKER_EOF_OBSERVED",
        "WORKER_REAPED",
        "SHARED_RECEIPT_INPUTS_FROZEN_BEFORE_OUTPUT",
    )
    return {
        H1ProductionOutputContextKindV1.EXACT_INFEASIBLE: (
            post,
            (H1BusinessResultVariantV1.EXACT_INFEASIBLE,),
            "INFEASIBILITY_CERTIFICATE",
            "FULL_GROUND_EXACT_INFEASIBLE",
            False,
        ),
        H1ProductionOutputContextKindV1.CAP_EXHAUSTED: (
            post,
            (H1BusinessResultVariantV1.CAP_EXHAUSTED,),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "FALLBACK_CAP_EXHAUSTED",
            False,
        ),
        H1ProductionOutputContextKindV1.SHARED_CAP_EXHAUSTED_PRE_BUSINESS: (
            (
                "ROUTE_DECISION_FROZEN",
                "SHARED_CAP_ADMISSION_REJECTED_BEFORE_CHILD_LAUNCH",
            ),
            (),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "FALLBACK_CAP_EXHAUSTED",
            False,
        ),
        H1ProductionOutputContextKindV1.SHARED_CAP_EXHAUSTED_POST_BUSINESS: (
            (
                # This context is a conservative post-result envelope.  A
                # shared-resource admission/verification can reject after the
                # broker/worker result reads, reap, cleanup, or receipt-input
                # freeze.  Until a source-owned lifecycle splits those sites,
                # retain the longest registered post-business prefix rather
                # than silently treating later work as unreachable.
                *post,
                "SHARED_CAP_ADMISSION_OR_VERIFICATION_REJECTED_POST_BUSINESS",
            ),
            (
                H1BusinessResultVariantV1.EXACT_INFEASIBLE,
                H1BusinessResultVariantV1.CAP_EXHAUSTED,
            ),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "FALLBACK_CAP_EXHAUSTED",
            False,
        ),
        H1ProductionOutputContextKindV1.PROTOCOL_PRE_BUSINESS: (
            base,
            (),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "PROTOCOL_FAILURE",
            True,
        ),
        H1ProductionOutputContextKindV1.PROTOCOL_POST_BUSINESS: (
            post,
            (
                H1BusinessResultVariantV1.EXACT_INFEASIBLE,
                H1BusinessResultVariantV1.CAP_EXHAUSTED,
            ),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "PROTOCOL_FAILURE",
            True,
        ),
        H1ProductionOutputContextKindV1.INTEGRITY_PRE_BUSINESS: (
            base,
            (),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "INTEGRITY_FAILURE",
            True,
        ),
        H1ProductionOutputContextKindV1.INTEGRITY_POST_BUSINESS: (
            post,
            (
                H1BusinessResultVariantV1.EXACT_INFEASIBLE,
                H1BusinessResultVariantV1.CAP_EXHAUSTED,
            ),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "INTEGRITY_FAILURE",
            True,
        ),
        H1ProductionOutputContextKindV1.AMBIGUOUS_NATIVE_LAUNCH: (
            ("ROUTE_DECISION_FROZEN", "WORKER_LAUNCH_EXISTENCE_AMBIGUOUS"),
            (),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "PROTOCOL_FAILURE",
            True,
        ),
        H1ProductionOutputContextKindV1.BUSINESS_ADAPTER_FAILURE: (
            (*business, "BUSINESS_ADAPTER_FAILED_BEFORE_RESULT_COMMIT"),
            (),
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "PROTOCOL_FAILURE",
            True,
        ),
    }


def _contexts() -> tuple[H1ProductionOutputBranchContextV1, ...]:
    rows = _expected_context_rows()
    return tuple(
        H1ProductionOutputBranchContextV1(kind, *rows[kind])
        for kind in H1ProductionOutputContextKindV1
    )


@dataclass(frozen=True, slots=True)
class H1ProductionOutputBranchLeafV1:
    branch_key: str
    context_kind: H1ProductionOutputContextKindV1
    broker_prefix_count: int
    finalization_status: H1OutputFinalizationStatusV1
    present_roles: tuple[str, ...]
    absent_roles: tuple[str, ...]
    invalidates_official_run: bool
    certificate_coverage_satisfied: bool
    effective_terminal_class: str
    effective_terminal_code: str
    terminal_artifact_matches_effective_closure: bool

    def __post_init__(self) -> None:
        if type(self.context_kind) is not H1ProductionOutputContextKindV1:
            _fail("output branch leaf context is malformed")
        _exact_int(self.broker_prefix_count, "broker prefix count")
        if self.broker_prefix_count > len(BROKER_OUTPUT_ROLE_ORDER):
            _fail("broker prefix exceeds the seven-role suffix")
        if type(self.finalization_status) is not H1OutputFinalizationStatusV1:
            _fail("output branch finalization status is malformed")
        if type(self.invalidates_official_run) is not bool:
            _fail("output branch validity flag is malformed")
        if (
            type(self.certificate_coverage_satisfied) is not bool
            or type(self.effective_terminal_class) is not str
            or not self.effective_terminal_class
            or type(self.effective_terminal_code) is not str
            or not self.effective_terminal_code
            or type(self.terminal_artifact_matches_effective_closure) is not bool
        ):
            _fail("output branch effective closure is malformed")
        expected = _make_leaf(
            self.context_kind,
            self.broker_prefix_count,
            self.finalization_status,
            validate=False,
        )
        if self != expected:
            _fail("output branch leaf differs from the registered DAG")

    def to_document(self) -> dict[str, Any]:
        return {
            "branch_key": self.branch_key,
            "context_kind": self.context_kind.value,
            "broker_prefix_count": self.broker_prefix_count,
            "finalization_status": self.finalization_status.value,
            "present_roles": list(self.present_roles),
            "absent_roles": list(self.absent_roles),
            "invalidates_official_run": self.invalidates_official_run,
            "certificate_coverage_satisfied": self.certificate_coverage_satisfied,
            "effective_terminal_class": self.effective_terminal_class,
            "effective_terminal_code": self.effective_terminal_code,
            "terminal_artifact_matches_effective_closure": (
                self.terminal_artifact_matches_effective_closure
            ),
        }


def _make_leaf(
    context_kind: H1ProductionOutputContextKindV1,
    prefix: int,
    status: H1OutputFinalizationStatusV1,
    *,
    validate: bool = True,
) -> H1ProductionOutputBranchLeafV1:
    _exact_int(prefix, "broker prefix")
    contexts = _expected_context_rows()
    if context_kind not in contexts or prefix > len(BROKER_OUTPUT_ROLE_ORDER):
        _fail("output leaf has an unknown context or prefix")
    if status is H1OutputFinalizationStatusV1.STOPPED_BEFORE_NEXT_ROLE:
        if prefix >= len(BROKER_OUTPUT_ROLE_ORDER):
            _fail("stopped-before-next-role leaf cannot have a complete suffix")
        suffix = f"P{prefix}_OUTPUT_COMMIT_FAILURE"
    elif status is H1OutputFinalizationStatusV1.FINALIZED:
        if prefix != len(BROKER_OUTPUT_ROLE_ORDER):
            _fail("finalized leaf requires all seven broker roles")
        suffix = "P7_FINALIZED"
    elif status is H1OutputFinalizationStatusV1.POST_MANIFEST_CLOSURE_FAILURE:
        if prefix != len(BROKER_OUTPUT_ROLE_ORDER):
            _fail("post-manifest closure failure requires a complete suffix")
        suffix = "P7_CLOSURE_FAILURE"
    else:  # pragma: no cover - enum exhaustiveness
        _fail("unknown finalization status")
    business = bool(contexts[context_kind][1])
    selected = (
        ((BUSINESS_RESULT_ROLE,) if business else ())
        + BROKER_OUTPUT_ROLE_ORDER[:prefix]
    )
    present = tuple(role for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES if role in selected)
    absent = tuple(role for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES if role not in present)
    context_terminal_class = contexts[context_kind][2]
    context_terminal_code = contexts[context_kind][3]
    context_primary_failure = contexts[context_kind][4]
    finalized = status is H1OutputFinalizationStatusV1.FINALIZED
    if finalized:
        effective_terminal_class = context_terminal_class
        effective_terminal_code = context_terminal_code
        invalid = context_primary_failure
        certificate_coverage_satisfied = context_terminal_class in {
            "PLAN_CERTIFICATE",
            "INFEASIBILITY_CERTIFICATE",
        }
        terminal_matches = True
    else:
        # A stopped/failed durable-output sequence cannot inherit a previously
        # planned success or infeasibility terminal.  It is a protocol-level
        # attempt closure.  Any earlier terminal-role bytes are provisional and
        # cannot be the authority for this effective closure.
        effective_terminal_class = "ATTEMPT_CLOSURE_NONCERTIFICATE"
        effective_terminal_code = "PROTOCOL_FAILURE"
        invalid = True
        certificate_coverage_satisfied = False
        terminal_matches = False
    value = object.__new__(H1ProductionOutputBranchLeafV1)
    object.__setattr__(value, "branch_key", f"{context_kind.value}_{suffix}")
    object.__setattr__(value, "context_kind", context_kind)
    object.__setattr__(value, "broker_prefix_count", prefix)
    object.__setattr__(value, "finalization_status", status)
    object.__setattr__(value, "present_roles", present)
    object.__setattr__(value, "absent_roles", absent)
    object.__setattr__(value, "invalidates_official_run", invalid)
    object.__setattr__(
        value, "certificate_coverage_satisfied", certificate_coverage_satisfied
    )
    object.__setattr__(value, "effective_terminal_class", effective_terminal_class)
    object.__setattr__(value, "effective_terminal_code", effective_terminal_code)
    object.__setattr__(
        value, "terminal_artifact_matches_effective_closure", terminal_matches
    )
    if validate:
        H1ProductionOutputBranchLeafV1.__post_init__(value)
    return value


def _leaves() -> tuple[H1ProductionOutputBranchLeafV1, ...]:
    rows: list[H1ProductionOutputBranchLeafV1] = []
    for context in H1ProductionOutputContextKindV1:
        rows.extend(
            _make_leaf(
                context,
                prefix,
                H1OutputFinalizationStatusV1.STOPPED_BEFORE_NEXT_ROLE,
            )
            for prefix in range(len(BROKER_OUTPUT_ROLE_ORDER))
        )
        rows.append(
            _make_leaf(
                context,
                len(BROKER_OUTPUT_ROLE_ORDER),
                H1OutputFinalizationStatusV1.FINALIZED,
            )
        )
        rows.append(
            _make_leaf(
                context,
                len(BROKER_OUTPUT_ROLE_ORDER),
                H1OutputFinalizationStatusV1.POST_MANIFEST_CLOSURE_FAILURE,
            )
        )
    return tuple(rows)


_DAG_ISSUER = object()
_UNIVERSE_ISSUER = object()
_CONTEXT_ISSUER = object()
_ROLE_UPPER_ISSUER = object()
_ITERATION_ISSUER = object()
_FIXED_POINT_ISSUER = object()
_CANDIDATE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1ProductionOutputBranchDAGV1:
    _issuer: InitVar[object]
    contexts: tuple[H1ProductionOutputBranchContextV1, ...]
    leaves: tuple[H1ProductionOutputBranchLeafV1, ...]
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER or self.contexts != _contexts() or self.leaves != _leaves():
            _fail("production output branch DAG is issuer-owned and exact")
        expected_leaf_count = len(self.contexts) * (
            len(BROKER_OUTPUT_ROLE_ORDER) + 2
        )
        if (
            len(self.leaves) != expected_leaf_count
            or len({leaf.branch_key for leaf in self.leaves}) != len(self.leaves)
            or any(
                tuple(role for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES if role in leaf.present_roles)
                != leaf.present_roles
                for leaf in self.leaves
            )
        ):
            _fail("production output branch DAG is incomplete or reordered")
        object.__setattr__(self, "_dag_id", _domain_id(BRANCH_DAG_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        topology = topology_v1.official_h1_execution_topology_profile_v1()
        ipc = ipc_v1.official_h1_broker_ipc_profile_v1()
        adapter = adapter_v1.official_h1_business_adapter_profile_v1()
        return {
            "schema": "acfqp.h1_production_output_branch_dag_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_execution_topology_profile_id": topology.profile_id,
            "h1_broker_ipc_profile_id": ipc.profile_id,
            "h1_business_adapter_profile_id": adapter.profile_id,
            "source_topology_contract": "2.0.55",
            "production_lifecycle_supersedes_construction_only_receipt_order": False,
            "shared_receipts_frozen_before_broker_output_commit": True,
            "production_lifecycle_source_authority_present": False,
            "branch_completeness_proven": False,
            "registered_output_roles": list(REGISTERED_OPERATIONAL_OUTPUT_ROLES),
            "broker_output_role_order": list(BROKER_OUTPUT_ROLE_ORDER),
            "contexts": [row.to_document() for row in self.contexts],
            "terminal_leaves": [row.to_document() for row in self.leaves],
            "context_count": len(self.contexts),
            "terminal_leaf_count": len(self.leaves),
            "terminal_leaf_count_derived_from_dag": True,
            "shared_cap_rejection_before_first_business_result_present": True,
            "shared_cap_rejection_after_business_result_commit_present": True,
            "legacy_72_case_fixture_imported": False,
            "legacy_fixture_numeric_value_used": False,
            "branch_completeness_source": "PREREGISTERED_SERIALIZER_TEMPLATE_CANDIDATE_TABLE",
            "registered_template_candidate": True,
            "production_semantic_authority": False,
        }

    @property
    def dag_id(self) -> str:
        if _domain_id(BRANCH_DAG_DOMAIN, self._payload()) != self._dag_id:
            _fail("production output branch DAG changed")
        return self._dag_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_production_output_branch_dag_id": self.dag_id}

    @property
    def by_key(self) -> dict[str, H1ProductionOutputBranchLeafV1]:
        return {leaf.branch_key: leaf for leaf in self.leaves}

    @property
    def context_by_kind(self) -> dict[H1ProductionOutputContextKindV1, H1ProductionOutputBranchContextV1]:
        return {row.kind: row for row in self.contexts}


_OFFICIAL_DAG = H1ProductionOutputBranchDAGV1(_DAG_ISSUER, _contexts(), _leaves())
_OFFICIAL_LEAF_BY_KEY = {leaf.branch_key: leaf for leaf in _OFFICIAL_DAG.leaves}
_OFFICIAL_CONTEXT_BY_KIND = {row.kind: row for row in _OFFICIAL_DAG.contexts}


def registered_h1_production_output_branch_dag_candidate_v1(
) -> H1ProductionOutputBranchDAGV1:
    _ = _OFFICIAL_DAG.dag_id
    return _OFFICIAL_DAG


def official_h1_production_output_branch_dag_v1() -> NoReturn:
    _fail(
        "official production output branch DAG authority is unavailable; "
        "use the registered candidate accessor"
    )


@dataclass(frozen=True, slots=True)
class H1ProductionOutputSerializerUniverseV1:
    _issuer: InitVar[object]
    _universe_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _UNIVERSE_ISSUER:
            _fail("production output serializer universe is issuer-owned")
        registry, stage, comparison, projection = _official_v6_profiles()
        direct = stage.by_stage[registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK]
        if (
            len(registry.required_paths) != 202
            or len(registry.operational_leaves) != 182
            or len(direct.allowed_nonzero_paths) != 24
            or tuple(term.source_leaf for term in projection.terms)
            != tuple(row.path for row in registry.operational_leaves)
            or tuple(axis.name for axis in comparison.axes) != accounting_v1.SHARED_AXES
        ):
            _fail("production serializer universe crossed the exact V6 profiles")
        object.__setattr__(
            self, "_universe_id", _domain_id(SERIALIZER_UNIVERSE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        registry, stage, comparison, projection = _official_v6_profiles()
        return {
            "schema": "acfqp.h1_production_output_serializer_universe_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_production_output_branch_dag_id": _OFFICIAL_DAG.dag_id,
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": stage.stage_profile_id,
            "comparison_profile_id": comparison.comparison_profile_id,
            "actual_projection_profile_id": projection.actual_projection_profile_id,
            "route_kind": "DIRECT_FALLBACK",
            "registered_output_roles": list(REGISTERED_OPERATIONAL_OUTPUT_ROLES),
            "durable_output_role_count": len(REGISTERED_OPERATIONAL_OUTPUT_ROLES),
            "ninth_durable_wrapper_allowed": False,
            "role_schema_ids": dict(_ROLE_SCHEMA_IDS),
            "operational_trace_contains_broker_trace": True,
            "shared_receipt_paths": list(SHARED_RECEIPT_PATHS),
            "shared_receipt_count": len(SHARED_RECEIPT_PATHS),
            "required_counter_record_count": EXPECTED_COUNTER_RECORD_COUNT,
            "projection_term_count": EXPECTED_PROJECTION_TERM_COUNT,
            "comparison_axis_count": EXPECTED_COMPARISON_AXIS_COUNT,
            "comparison_axes": list(accounting_v1.SHARED_AXES),
            "counter_value_serialization_ceiling": MAX_COUNTER_VALUE_FOR_SERIALIZATION,
            "comparison_value_serialization_ceiling": MAX_COMPARISON_VALUE_FOR_SERIALIZATION,
            "frontier_point_serialization_ceiling": MAX_FRONTIER_POINTS_FOR_SERIALIZATION,
            "terminal_attestation_serialization_ceiling": MAX_TERMINAL_ATTESTATIONS_FOR_SERIALIZATION,
            "broker_trace_event_serialization_ceiling": MAX_BROKER_TRACE_EVENTS_FOR_SERIALIZATION,
            "role_byte_cap": MAX_ROLE_BYTES,
            "total_output_byte_cap": MAX_TOTAL_OUTPUT_BYTES,
            "fixed_point_iteration_cap": MAX_FIXED_POINT_ITERATIONS,
            "terminal_replay_count": TERMINAL_REPLAY_COUNT,
            "numeric_witnesses_are_actual_counter_records": False,
            "numeric_witnesses_are_monotone_serializer_upper_envelopes": True,
            "actual_values_must_not_exceed_width_ceilings": True,
            "width_ceiling_source_authority_present": False,
            "production_v6_object_schema_authority_present": False,
            "formal_parser_replay_present": False,
            "placeholder_ids_are_symbolic_width_witnesses": True,
            "serializer_template_candidate": True,
            "production_serializer_upper_authority": False,
            "registered_template_candidate": True,
            "production_semantic_authority": False,
            "legacy_fixture_serializer_used": False,
        }

    @property
    def universe_id(self) -> str:
        if _domain_id(SERIALIZER_UNIVERSE_DOMAIN, self._payload()) != self._universe_id:
            _fail("production output serializer universe changed")
        return self._universe_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_production_output_serializer_universe_id": self.universe_id,
        }


_OFFICIAL_UNIVERSE = H1ProductionOutputSerializerUniverseV1(_UNIVERSE_ISSUER)


def registered_h1_production_output_serializer_universe_candidate_v1(
) -> H1ProductionOutputSerializerUniverseV1:
    _ = _OFFICIAL_UNIVERSE.universe_id
    return _OFFICIAL_UNIVERSE


def official_h1_production_output_serializer_universe_v1() -> NoReturn:
    _fail(
        "official production serializer-universe authority is unavailable; "
        "use the registered candidate accessor"
    )


_LIVE_CONTEXTS: dict[int, tuple[Any, bytes, Any, Any]] = {}
_LIVE_CANDIDATES: dict[int, tuple[Any, bytes]] = {}
_RETENTION_LOCK = threading.RLock()


@dataclass(frozen=True, slots=True)
class H1ProductionOutputOperandContextV1:
    _issuer: InitVar[object]
    current_access_authority_id: str
    current_access_context_id: str
    recipe_id: str
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    kernel_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    session_nonce: str
    branch_dag_id: str
    serializer_universe_id: str
    _context_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CONTEXT_ISSUER:
            _fail("production output operand context is caller-minted")
        for name, value in self._payload().items():
            if type(value) is str and (name.endswith("_id") or name == "session_nonce"):
                _cid(value, name)
        object.__setattr__(self, "_context_id", _domain_id(OPERAND_CONTEXT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        registry, stage, comparison, projection = _official_v6_profiles()
        return {
            "schema": "acfqp.h1_production_output_operand_context.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_production_current_access_authority_id": self.current_access_authority_id,
            "h1_current_access_predecision_context_id": self.current_access_context_id,
            "h1_direct_fallback_two_role_recipe_id": self.recipe_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "BuildEpoch_id": self.build_epoch_id,
            "kernel_id": self.kernel_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "session_nonce": self.session_nonce,
            "h1_production_output_branch_dag_id": self.branch_dag_id,
            "h1_production_output_serializer_universe_id": self.serializer_universe_id,
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": stage.stage_profile_id,
            "comparison_profile_id": comparison.comparison_profile_id,
            "actual_projection_profile_id": projection.actual_projection_profile_id,
            "route_execution_started": False,
            "predecision_production_output_serializer_context": True,
        }

    @property
    def context_id(self) -> str:
        _require_live_context(self)
        return self._context_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_production_output_operand_context_id": self._context_id}


def _require_live_context(value: Any) -> tuple[Any, bytes, Any, Any]:
    if type(value) is not H1ProductionOutputOperandContextV1:
        _fail("production output operand context has a foreign type")
    with _RETENTION_LOCK:
        retained = _LIVE_CONTEXTS.get(id(value))
        if retained is None or retained[0] is not value:
            _fail("production output operand context is not issuer retained")
        authority = access_v1.require_h1_production_current_access_authority_v1(retained[2])
        recipe = retained[3]
        if type(recipe) is not recipe_v1.H1DirectFallbackTwoRoleRecipeV1 or recipe.recipe_id != value.recipe_id:
            _fail("production output operand context lost its exact recipe")
        if authority.authority_id != value.current_access_authority_id:
            _fail("production output operand context lost current-access authority")
        raw = canonical_json_bytes(value.to_document())
        if not hmac.compare_digest(raw, retained[1]):
            _fail("production output operand context changed")
        return retained


def freeze_h1_production_output_operand_context_v1(
    *,
    current_access_authority: access_v1.H1ProductionCurrentAccessAuthorityV1,
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1,
) -> H1ProductionOutputOperandContextV1:
    authority = access_v1.require_h1_production_current_access_authority_v1(
        current_access_authority
    )
    if type(recipe) is not recipe_v1.H1DirectFallbackTwoRoleRecipeV1:
        _fail("production output context requires the exact H1 recipe type")
    source = recipe.source
    _ = recipe.recipe_id
    if (
        source.structural_id != authority.structural_id
        or source.query_id != authority.query_id
        or source.threshold_profile_id != authority.threshold_profile_id
        or source.build_epoch_id != authority.build_epoch_id
        or source.kernel_id != authority.kernel_id
        or source.logical_occurrence_id != authority.logical_occurrence_id
        or source.route_attempt_id != authority.route_attempt_id
    ):
        _fail("production output context crossed recipe/current-access identities")
    value = H1ProductionOutputOperandContextV1(
        _CONTEXT_ISSUER,
        authority.authority_id,
        authority.context_id,
        recipe.recipe_id,
        authority.structural_id,
        authority.query_id,
        source.selected_plan_id,
        authority.threshold_profile_id,
        authority.build_epoch_id,
        authority.kernel_id,
        authority.logical_occurrence_id,
        authority.route_attempt_id,
        authority.session_nonce,
        _OFFICIAL_DAG._dag_id,
        _OFFICIAL_UNIVERSE._universe_id,
    )
    raw = canonical_json_bytes(value.to_document())
    with _RETENTION_LOCK:
        _LIVE_CONTEXTS[id(value)] = (value, raw, authority, recipe)
    return value


def _identity_fields(context: H1ProductionOutputOperandContextV1) -> dict[str, Any]:
    return {
        "h1_production_output_operand_context_id": context._context_id,
        "h1_production_current_access_authority_id": context.current_access_authority_id,
        "structural_id": context.structural_id,
        "query_id": context.query_id,
        "selected_plan_id": context.selected_plan_id,
        "threshold_profile_id": context.threshold_profile_id,
        "BuildEpoch_id": context.build_epoch_id,
        "kernel_id": context.kernel_id,
        "logical_occurrence_id": context.logical_occurrence_id,
        "route_attempt_id": context.route_attempt_id,
    }


def _counter_values(candidate_output_bytes: int) -> dict[str, int]:
    registry, stage, _comparison, _projection = _official_v6_profiles()
    direct = stage.by_stage[registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK]
    allowed = set(direct.allowed_nonzero_paths)
    values = {
        path: (MAX_COUNTER_VALUE_FOR_SERIALIZATION if path in allowed else 0)
        for path in registry.required_paths
    }
    values["io.output_bytes"] = candidate_output_bytes
    return values


def _counter_record_documents(
    context: H1ProductionOutputOperandContextV1,
    candidate_output_bytes: int,
) -> tuple[dict[str, Any], ...]:
    registry, _stage, _comparison, _projection = _official_v6_profiles()
    values = _counter_values(candidate_output_bytes)
    recorder_id = _placeholder(f"recorder:{context._context_id}")
    by_path = registry.by_path
    rows = tuple(
        {
            "schema": "acfqp.counter_record.width_witness.v1",
            "counter_registry_id": registry.registry_id,
            "path": path,
            "value_upper_width_witness": values[path],
            "observed": False,
            "recorder_width_witness_id": recorder_id,
            "semantics_id": by_path[path].semantics_id,
            "owner": by_path[path].owner,
            "unit": by_path[path].unit,
            "lane": by_path[path].lane.value,
            "scope": by_path[path].scope,
            "reducer": by_path[path].reducer.value,
            # Every production record ID is one fixed-width SHA-256.  The
            # envelope does not pretend its maximum-width value is actual.
            "counter_record_width_witness_id": _placeholder(
                f"counter-record:{path}"
            ),
            "formal_counter_record": False,
            "formal_parser_replay_present": False,
        }
        for path in registry.required_paths
    )
    if len(rows) != EXPECTED_COUNTER_RECORD_COUNT:
        _fail("counter-record serializer omitted a required V6 path")
    return rows


def _business_result_document(
    context: H1ProductionOutputOperandContextV1,
    variant: H1BusinessResultVariantV1,
) -> dict[str, Any]:
    if variant not in {
        H1BusinessResultVariantV1.EXACT_INFEASIBLE,
        H1BusinessResultVariantV1.CAP_EXHAUSTED,
    }:
        _fail("business-result serializer received an absent variant")
    frontier = []
    if variant is H1BusinessResultVariantV1.EXACT_INFEASIBLE:
        point = {
            "expected_reward": {
                "numerator": MAX_COUNTER_VALUE_FOR_SERIALIZATION - 1,
                "denominator": MAX_COUNTER_VALUE_FOR_SERIALIZATION,
            },
            "failure_probability": {
                "numerator": MAX_COUNTER_VALUE_FOR_SERIALIZATION - 1,
                "denominator": MAX_COUNTER_VALUE_FOR_SERIALIZATION,
            },
            "policy_digest": _placeholder("policy-digest"),
        }
        frontier = [dict(point) for _ in range(MAX_FRONTIER_POINTS_FOR_SERIALIZATION)]
    owned_paths = (
        "fallback.states_expanded",
        "fallback.actions_evaluated",
        "fallback.ground_steps",
        "fallback.outcome_rows",
        "fallback.bellman_backups",
        "control.cap_checks",
        "control.cap_rejections",
    )
    return {
        "schema": "acfqp.h1.production_business_result.width_witness.v1",
        "schema_version": SCHEMA_VERSION,
        "role": BUSINESS_RESULT_ROLE,
        **_identity_fields(context),
        "decision_point_id": _placeholder("decision-point"),
        "formal_v7_route_upper_id": _placeholder("route-upper"),
        "formal_v7_route_decision_id": _placeholder("route-decision"),
        "h1_business_adapter_profile_id": adapter_v1.official_h1_business_adapter_profile_v1().profile_id,
        "h1_broker_ipc_profile_id": ipc_v1.official_h1_broker_ipc_profile_v1().profile_id,
        "owned_engine_route_segment_transcript_id": _placeholder("owned-transcript"),
        "owned_engine_finished_execution_binding_id": _placeholder("owned-finished"),
        "outcome": (
            "INFEASIBLE_CERTIFIED"
            if variant is H1BusinessResultVariantV1.EXACT_INFEASIBLE
            else "CAP_EXHAUSTED"
        ),
        "search_complete": variant is H1BusinessResultVariantV1.EXACT_INFEASIBLE,
        "frontier": frontier,
        "selected": {
            "kind": "NOT_APPLICABLE",
            "reason": (
                "INFEASIBLE_CERTIFIED"
                if variant is H1BusinessResultVariantV1.EXACT_INFEASIBLE
                else "CAP_EXHAUSTED"
            ),
        },
        "cap_outcome": (
            {"kind": "NOT_APPLICABLE", "reason": "SEARCH_COMPLETE"}
            if variant is H1BusinessResultVariantV1.EXACT_INFEASIBLE
            else {
                "kind": "EXHAUSTED_CAP",
                "name": "max_materialization_positive_outcomes",
            }
        ),
        "owned_event_count": MAX_COUNTER_VALUE_FOR_SERIALIZATION,
        "owned_values": {
            path: MAX_COUNTER_VALUE_FOR_SERIALIZATION for path in owned_paths
        },
        "production_business_result_width_witness_id": _placeholder(
            "business-result"
        ),
        "formal_business_result": False,
    }


def _trace_document(
    context: H1ProductionOutputOperandContextV1,
    branch_context: H1ProductionOutputBranchContextV1,
    leaf: H1ProductionOutputBranchLeafV1,
    candidate_output_bytes: int,
) -> dict[str, Any]:
    event_count = min(
        MAX_BROKER_TRACE_EVENTS_FOR_SERIALIZATION,
        len(branch_context.runtime_path)
        + len(SHARED_RECEIPT_PATHS)
        + leaf.broker_prefix_count
        + 4,
    )
    events = [
        {
            "sequence": index,
            "operation": "OUTPUT_ROLE_COMMIT_OR_TYPED_FAILURE_SETTLEMENT",
            "owner": "BROKER_PARENT",
            "event_id": _placeholder(f"trace:{leaf.branch_key}", index),
            "predecessor_event_id": (
                None
                if index == 1
                else _placeholder(f"trace:{leaf.branch_key}", index - 1)
            ),
        }
        for index in range(1, event_count + 1)
    ]
    receipts = [
        {
            "path": path,
            "value_upper": (
                candidate_output_bytes
                if path == "io.output_bytes"
                else MAX_COUNTER_VALUE_FOR_SERIALIZATION
            ),
            "receipt_id": _placeholder(f"receipt:{path}"),
            "extent_or_cardinality_authority_id": _placeholder(f"receipt-authority:{path}"),
            "actual_receipt_must_be_replayed": True,
        }
        for path in SHARED_RECEIPT_PATHS
    ]
    return {
        "schema": "acfqp.h1.production_operational_trace.width_witness.v1",
        "schema_version": SCHEMA_VERSION,
        "role": "OPERATIONAL_TRACE",
        **_identity_fields(context),
        "branch_key": leaf.branch_key,
        "primary_terminal_code": branch_context.terminal_code,
        "effective_terminal_class": leaf.effective_terminal_class,
        "effective_terminal_code": leaf.effective_terminal_code,
        "broker_trace": events,
        "broker_trace_event_count_upper": event_count,
        "shared_resource_receipts": receipts,
        "shared_resource_receipt_count": len(receipts),
        "candidate_output_bytes": candidate_output_bytes,
        "partial_prefix_preserved": (
            leaf.finalization_status is not H1OutputFinalizationStatusV1.FINALIZED
        ),
        "operational_trace_width_witness_id": _placeholder(
            f"operational-trace:{leaf.branch_key}"
        ),
        "formal_operational_trace": False,
    }


def _terminal_document(
    context: H1ProductionOutputOperandContextV1,
    branch_context: H1ProductionOutputBranchContextV1,
    leaf: H1ProductionOutputBranchLeafV1,
) -> dict[str, Any]:
    evidence = tuple(
        sorted(
            _placeholder("terminal-evidence", index)
            for index in range(MAX_TERMINAL_ATTESTATIONS_FOR_SERIALIZATION)
        )
    )
    return {
        "schema": "acfqp.terminal_artifact.width_witness.v1",
        "schema_version": "1.0.0",
        "terminal_scope": "ROUTE_ATTEMPT",
        "terminal_class": branch_context.terminal_class,
        "terminal_code": branch_context.terminal_code,
        "terminal_role_provisional_until_output_manifest_commit": True,
        "authoritative_for_effective_attempt_closure": (
            leaf.terminal_artifact_matches_effective_closure
        ),
        "effective_attempt_closure_class": leaf.effective_terminal_class,
        "effective_attempt_closure_code": leaf.effective_terminal_code,
        "RouteDecisionContext_id": _placeholder("route-decision-context"),
        "logical_occurrence_id": context.logical_occurrence_id,
        "route_attempt_id": context.route_attempt_id,
        "decision_point_id": _placeholder("decision-point"),
        "transaction_id": {"kind": "NOT_APPLICABLE", "reason": "DIRECT_FALLBACK"},
        "candidate_work_vector_width_witness_id": _placeholder("work-vector"),
        "evidence_attestation_ids": list(evidence),
        "candidate_comparison_vector_width_witness_id": _placeholder(
            "comparison-vector"
        ),
        "candidate_projection_width_witness_id": _placeholder(
            "actual-projection-proof"
        ),
        "marginal_work_aggregation_proof_id": {
            "kind": "NOT_APPLICABLE",
            "reason": "SINGLE_DIRECT_FALLBACK_SEGMENT",
        },
        "route_decision_freeze_attestation_id": _placeholder("route-freeze"),
        "access_event_log_id": _placeholder("access-log"),
        "terminal_width_witness_id": _placeholder(f"terminal:{leaf.branch_key}"),
        "terminal_classification_issued": False,
        "formal_terminal_artifact": False,
    }


def _counter_record_set_document(
    context: H1ProductionOutputOperandContextV1,
    records: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.h1.production_counter_record_set.width_witness.v1",
        "schema_version": SCHEMA_VERSION,
        **_identity_fields(context),
        "route_kind": "DIRECT_FALLBACK",
        "counter_record_count": len(records),
        "counter_record_width_witness_ids": [
            row["counter_record_width_witness_id"] for row in records
        ],
        "records": list(records),
        "all_required_paths_present_in_width_witness": True,
        "native_zero_missing_as_zero_allowed": False,
        "counter_record_set_width_witness_id": _placeholder("counter-record-set"),
        "formal_counter_record_set": False,
    }


def _work_vector_document(
    context: H1ProductionOutputOperandContextV1,
    records: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    registry, _stage, _comparison, _projection = _official_v6_profiles()
    return {
        "schema": "acfqp.work_vector.width_witness.v1",
        "counter_registry_id": registry.registry_id,
        "subject_id": context.route_attempt_id,
        "route_kind": "DIRECT_FALLBACK",
        "counter_record_width_witness_ids": [
            row["counter_record_width_witness_id"] for row in records
        ],
        "records": list(records),
        "work_vector_width_witness_id": _placeholder("work-vector"),
        "formal_work_vector": False,
    }


def _comparison_values(candidate_output_bytes: int) -> tuple[tuple[str, int], ...]:
    return tuple(
        (
            axis,
            candidate_output_bytes
            if axis == accounting_v1.OUTPUT_BYTES
            else MAX_COMPARISON_VALUE_FOR_SERIALIZATION,
        )
        for axis in accounting_v1.SHARED_AXES
    )


def _comparison_vector_document(
    context: H1ProductionOutputOperandContextV1,
    work_vector_document: Mapping[str, Any],
    candidate_output_bytes: int,
) -> dict[str, Any]:
    _registry, _stage, comparison, _projection = _official_v6_profiles()
    return {
        "schema": "acfqp.comparison_vector.width_witness.v1",
        "comparison_profile_id": comparison.comparison_profile_id,
        "work_vector_width_witness_id": work_vector_document[
            "work_vector_width_witness_id"
        ],
        "subject_id": context.route_attempt_id,
        "route_kind": "DIRECT_FALLBACK",
        "values": [
            {"axis": axis, "value": value}
            for axis, value in _comparison_values(candidate_output_bytes)
        ],
        "comparison_vector_width_witness_id": _placeholder("comparison-vector"),
        "formal_comparison_vector": False,
    }


def _projection_document(
    context: H1ProductionOutputOperandContextV1,
    records: tuple[dict[str, Any], ...],
    work_vector_document: Mapping[str, Any],
    comparison_document: Mapping[str, Any],
    candidate_output_bytes: int,
) -> dict[str, Any]:
    registry, stage, comparison, projection = _official_v6_profiles()
    record_by_path = {row["path"]: row for row in records}
    values = _counter_values(candidate_output_bytes)
    rows = []
    for term in projection.terms:
        value = values[term.source_leaf]
        rows.append(
            {
                "source_leaf": term.source_leaf,
                "counter_record_width_witness_id": record_by_path[
                    term.source_leaf
                ]["counter_record_width_witness_id"],
                "source_value_upper": value,
                "target_axis": term.target_axis,
                "coefficient": term.coefficient,
                "reducer": term.reducer.value,
                "contribution_upper": value * term.coefficient,
            }
        )
    if len(rows) != EXPECTED_PROJECTION_TERM_COUNT:
        _fail("actual-projection serializer omitted a V6 operational term")
    return {
        "schema": (
            "acfqp.h1.production_actual_projection_proof.width_witness.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        **_identity_fields(context),
        "counter_registry_id": registry.registry_id,
        "stage_profile_id": stage.stage_profile_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": projection.actual_projection_profile_id,
        "work_vector_width_witness_id": work_vector_document[
            "work_vector_width_witness_id"
        ],
        "comparison_vector_width_witness_id": comparison_document[
            "comparison_vector_width_witness_id"
        ],
        "projection_term_count": len(rows),
        "projection_terms": rows,
        "all_182_operational_leaves_covered_once_in_width_witness": True,
        "projection_width_witness_id": _placeholder("actual-projection-proof"),
        "formal_actual_projection_proof": False,
    }


@lru_cache(maxsize=512)
def _accounting_serializer_documents(
    context: H1ProductionOutputOperandContextV1,
    candidate_output_bytes: int,
) -> tuple[
    tuple[dict[str, Any], ...],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Build the large 202/182 serializer closure once per context/candidate."""

    records = _counter_record_documents(context, candidate_output_bytes)
    work = _work_vector_document(context, records)
    comparison = _comparison_vector_document(
        context, work, candidate_output_bytes
    )
    projection = _projection_document(
        context,
        records,
        work,
        comparison,
        candidate_output_bytes,
    )
    return records, work, comparison, projection


def _schema_id_for_role(role: str) -> str:
    if role not in _ROLE_SCHEMA_IDS:
        _fail("serializer received an unregistered ninth role")
    return _ROLE_SCHEMA_IDS[role]


@dataclass(frozen=True, slots=True)
class H1ProductionOutputRoleUpperV1:
    _issuer: InitVar[object]
    context_id: str
    branch_key: str
    role: str
    role_schema_id: str
    candidate_output_bytes: int
    witness_variant: str
    witness_sha256: str
    upper_bytes: int
    _raw_bytes: bytes = field(repr=False)
    _role_upper_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_UPPER_ISSUER:
            _fail("production output role upper is caller-minted")
        _cid(self.context_id, "output operand context")
        if self.role not in REGISTERED_OPERATIONAL_OUTPUT_ROLES:
            _fail("output role upper contains an unregistered ninth role")
        if self.role_schema_id != _schema_id_for_role(self.role):
            _fail("output role upper schema differs from the serializer universe")
        _exact_int(self.candidate_output_bytes, "role-upper candidate")
        _exact_int(self.upper_bytes, "role-upper extent", minimum=1)
        if (
            type(self._raw_bytes) is not bytes
            or len(self._raw_bytes) != self.upper_bytes
            or _digest(self._raw_bytes) != self.witness_sha256
            or self.upper_bytes > MAX_ROLE_BYTES
            or type(self.witness_variant) is not str
            or not self.witness_variant
        ):
            _fail("output role upper witness hash/extent/cap is invalid")
        object.__setattr__(self, "_role_upper_id", _domain_id(ROLE_UPPER_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_output_role_width_witness.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_production_output_operand_context_id": self.context_id,
            "branch_key": self.branch_key,
            "role": self.role,
            "role_schema_id": self.role_schema_id,
            "candidate_output_bytes": self.candidate_output_bytes,
            "witness_variant": self.witness_variant,
            "witness_sha256": self.witness_sha256,
            "upper_bytes": self.upper_bytes,
            "witness_is_durable_operational_output": False,
            "witness_is_monotone_serializer_upper": True,
            "candidate_width_witness": True,
            "production_upper_authority": False,
            "source_authoritative_upper": False,
        }

    @property
    def role_upper_id(self) -> str:
        if _domain_id(ROLE_UPPER_DOMAIN, self._payload()) != self._role_upper_id:
            _fail("production output role upper changed")
        return self._role_upper_id

    @property
    def raw_bytes(self) -> bytes:
        _ = self.role_upper_id
        return bytes(self._raw_bytes)

    def descriptor(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "role_schema_id": self.role_schema_id,
            "role_width_witness_id": self.role_upper_id,
            "witness_sha256": self.witness_sha256,
            "upper_bytes": self.upper_bytes,
        }


def _freeze_role_upper(
    *,
    context: H1ProductionOutputOperandContextV1,
    leaf: H1ProductionOutputBranchLeafV1,
    role: str,
    candidate: int,
    variants: tuple[tuple[str, bytes], ...],
) -> H1ProductionOutputRoleUpperV1:
    if type(variants) is not tuple or not variants:
        _fail("output role serializer produced no upper witness")
    for name, raw in variants:
        if type(name) is not str or not name or type(raw) is not bytes or not raw:
            _fail("output role serializer produced a malformed witness")
    selected_name, selected_raw = max(variants, key=lambda row: (len(row[1]), row[1]))
    return H1ProductionOutputRoleUpperV1(
        _ROLE_UPPER_ISSUER,
        context._context_id,
        leaf.branch_key,
        role,
        _schema_id_for_role(role),
        candidate,
        selected_name,
        _digest(selected_raw),
        len(selected_raw),
        selected_raw,
    )


def _render_nonmanifest_role_upper(
    *,
    context: H1ProductionOutputOperandContextV1,
    branch_context: H1ProductionOutputBranchContextV1,
    leaf: H1ProductionOutputBranchLeafV1,
    role: str,
    candidate: int,
    records: tuple[dict[str, Any], ...],
    work: Mapping[str, Any],
    comparison: Mapping[str, Any],
    projection_document: Mapping[str, Any],
) -> H1ProductionOutputRoleUpperV1:
    if role == BUSINESS_RESULT_ROLE:
        variants = tuple(
            (
                variant.value,
                canonical_json_bytes(_business_result_document(context, variant)),
            )
            for variant in branch_context.business_variants
        )
    elif role == "OPERATIONAL_TRACE":
        variants = (("BRANCH_TRACE_AND_NINE_RECEIPTS", canonical_json_bytes(
            _trace_document(context, branch_context, leaf, candidate)
        )),)
    elif role == "TERMINAL_ARTIFACT":
        variants = ((leaf.effective_terminal_code, canonical_json_bytes(
            _terminal_document(context, branch_context, leaf)
        )),)
    elif role == "COUNTER_RECORD_SET":
        variants = (("EXACT_202_REQUIRED_RECORD_ENVELOPE", canonical_json_bytes(
            _counter_record_set_document(context, records)
        )),)
    elif role == "WORK_VECTOR":
        variants = (("EXACT_202_RECORD_WORK_VECTOR_ENVELOPE", canonical_json_bytes(dict(work))),)
    elif role == "COMPARISON_VECTOR":
        variants = (("EXACT_EIGHT_AXIS_COMPARISON_ENVELOPE", canonical_json_bytes(dict(comparison))),)
    elif role == "ACTUAL_PROJECTION_PROOF":
        variants = ((
            "EXACT_182_TERM_PROJECTION_ENVELOPE",
            canonical_json_bytes(dict(projection_document)),
        ),)
    else:
        _fail("non-manifest serializer received a missing or ninth role")
    return _freeze_role_upper(
        context=context,
        leaf=leaf,
        role=role,
        candidate=candidate,
        variants=variants,
    )


def _manifest_document(
    context: H1ProductionOutputOperandContextV1,
    branch_context: H1ProductionOutputBranchContextV1,
    leaf: H1ProductionOutputBranchLeafV1,
    candidate: int,
    prior: tuple[H1ProductionOutputRoleUpperV1, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.h1.production_output_manifest.width_witness.v1",
        "schema_version": SCHEMA_VERSION,
        "role": OUTPUT_MANIFEST_ROLE,
        **_identity_fields(context),
        "branch_key": leaf.branch_key,
        "primary_terminal_code": branch_context.terminal_code,
        "candidate_output_bytes": candidate,
        "present_non_manifest_role_uppers": [item.descriptor() for item in prior],
        "absent_roles": [
            {
                "role": role,
                "kind": "NOT_COMMITTED",
                "reason": (
                    "BUSINESS_RESULT_NOT_COMMITTED"
                    if role == BUSINESS_RESULT_ROLE
                    else "OUTPUT_FINALIZATION_STOPPED_BEFORE_ROLE_COMMIT"
                ),
            }
            for role in leaf.absent_roles
        ],
        "registered_role_count": len(REGISTERED_OPERATIONAL_OUTPUT_ROLES),
        "present_role_count": len(leaf.present_roles),
        "hidden_or_wrapper_output_count": 0,
        "manifest_self_identity_fields_present": False,
        "unregistered_ninth_output_present": False,
    }


def _render_branch_candidate(
    context: H1ProductionOutputOperandContextV1,
    leaf: H1ProductionOutputBranchLeafV1,
    candidate: int,
) -> tuple[H1ProductionOutputRoleUpperV1, ...]:
    _exact_int(candidate, "output fixed-point candidate")
    if candidate > MAX_TOTAL_OUTPUT_BYTES:
        _fail("output fixed-point candidate exceeds total cap")
    official_leaf = _OFFICIAL_LEAF_BY_KEY.get(leaf.branch_key)
    if official_leaf != leaf:
        _fail("output fixed point received an unregistered branch leaf")
    branch_context = _OFFICIAL_CONTEXT_BY_KIND[leaf.context_kind]
    accounting_roles = {
        "COUNTER_RECORD_SET",
        "WORK_VECTOR",
        "COMPARISON_VECTOR",
        "ACTUAL_PROJECTION_PROOF",
    }
    if any(role in accounting_roles for role in leaf.present_roles):
        records, work, comparison, projection_document = (
            _accounting_serializer_documents(context, candidate)
        )
    else:
        records, work, comparison, projection_document = (), {}, {}, {}
    result: list[H1ProductionOutputRoleUpperV1] = []
    for role in leaf.present_roles:
        if role == OUTPUT_MANIFEST_ROLE:
            raw = canonical_json_bytes(
                _manifest_document(context, branch_context, leaf, candidate, tuple(result))
            )
            item = _freeze_role_upper(
                context=context,
                leaf=leaf,
                role=role,
                candidate=candidate,
                variants=(("NO_SELF_REFERENCE_NO_NINTH_WRAPPER", raw),),
            )
        else:
            item = _render_nonmanifest_role_upper(
                context=context,
                branch_context=branch_context,
                leaf=leaf,
                role=role,
                candidate=candidate,
                records=records,
                work=work,
                comparison=comparison,
                projection_document=projection_document,
            )
        result.append(item)
    if tuple(item.role for item in result) != leaf.present_roles:
        _fail("output renderer omitted, reordered, or added a ninth role")
    if sum(item.upper_bytes for item in result) > MAX_TOTAL_OUTPUT_BYTES:
        _fail("rendered production output upper exceeds the total cap")
    return tuple(result)


@dataclass(frozen=True, slots=True)
class H1ProductionOutputFixedPointIterationV1:
    _issuer: InitVar[object]
    context_id: str
    branch_key: str
    iteration_index: int
    candidate_output_bytes: int
    observed_output_bytes: int
    role_upper_ids: tuple[str, ...]
    converged: bool
    _iteration_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ITERATION_ISSUER:
            _fail("output fixed-point iteration is caller-minted")
        _cid(self.context_id, "output operand context")
        _exact_int(self.iteration_index, "fixed-point iteration", minimum=1)
        _exact_int(self.candidate_output_bytes, "fixed-point candidate")
        _exact_int(self.observed_output_bytes, "fixed-point observation")
        if (
            type(self.role_upper_ids) is not tuple
            or len(set(self.role_upper_ids)) != len(self.role_upper_ids)
            or any(_cid(item, "role upper") != item for item in self.role_upper_ids)
            or type(self.converged) is not bool
            or self.converged is not (self.candidate_output_bytes == self.observed_output_bytes)
        ):
            _fail("output fixed-point iteration fields are malformed")
        object.__setattr__(self, "_iteration_id", _domain_id(ITERATION_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_output_fixed_point_iteration_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "h1_production_output_operand_context_id": self.context_id,
            "branch_key": self.branch_key,
            "iteration_index": self.iteration_index,
            "candidate_output_bytes": self.candidate_output_bytes,
            "observed_output_bytes": self.observed_output_bytes,
            "role_width_witness_ids": list(self.role_upper_ids),
            "converged": self.converged,
            "production_upper_authority": False,
        }

    @property
    def iteration_id(self) -> str:
        if _domain_id(ITERATION_DOMAIN, self._payload()) != self._iteration_id:
            _fail("output fixed-point iteration changed")
        return self._iteration_id


@dataclass(frozen=True, slots=True)
class H1ProductionOutputBranchFixedPointV1:
    _issuer: InitVar[object]
    context: H1ProductionOutputOperandContextV1
    branch_key: str
    iterations: tuple[H1ProductionOutputFixedPointIterationV1, ...]
    final_role_uppers: tuple[H1ProductionOutputRoleUpperV1, ...]
    output_bytes_upper: int
    terminal_replay_role_upper_id_sets: tuple[tuple[str, ...], ...]
    _fixed_point_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _FIXED_POINT_ISSUER:
            _fail("production branch fixed point is caller-minted")
        _verify_branch_fixed_point_structure(self)
        object.__setattr__(
            self,
            "_fixed_point_id",
            _domain_id(BRANCH_FIXED_POINT_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        leaf = _OFFICIAL_LEAF_BY_KEY[self.branch_key]
        return {
            "schema": "acfqp.h1_production_output_branch_fixed_point_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "h1_production_output_operand_context_id": self.context._context_id,
            "h1_production_output_branch_dag_id": _OFFICIAL_DAG._dag_id,
            "h1_production_output_serializer_universe_id": _OFFICIAL_UNIVERSE._universe_id,
            "branch_key": self.branch_key,
            "present_roles": list(leaf.present_roles),
            "absent_roles": list(leaf.absent_roles),
            "iteration_candidate_ids": [item.iteration_id for item in self.iterations],
            "final_role_width_witness_ids": [
                item.role_upper_id for item in self.final_role_uppers
            ],
            "output_bytes_upper": self.output_bytes_upper,
            "terminal_replay_role_width_witness_id_sets": [
                list(row) for row in self.terminal_replay_role_upper_id_sets
            ],
            "exact_fixed_point": True,
            "branch_upper_is_actual_output": False,
            "branch_upper_is_predecision_serializer_bound": True,
            "production_upper_authority": False,
            "source_authoritative_upper": False,
            "hidden_or_wrapper_output_count": 0,
        }

    @property
    def fixed_point_id(self) -> str:
        if _domain_id(BRANCH_FIXED_POINT_DOMAIN, self._payload()) != self._fixed_point_id:
            _fail("production branch fixed point changed")
        return self._fixed_point_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_production_output_branch_fixed_point_candidate_id": (
                self.fixed_point_id
            ),
        }


def _freeze_iteration(
    context: H1ProductionOutputOperandContextV1,
    leaf: H1ProductionOutputBranchLeafV1,
    index: int,
    candidate: int,
    rendered: tuple[H1ProductionOutputRoleUpperV1, ...],
) -> H1ProductionOutputFixedPointIterationV1:
    observed = sum(item.upper_bytes for item in rendered)
    return H1ProductionOutputFixedPointIterationV1(
        _ITERATION_ISSUER,
        context._context_id,
        leaf.branch_key,
        index,
        candidate,
        observed,
        tuple(item.role_upper_id for item in rendered),
        candidate == observed,
    )


def _verify_branch_fixed_point_structure(
    value: H1ProductionOutputBranchFixedPointV1,
) -> None:
    leaf = _OFFICIAL_LEAF_BY_KEY.get(value.branch_key)
    if leaf is None:
        _fail("branch fixed point names an unregistered branch")
    if type(value.iterations) is not tuple or not value.iterations:
        _fail("branch fixed point has no iteration trace")
    if len(value.iterations) > MAX_FIXED_POINT_ITERATIONS:
        _fail("branch fixed point exceeds the iteration cap")
    if value.iterations[0].candidate_output_bytes != 0:
        _fail("branch fixed point must start at candidate zero")
    previous_observed: int | None = None
    for index, item in enumerate(value.iterations, 1):
        if (
            type(item) is not H1ProductionOutputFixedPointIterationV1
            or item.context_id != value.context._context_id
            or item.branch_key != value.branch_key
            or item.iteration_index != index
            or (previous_observed is not None and item.candidate_output_bytes != previous_observed)
        ):
            _fail("branch fixed-point iteration trace is missing or reordered")
        if previous_observed is not None and item.observed_output_bytes < previous_observed:
            _fail("branch fixed-point recurrence decreased")
        if index < len(value.iterations) and item.converged:
            _fail("branch fixed-point trace continued after convergence")
        previous_observed = item.observed_output_bytes
    if not value.iterations[-1].converged:
        _fail("branch fixed-point trace did not converge")
    if (
        type(value.final_role_uppers) is not tuple
        or tuple(item.role for item in value.final_role_uppers) != leaf.present_roles
        or tuple(item.role_upper_id for item in value.final_role_uppers)
        != value.iterations[-1].role_upper_ids
        or value.output_bytes_upper != sum(item.upper_bytes for item in value.final_role_uppers)
        or value.output_bytes_upper != value.iterations[-1].candidate_output_bytes
        or value.output_bytes_upper > MAX_TOTAL_OUTPUT_BYTES
    ):
        _fail("branch fixed-point final role set or exact total changed")
    expected_replay = tuple(item.role_upper_id for item in value.final_role_uppers)
    if (
        type(value.terminal_replay_role_upper_id_sets) is not tuple
        or len(value.terminal_replay_role_upper_id_sets) != TERMINAL_REPLAY_COUNT
        or any(row != expected_replay for row in value.terminal_replay_role_upper_id_sets)
    ):
        _fail("branch fixed-point terminal replay differs")


def _solve_verified_h1_production_output_branch_fixed_point_v1(
    *,
    context: H1ProductionOutputOperandContextV1,
    branch_key: str,
) -> H1ProductionOutputBranchFixedPointV1:
    if type(branch_key) is not str or branch_key not in _OFFICIAL_LEAF_BY_KEY:
        _fail("output fixed-point branch is missing or unregistered")
    leaf = _OFFICIAL_LEAF_BY_KEY[branch_key]
    candidate = 0
    iterations: list[H1ProductionOutputFixedPointIterationV1] = []
    final: tuple[H1ProductionOutputRoleUpperV1, ...] | None = None
    seen: set[int] = set()
    for index in range(1, MAX_FIXED_POINT_ITERATIONS + 1):
        if candidate in seen:
            _fail("production output fixed-point recurrence cycled")
        seen.add(candidate)
        first = _render_branch_candidate(context, leaf, candidate)
        second = _render_branch_candidate(context, leaf, candidate)
        if (
            tuple(item.role_upper_id for item in first)
            != tuple(item.role_upper_id for item in second)
            or tuple(item.raw_bytes for item in first)
            != tuple(item.raw_bytes for item in second)
        ):
            _fail("production output serializer upper is nondeterministic")
        iteration = _freeze_iteration(context, leaf, index, candidate, first)
        iterations.append(iteration)
        observed = iteration.observed_output_bytes
        if observed < candidate:
            _fail("production output fixed-point recurrence decreased")
        if observed == candidate:
            final = first
            break
        candidate = observed
    if final is None:
        _fail("production output fixed point did not converge within its cap")
    replays = tuple(
        _render_branch_candidate(context, leaf, candidate)
        for _ in range(TERMINAL_REPLAY_COUNT)
    )
    expected_ids = tuple(item.role_upper_id for item in final)
    if any(
        tuple(item.role_upper_id for item in replay) != expected_ids
        or tuple(item.raw_bytes for item in replay) != tuple(item.raw_bytes for item in final)
        for replay in replays
    ):
        _fail("production output terminal serializer replay changed")
    return H1ProductionOutputBranchFixedPointV1(
        _FIXED_POINT_ISSUER,
        context,
        branch_key,
        tuple(iterations),
        final,
        candidate,
        tuple(tuple(item.role_upper_id for item in replay) for replay in replays),
    )


def solve_h1_production_output_branch_fixed_point_v1(
    *,
    context: H1ProductionOutputOperandContextV1,
    branch_key: str,
) -> H1ProductionOutputBranchFixedPointV1:
    _require_live_context(context)
    return _solve_verified_h1_production_output_branch_fixed_point_v1(
        context=context,
        branch_key=branch_key,
    )


def replay_h1_production_output_branch_fixed_point_v1(
    value: H1ProductionOutputBranchFixedPointV1,
) -> H1ProductionOutputBranchFixedPointV1:
    if type(value) is not H1ProductionOutputBranchFixedPointV1:
        _fail("branch fixed-point replay received a foreign type")
    _verify_branch_fixed_point_structure(value)
    _require_live_context(value.context)
    replay = _solve_verified_h1_production_output_branch_fixed_point_v1(
        context=value.context,
        branch_key=value.branch_key,
    )
    if (
        replay.fixed_point_id != value.fixed_point_id
        or tuple(item.raw_bytes for item in replay.final_role_uppers)
        != tuple(item.raw_bytes for item in value.final_role_uppers)
    ):
        _fail("branch fixed-point replay differs")
    return replay


@dataclass(frozen=True, slots=True)
class H1ProductionOutputOperandCandidateV1:
    _issuer: InitVar[object]
    context: H1ProductionOutputOperandContextV1
    branch_fixed_points: tuple[H1ProductionOutputBranchFixedPointV1, ...]
    output_bytes_upper: int
    maximizing_branch_keys: tuple[str, ...]
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CANDIDATE_ISSUER:
            _fail("production output operand candidate is caller-minted")
        _verify_operand_candidate_structure(self)
        object.__setattr__(
            self,
            "_candidate_id",
            _domain_id(OPERAND_CANDIDATE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_production_output_operand_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_production_output_operand_context_id": self.context._context_id,
            "h1_production_current_access_authority_id": self.context.current_access_authority_id,
            "h1_production_output_branch_dag_id": _OFFICIAL_DAG._dag_id,
            "h1_production_output_serializer_universe_id": _OFFICIAL_UNIVERSE._universe_id,
            "branch_fixed_point_candidate_ids": [
                item.fixed_point_id for item in self.branch_fixed_points
            ],
            "registered_candidate_leaf_count": len(self.branch_fixed_points),
            "output_bytes_path": "io.output_bytes",
            "output_bytes_upper": self.output_bytes_upper,
            "maximizing_branch_keys": list(self.maximizing_branch_keys),
            "branch_reducer": "max",
            "every_branch_fixed_point_exact": True,
            "all_registered_output_commit_prefixes_included": True,
            "production_branch_completeness_claimed": False,
            "legacy_fixture_numeric_value_used": False,
            "ninth_durable_output_wrapper_allowed": False,
            "predecision_output_serializer_upper_authority": False,
            "predecision_output_serializer_template_candidate": True,
            "production_lifecycle_source_authority_present": False,
            "width_ceiling_source_authority_present": False,
            "formal_v6_serializer_parser_replay_present": False,
            "atomic_multi_authority_consumption_present": False,
            "typed_consumption_receipt_present": False,
            "final_tight_output_operand_authority": False,
            "joint_output_read_fixed_point_present": False,
            "downstream_verified_read_catalogue_required": True,
            "serializer_width_read_ceiling_is_not_tight_read_operand": True,
            "formal_v7_route_authority_present": False,
            "route_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def candidate_id(self) -> str:
        _require_live_operand_candidate(self, replay=False)
        return self._candidate_id

    @property
    def authority_id(self) -> str:
        _fail(
            "production output operand candidate has no authority_id; "
            "a future source-bound authority requires a distinct role and domain"
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_production_output_operand_candidate_id": self._candidate_id,
        }


def _verify_operand_candidate_structure(value: H1ProductionOutputOperandCandidateV1) -> None:
    _require_live_context(value.context)
    expected_keys = tuple(leaf.branch_key for leaf in _OFFICIAL_DAG.leaves)
    if (
        type(value.branch_fixed_points) is not tuple
        or tuple(item.branch_key for item in value.branch_fixed_points) != expected_keys
        or len({item.fixed_point_id for item in value.branch_fixed_points})
        != len(value.branch_fixed_points)
    ):
        _fail("production output candidate omits, reorders, or repeats a reachable branch")
    for item in value.branch_fixed_points:
        if (
            type(item) is not H1ProductionOutputBranchFixedPointV1
            or item.context is not value.context
        ):
            _fail("production output candidate crossed a branch/context")
        _verify_branch_fixed_point_structure(item)
    expected_max = max(item.output_bytes_upper for item in value.branch_fixed_points)
    expected_keys_at_max = tuple(
        item.branch_key
        for item in value.branch_fixed_points
        if item.output_bytes_upper == expected_max
    )
    if (
        type(value.output_bytes_upper) is not int
        or value.output_bytes_upper != expected_max
        or value.maximizing_branch_keys != expected_keys_at_max
        or not value.maximizing_branch_keys
    ):
        _fail("production output candidate max reducer or maximizing branches changed")


def issue_h1_production_output_operand_candidate_v1(
    *,
    context: H1ProductionOutputOperandContextV1,
) -> H1ProductionOutputOperandCandidateV1:
    _require_live_context(context)
    points = tuple(
        _solve_verified_h1_production_output_branch_fixed_point_v1(
            context=context,
            branch_key=leaf.branch_key,
        )
        for leaf in _OFFICIAL_DAG.leaves
    )
    maximum = max(item.output_bytes_upper for item in points)
    maximizing = tuple(item.branch_key for item in points if item.output_bytes_upper == maximum)
    value = H1ProductionOutputOperandCandidateV1(
        _CANDIDATE_ISSUER,
        context,
        points,
        maximum,
        maximizing,
    )
    raw = canonical_json_bytes(value.to_document())
    with _RETENTION_LOCK:
        _LIVE_CANDIDATES[id(value)] = (value, raw)
    return value


def _require_live_operand_candidate(
    value: Any,
    *,
    replay: bool,
) -> tuple[Any, bytes]:
    if type(value) is not H1ProductionOutputOperandCandidateV1:
        _fail("production output operand candidate has a foreign type")
    with _RETENTION_LOCK:
        retained = _LIVE_CANDIDATES.get(id(value))
        if retained is None or retained[0] is not value:
            _fail("production output operand candidate is not issuer retained")
        _verify_operand_candidate_structure(value)
        if replay:
            for item in value.branch_fixed_points:
                replay_h1_production_output_branch_fixed_point_v1(item)
        current = canonical_json_bytes(value.to_document())
        if not hmac.compare_digest(current, retained[1]):
            _fail("production output operand candidate changed")
        return retained


def require_h1_production_output_operand_candidate_v1(
    value: Any,
    *,
    replay_all_branches: bool = True,
) -> H1ProductionOutputOperandCandidateV1:
    if type(replay_all_branches) is not bool:
        _fail("output candidate replay flag must be exact bool")
    _require_live_operand_candidate(
        value,
        replay=replay_all_branches,
    )
    return value


def consume_h1_production_output_operand_candidate_v1(value: Any) -> bytes:
    _require_live_operand_candidate(value, replay=True)
    raise ConstructionK7H1ProductionOutputUpperV1Error(
        "serializer-template candidate cannot be consumed before one atomic "
        "current-access/output/operand join with a typed receipt"
    )


class H1ProductionOutputOperandAuthorityV1:
    """Unavailable compatibility role; this contract issues no authority."""

    def __new__(cls, *args: Any, **kwargs: Any) -> NoReturn:
        del args, kwargs
        _fail(
            "production output operand authority is unavailable; "
            "use the explicitly nonauthorizing candidate API"
        )

    @property
    def authority_id(self) -> NoReturn:
        _fail("production output operand authority_id is unavailable")


def issue_h1_production_output_operand_authority_v1(
    *, context: H1ProductionOutputOperandContextV1
) -> NoReturn:
    del context
    _fail(
        "production output operand authority issuance is unavailable in this contract"
    )


def require_h1_production_output_operand_authority_v1(
    value: Any, *, replay_all_branches: bool = True
) -> NoReturn:
    del value, replay_all_branches
    _fail(
        "production output operand authority verification is unavailable in this contract"
    )


def consume_h1_production_output_operand_authority_v1(value: Any) -> NoReturn:
    del value
    _fail(
        "production output operand authority consumption is unavailable in this contract"
    )


__all__ = (
    "BRANCH_DAG_DOMAIN",
    "BRANCH_FIXED_POINT_DOMAIN",
    "BROKER_OUTPUT_ROLE_ORDER",
    "BUSINESS_RESULT_ROLE",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7H1ProductionOutputUpperV1Error",
    "EXPECTED_COMPARISON_AXIS_COUNT",
    "EXPECTED_COUNTER_RECORD_COUNT",
    "EXPECTED_PROJECTION_TERM_COUNT",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "H1BusinessResultVariantV1",
    "H1OutputFinalizationStatusV1",
    "H1ProductionOutputBranchContextV1",
    "H1ProductionOutputBranchDAGV1",
    "H1ProductionOutputBranchFixedPointV1",
    "H1ProductionOutputBranchLeafV1",
    "H1ProductionOutputContextKindV1",
    "H1ProductionOutputFixedPointIterationV1",
    "H1ProductionOutputOperandAuthorityV1",
    "H1ProductionOutputOperandCandidateV1",
    "H1ProductionOutputOperandContextV1",
    "H1ProductionOutputRoleUpperV1",
    "H1ProductionOutputSerializerUniverseV1",
    "ITERATION_DOMAIN",
    "JOINT_OUTPUT_READ_FIXED_POINT_PRESENT",
    "LEGACY_72_CASE_FIXTURE_IMPORTED",
    "LEGACY_FIXTURE_NUMERIC_VALUE_USED",
    "MAX_FIXED_POINT_ITERATIONS",
    "MAX_ROLE_BYTES",
    "MAX_TOTAL_OUTPUT_BYTES",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OPERAND_CANDIDATE_DOMAIN",
    "OPERAND_CONTEXT_DOMAIN",
    "OUTPUT_MANIFEST_ROLE",
    "PREDECISION_ONLY",
    "PRODUCTION_OUTPUT_OPERAND_AUTHORITY_PRESENT",
    "PRODUCTION_OUTPUT_SERIALIZER_UPPER_AUTHORITY_PRESENT",
    "PRODUCTION_OUTPUT_SERIALIZER_TEMPLATE_CANDIDATE_PRESENT",
    "PRODUCTION_SEMANTIC_SERIALIZER_UNIVERSE_PRESENT",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_OPERATIONAL_OUTPUT_ROLES",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "ROLE_UPPER_DOMAIN",
    "ROUTE_EXECUTION_AUTHORIZED",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SERIALIZER_TEMPLATE_UNIVERSE_CANDIDATE_PRESENT",
    "SERIALIZER_UNIVERSE_DOMAIN",
    "SHARED_RECEIPT_PATHS",
    "TERMINAL_REPLAY_COUNT",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "consume_h1_production_output_operand_authority_v1",
    "consume_h1_production_output_operand_candidate_v1",
    "freeze_h1_production_output_operand_context_v1",
    "issue_h1_production_output_operand_authority_v1",
    "issue_h1_production_output_operand_candidate_v1",
    "official_h1_production_output_branch_dag_v1",
    "official_h1_production_output_serializer_universe_v1",
    "registered_h1_production_output_branch_dag_candidate_v1",
    "registered_h1_production_output_serializer_universe_candidate_v1",
    "replay_h1_production_output_branch_fixed_point_v1",
    "require_h1_production_output_operand_authority_v1",
    "require_h1_production_output_operand_candidate_v1",
    "solve_h1_production_output_branch_fixed_point_v1",
)
