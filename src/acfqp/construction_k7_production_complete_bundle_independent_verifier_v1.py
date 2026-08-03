"""Independent full-root verification of the production K7 accounting bundle.

This module is intentionally a separate implementation from both the formal
materializer and the root-cap terminal producer.  It consumes only portable
bytes plus the complete replay roots.  It replays the 202-path semantic
closure, reconstructs every V6 counter record, the 182-term projection and
all eight comparison axes, then independently derives the source cap and its
attempt-terminal mapping.

The result is an evaluation-lane typed attestation.  It is not an official
execution, terminal producer, certificate, campaign closure or Gate unlock.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    SHARED_AXES,
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp import campaign_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_semantic_evidence_closure_v1 as closure_v1
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
from acfqp import v075_construction_native_accounting_foundation_v2 as foundation_v2
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as route_ipc_v1
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic_v2
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as multiround_v2
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_FORMAL_ACCOUNTING_MATERIALIZATION_BUNDLE_V1_DOMAIN,
    CONSTRUCTION_K7_FORMAL_ACTUAL_PROJECTION_PROOF_V6_DOMAIN,
    CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_EVALUATION_RECORDER_V1_DOMAIN,
    CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN,
    CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN,
    CONSTRUCTION_K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    TYPED_VERIFICATION_ATTESTATION_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.31"
PROFILE_KEY = "construction_k7_production_complete_bundle_independent_verifier_v1"

FORMAL_SCHEMA_VERSION = "1.0.0"
FORMAL_CONTRACT_VERSION = "2.0.29"
FORMAL_PROFILE_KEY = "construction_k7_formal_accounting_materializer_v1"
TERMINAL_SCHEMA_VERSION = "1.0.0"
TERMINAL_CONTRACT_VERSION = "2.0.30"
TERMINAL_PROFILE_KEY = "construction_k7_root_cap_terminal_authority_v1"

EXPECTED_COUNTER_RECORD_COUNT = 202
EXPECTED_PROJECTION_TERM_COUNT = 182
EXPECTED_PROFILE_NATIVE_ZERO_COUNT = 114
EXPECTED_ROLE_BINDING_COUNT = 8

SOURCE_CAUSE = "CHILD_ACTION_ROW_CAP_EXCEEDED"
CAP_RELATION = "EXISTING_PLUS_UNRESOLVED_CHILD_ACTION_ROWS_GT_REGISTERED_CAP"
TERMINAL_SCOPE = "ROUTE_ATTEMPT"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "ATTEMPT_BUDGET_EXHAUSTED"
ARTIFACT_ROLE = "K7_ROOT_CAP_TERMINAL_ACCOUNTING_COMPLETE_BUNDLE"
VERIFICATION_RESULT = "VALID_EXACT_INDEPENDENT_REPLAY"
VERIFIED_AT_PROTOCOL_STEP = "POST_TERMINAL_COMPLETE_BUNDLE_INDEPENDENT_REPLAY"

K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN = (
    CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN
)
K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN = (
    CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN
)
K7_COMPLETE_BUNDLE_EVALUATION_RECORDER_V1_DOMAIN = (
    CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_EVALUATION_RECORDER_V1_DOMAIN
)
K7_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN = (
    CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN
)

K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN = (
    CONSTRUCTION_K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN
)
K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN = (
    CONSTRUCTION_K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN
)
K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN = (
    CONSTRUCTION_K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN
)
K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN = (
    CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN
)

LOCAL_DOMAINS = frozenset(
    {
        K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN,
        K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN,
        K7_COMPLETE_BUNDLE_EVALUATION_RECORDER_V1_DOMAIN,
        K7_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN,
        K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN,
        K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN,
        K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN,
        K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 8:  # pragma: no cover
    raise RuntimeError("K7 independent-verifier domains must be unique")
if not LOCAL_DOMAINS.issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("K7 independent-verifier domains must be centrally registered")

_ATTESTATION_ISSUER = object()
_VERIFICATION_ISSUER = object()


class ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error(
    ValueError
):
    """A portable role, value, identity, cap, or terminal failed replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error(
        message
    )


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("independent verifier used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256")
    return value


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error(
            f"{label} bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are noncanonical")
    return document


def _verification_profile_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_k7_production_complete_bundle_verification_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "accepted_artifact_role": ARTIFACT_ROLE,
        "semantic_closure_replay_required": True,
        "formal_202_record_reconstruction_required": True,
        "exact_182_term_projection_required": True,
        "source_cap_replay_required": True,
        "terminal_mapping_replay_required": True,
        "materializer_verifier_callable_allowed": False,
        "terminal_producer_verifier_callable_allowed": False,
        "id_only_or_hash_only_acceptance_allowed": False,
        "evaluation_lane_only": True,
        "official_execution_allowed": False,
    }


K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_ID_V1 = _local_id(
    K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN,
    _verification_profile_payload(),
)
K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_ID_V1 = _local_id(
    K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN,
    {
        "schema": "acfqp.construction_k7_production_complete_bundle_semantic_verifier.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "verification_profile_id": K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_ID_V1,
        "module": (
            "acfqp.construction_k7_production_complete_bundle_"
            "independent_verifier_v1"
        ),
        "entrypoint": "verify_k7_production_complete_bundle_independently_v1",
        "producer_implementation_reused": False,
    },
)
K7_TERMINAL_BUNDLE_SCHEMA_ID_V1 = _local_id(
    K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN,
    {
        "schema": "acfqp.construction_k7_verified_artifact_schema_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "artifact_role": ARTIFACT_ROLE,
        "artifact_schema": (
            "acfqp.construction_k7_root_cap_terminal_accounting_bundle.v1"
        ),
        "producer_contract_version": TERMINAL_CONTRACT_VERSION,
    },
)


@dataclass(frozen=True, slots=True)
class K7IndependentTypedVerificationAttestationV1:
    _issuer: InitVar[object]
    artifact_id: str
    artifact_schema_id: str
    route_decision_context_id: str
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: str
    verification_work_counter_record_id: str
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("typed complete-bundle attestation is caller-minted")
        for value, label in (
            (self.artifact_id, "verified artifact"),
            (self.artifact_schema_id, "artifact schema"),
            (self.route_decision_context_id, "route decision context"),
            (self.structural_id, "structural identity"),
            (self.query_id, "query identity"),
            (self.selected_plan_id, "selected plan"),
            (self.threshold_profile_id, "threshold profile"),
            (self.build_epoch_id, "BuildEpoch"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.transaction_id, "transaction"),
            (
                self.verification_work_counter_record_id,
                "verification work counter record",
            ),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_attestation_id",
            content_id(TYPED_VERIFICATION_ATTESTATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_independent_typed_verification_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "artifact_id": self.artifact_id,
            "artifact_schema_id": self.artifact_schema_id,
            "artifact_role": ARTIFACT_ROLE,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "BuildEpoch_id": self.build_epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "semantic_verifier_id": (
                K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_ID_V1
            ),
            "verification_profile_id": (
                K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_ID_V1
            ),
            "verification_result": VERIFICATION_RESULT,
            "verification_work_counter_record_id": (
                self.verification_work_counter_record_id
            ),
            "verified_at_protocol_step": VERIFIED_AT_PROTOCOL_STEP,
            "producer_self_attestation_accepted": False,
            "same_id_cross_role_reuse_accepted": False,
            "official_execution_allowed": False,
        }

    @property
    def attestation_id(self) -> str:
        expected = content_id(
            TYPED_VERIFICATION_ATTESTATION_DOMAIN,
            self._payload(),
        )
        if expected != self._attestation_id:
            _fail("typed complete-bundle attestation changed after issuance")
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "typed_verification_attestation_id": self.attestation_id,
        }


@dataclass(frozen=True, slots=True)
class K7ProductionCompleteBundleVerificationV1:
    _issuer: InitVar[object]
    semantic_evidence_closure_id: str
    semantic_evidence_closure_context_id: str
    formal_materialization_bundle_id: str
    formal_actual_projection_proof_id: str
    actual_work_vector_id: str
    actual_comparison_vector_id: str
    counter_record_ids: tuple[str, ...]
    root_cap_exhaustion_evidence_id: str
    attempt_budget_terminal_authority_id: str
    terminal_accounting_bundle_id: str
    verified_role_bindings: tuple[tuple[str, str, str], ...]
    verified_work_vector: WorkVectorV1 = field(repr=False, compare=False)
    verified_comparison_vector: ComparisonVectorV1 = field(
        repr=False,
        compare=False,
    )
    verification_work_record: CounterRecordV1 = field(repr=False)
    attestation: K7IndependentTypedVerificationAttestationV1
    semantic_closure_sha256: str
    formal_materialization_sha256: str
    terminal_bundle_sha256: str
    semantic_closure_byte_count: int
    formal_materialization_byte_count: int
    terminal_bundle_byte_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.verified_work_vector) is not WorkVectorV1
            or type(self.verified_comparison_vector) is not ComparisonVectorV1
            or type(self.verification_work_record) is not CounterRecordV1
            or type(self.attestation)
            is not K7IndependentTypedVerificationAttestationV1
        ):
            _fail("complete-bundle verification is caller-minted")
        for value, label in (
            (self.semantic_evidence_closure_id, "semantic closure"),
            (self.semantic_evidence_closure_context_id, "closure context"),
            (self.formal_materialization_bundle_id, "formal materialization"),
            (self.formal_actual_projection_proof_id, "projection proof"),
            (self.actual_work_vector_id, "work vector"),
            (self.actual_comparison_vector_id, "comparison vector"),
            *((value, "counter record") for value in self.counter_record_ids),
            (self.root_cap_exhaustion_evidence_id, "root-cap evidence"),
            (self.attempt_budget_terminal_authority_id, "attempt terminal"),
            (self.terminal_accounting_bundle_id, "terminal bundle"),
        ):
            _cid(value, label)
        for value, label in (
            (self.semantic_closure_sha256, "semantic-closure digest"),
            (self.formal_materialization_sha256, "formal-materialization digest"),
            (self.terminal_bundle_sha256, "terminal-bundle digest"),
        ):
            _sha256(value, label)
        for value, label in (
            (self.semantic_closure_byte_count, "semantic-closure bytes"),
            (self.formal_materialization_byte_count, "formal-materialization bytes"),
            (self.terminal_bundle_byte_count, "terminal-bundle bytes"),
        ):
            if _nonnegative(value, label) <= 0:
                _fail(f"{label} must be positive")
        if (
            type(self.counter_record_ids) is not tuple
            or len(self.counter_record_ids) != EXPECTED_COUNTER_RECORD_COUNT
            or len(set(self.counter_record_ids)) != len(self.counter_record_ids)
            or type(self.verified_role_bindings) is not tuple
            or len(self.verified_role_bindings) != EXPECTED_ROLE_BINDING_COUNT
            or any(
                type(row) is not tuple
                or len(row) != 3
                or not all(type(value) is str and value for value in row)
                for row in self.verified_role_bindings
            )
            or len({row[0] for row in self.verified_role_bindings})
            != EXPECTED_ROLE_BINDING_COUNT
            or len({row[2] for row in self.verified_role_bindings})
            != EXPECTED_ROLE_BINDING_COUNT
            or self.attestation.artifact_id != self.terminal_accounting_bundle_id
            or self.verified_work_vector.work_vector_id
            != self.actual_work_vector_id
            or self.verified_comparison_vector.comparison_vector_id
            != self.actual_comparison_vector_id
            or self.verified_comparison_vector.work_vector_id
            != self.verified_work_vector.work_vector_id
            or tuple(
                row.record_id for row in self.verified_work_vector.records
            )
            != self.counter_record_ids
            or self.attestation.verification_work_counter_record_id
            != self.verification_work_record.record_id
            or self.verification_work_record.path
            != "evaluation.semantic_protocol_checks"
            or self.verification_work_record.value != 1
            or self.verification_work_record.observed is not True
            or self.verification_work_record.lane is not LaneEnum.EVALUATION
        ):
            _fail("complete-bundle role, record, or attestation binding changed")
        object.__setattr__(
            self,
            "_verification_id",
            _local_id(
                K7_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_production_complete_bundle_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": (
                K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_ID_V1
            ),
            "semantic_verifier_id": (
                K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_ID_V1
            ),
            "semantic_evidence_closure_id": self.semantic_evidence_closure_id,
            "semantic_evidence_closure_context_id": (
                self.semantic_evidence_closure_context_id
            ),
            "formal_accounting_materialization_bundle_id": (
                self.formal_materialization_bundle_id
            ),
            "formal_actual_projection_proof_id": (
                self.formal_actual_projection_proof_id
            ),
            "actual_work_vector_id": self.actual_work_vector_id,
            "actual_comparison_vector_id": self.actual_comparison_vector_id,
            "counter_record_count": len(self.counter_record_ids),
            "counter_record_ids": list(self.counter_record_ids),
            "root_cap_exhaustion_evidence_id": (
                self.root_cap_exhaustion_evidence_id
            ),
            "attempt_budget_terminal_authority_id": (
                self.attempt_budget_terminal_authority_id
            ),
            "root_cap_terminal_accounting_bundle_id": (
                self.terminal_accounting_bundle_id
            ),
            "verified_role_bindings": [
                {
                    "artifact_role": role,
                    "artifact_schema": schema,
                    "artifact_id": artifact_id,
                }
                for role, schema, artifact_id in self.verified_role_bindings
            ],
            "evaluation_verification_work_counter_record": (
                self.verification_work_record.to_dict()
            ),
            "typed_verification_attestation": self.attestation.to_document(),
            "input_bytes": {
                "semantic_closure": {
                    "sha256": self.semantic_closure_sha256,
                    "byte_count": self.semantic_closure_byte_count,
                },
                "formal_materialization": {
                    "sha256": self.formal_materialization_sha256,
                    "byte_count": self.formal_materialization_byte_count,
                },
                "terminal_bundle": {
                    "sha256": self.terminal_bundle_sha256,
                    "byte_count": self.terminal_bundle_byte_count,
                },
            },
            "full_semantic_roots_replayed": True,
            "all_202_counter_records_recomputed": True,
            "all_182_operational_projection_terms_recomputed": True,
            "all_eight_comparison_axes_recomputed": True,
            "source_cap_and_specific_cause_recomputed": True,
            "terminal_mapping_recomputed": True,
            "all_identity_references_replayed": True,
            "producer_materializer_verifier_called": False,
            "producer_terminal_verifier_called": False,
            "producer_self_report_accepted": False,
            "id_only_or_hash_only_evidence_accepted": False,
            "cross_role_identity_reuse_accepted": False,
            "evaluation_lane_only": True,
            "terminal_artifact_issued": False,
            "certificate_issued": False,
            "logical_occurrence_closed": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def verification_id(self) -> str:
        expected = _local_id(
            K7_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._verification_id:
            _fail("complete-bundle verification changed after issuance")
        return self._verification_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "production_complete_bundle_verification_id": self.verification_id,
        }


@dataclass(frozen=True, slots=True)
class _FormalReplay:
    document: dict[str, Any]
    vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    proof_id: str
    counter_record_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _CapReplay:
    document: dict[str, Any]
    evidence_id: str
    occurrence: Any
    occurrence_row: Any
    cutoff_row: Any
    route: Any


def _replay_semantic_closure(
    *,
    semantic_closure_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> closure_v1.K7SemanticEvidenceClosureV1:
    if type(closure_replay_inputs) is not dict:
        _fail("semantic-closure replay inputs must be one exact dictionary")
    try:
        result = closure_v1.verify_k7_semantic_evidence_closure_bytes_v1(
            raw=semantic_closure_raw,
            **closure_replay_inputs,
        )
    except Exception as error:
        raise ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error(
            "semantic closure failed independent full-root replay"
        ) from error
    document = result.to_document() if hasattr(result, "to_document") else None
    if (
        type(result) is not closure_v1.K7SemanticEvidenceClosureV1
        or type(document) is not dict
        or len(result.resolutions) != EXPECTED_COUNTER_RECORD_COUNT
        or document.get("semantic_replay_complete") is not True
        or document.get("every_path_resolved_exactly_once") is not True
        or document.get("next_atomic_materialization_authorized") is not True
        or document.get("counter_records_issued") is not False
        or document.get("formal_vectors_issued") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("semantic closure is not the exact pre-materialization authority")
    return result


def _official_profiles() -> tuple[Any, Any, Any, Any]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(
        registry,
        comparison,
    )
    registry.validate_official_catalogue()
    stage.validate(registry)
    comparison.validate(registry)
    actual.validate(registry, comparison)
    return registry, stage, comparison, actual


def _recompute_formal_materialization(
    semantic_closure: closure_v1.K7SemanticEvidenceClosureV1,
) -> _FormalReplay:
    registry, stage, comparison, actual = _official_profiles()
    context = semantic_closure.context
    if (
        context.counter_registry_id != registry.registry_id
        or context.stage_profile_id != stage.stage_profile_id
        or tuple(row.path for row in semantic_closure.resolutions)
        != registry.required_paths
        or len({row.path for row in semantic_closure.resolutions})
        != EXPECTED_COUNTER_RECORD_COUNT
    ):
        _fail("semantic closure crossed its exact V6 registry/stage profile")

    records: list[CounterRecordV1] = []
    native_zero_paths: list[str] = []
    for resolution in semantic_closure.resolutions:
        leaf = registry.by_path.get(resolution.path)
        if (
            leaf is None
            or not leaf.required
            or resolution.semantics_id != leaf.semantics_id
            or resolution.owner != leaf.owner
            or resolution.unit != leaf.unit
            or resolution.lane != leaf.lane.value
            or resolution.scope != leaf.scope
            or resolution.reducer != leaf.reducer.value
            or resolution.comparison_axis != leaf.comparison_axis
            or type(resolution.value) is not int
            or resolution.value < 0
        ):
            _fail("semantic closure path differs from exact V6 metadata")
        record = CounterRecordV1(
            registry.registry_id,
            resolution.path,
            resolution.value,
            True,
            resolution.recorder_authority_id,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        )
        records.append(record)
        if (
            resolution.kind
            is closure_v1.SemanticResolutionKindV1.PROFILE_NATIVE_ZERO
        ):
            if record.value != 0:
                _fail("profile-native-zero resolution became nonzero")
            native_zero_paths.append(record.path)

    rows = tuple(records)
    if (
        len(rows) != EXPECTED_COUNTER_RECORD_COUNT
        or tuple(row.path for row in rows) != registry.required_paths
        or len({row.record_id for row in rows}) != len(rows)
        or len(native_zero_paths) != EXPECTED_PROFILE_NATIVE_ZERO_COUNT
        or len(set(native_zero_paths)) != len(native_zero_paths)
        or len({row.recorder_id for row in rows}) != len(rows)
        or not all(row.observed is True for row in rows)
    ):
        _fail("V6 records are missing, duplicated, unobserved, or share recorders")

    vector = WorkVectorV1(
        registry.registry_id,
        context.logical_occurrence_id,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        rows,
    )
    values = vector.values
    for total, successes, failures in (
        ("route.attempts", "route.successes", "route.failures"),
        ("solver.attempts", "solver.successes", "solver.failures"),
        ("process.launches", "process.exit_successes", "process.exit_failures"),
    ):
        if values[total] != values[successes] + values[failures]:
            _fail(f"V6 reconciliation failed for {total}")
    if (
        (
            values["route.attempts"],
            values["route.successes"],
            values["route.failures"],
        )
        != (1, 0, 1)
        or (
            values["solver.attempts"],
            values["solver.successes"],
            values["solver.failures"],
        )
        != (0, 0, 0)
        or any(
            value
            and path.startswith(("local.", "fallback.", "rebuild."))
            and path != "local.causal_candidate_evaluations"
            for path, value in values.items()
        )
    ):
        _fail("work vector is not the exact K7 abstract-failed prefix")

    terms = actual.terms
    operational = tuple(row.path for row in registry.operational_leaves)
    axis_reducers = {row.name: row.reducer for row in comparison.axes}
    if (
        len(terms) != EXPECTED_PROJECTION_TERM_COUNT
        or tuple(row.source_leaf for row in terms) != operational
        or len(set(operational)) != EXPECTED_PROJECTION_TERM_COUNT
        or tuple(axis_reducers) != SHARED_AXES
        or any(
            registry.by_path[term.source_leaf].lane is not LaneEnum.OPERATIONAL
            or term.source_lane is not LaneEnum.OPERATIONAL
            or term.coefficient != 1
            or term.source_semantics_id
            != registry.by_path[term.source_leaf].semantics_id
            or term.target_axis
            != registry.by_path[term.source_leaf].comparison_axis
            or term.reducer != registry.by_path[term.source_leaf].reducer
            or axis_reducers[term.target_axis] is not term.reducer
            for term in terms
        )
        or any(
            row.lane is not LaneEnum.OPERATIONAL and row.path in set(operational)
            for row in registry.leaves
        )
    ):
        _fail("V6 projection is not the exact 182 operational terms")

    axis_values = {axis: 0 for axis in SHARED_AXES}
    for term in terms:
        contribution = values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axis_values[term.target_axis] += contribution
        else:
            axis_values[term.target_axis] = max(
                axis_values[term.target_axis],
                contribution,
            )
    comparison_vector = ComparisonVectorV1(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        tuple((axis, axis_values[axis]) for axis in SHARED_AXES),
    )

    by_path = {row.path: row for row in rows}
    proof_payload = {
        "schema": "acfqp.construction_k7_formal_actual_projection_proof.v6",
        "schema_version": FORMAL_SCHEMA_VERSION,
        "proposed_contract_version": FORMAL_CONTRACT_VERSION,
        "profile_key": FORMAL_PROFILE_KEY,
        "semantic_evidence_closure_id": semantic_closure.closure_id,
        "semantic_evidence_closure_context_id": context.context_id,
        "counter_registry_id": registry.registry_id,
        "stage_profile_id": stage.stage_profile_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": actual.actual_projection_profile_id,
        "work_vector_id": vector.work_vector_id,
        "comparison_vector_id": comparison_vector.comparison_vector_id,
        "counter_record_ids": [row.record_id for row in rows],
        "projected_source_paths": [row.source_leaf for row in terms],
        "projected_counter_record_ids": [
            by_path[row.source_leaf].record_id for row in terms
        ],
        "profile_native_zero_counter_record_ids": [
            by_path[path].record_id for path in native_zero_paths
        ],
        "projection_term_count": len(terms),
        "all_182_operational_leaves_projected_exactly_once": True,
        "nonoperational_leaves_projected": False,
        "profile_native_zero_recorders_explicit": True,
        "eight_axis_sum_max_replayed": True,
        "caller_supplied_actual_comparison_accepted": False,
        "scalar_cost_defined": False,
        "official_execution_allowed": False,
    }
    proof_id = content_id(
        CONSTRUCTION_K7_FORMAL_ACTUAL_PROJECTION_PROOF_V6_DOMAIN,
        proof_payload,
    )
    proof_document = {
        **proof_payload,
        "formal_actual_projection_proof_id": proof_id,
    }
    bundle_payload = {
        "schema": "acfqp.construction_k7_formal_accounting_materialization_bundle.v1",
        "schema_version": FORMAL_SCHEMA_VERSION,
        "proposed_contract_version": FORMAL_CONTRACT_VERSION,
        "profile_key": FORMAL_PROFILE_KEY,
        "semantic_evidence_closure_id": semantic_closure.closure_id,
        "semantic_evidence_closure_context_id": context.context_id,
        "counter_registry_id": registry.registry_id,
        "stage_profile_id": stage.stage_profile_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": actual.actual_projection_profile_id,
        "route_kind": RouteKindEnum.ABSTRACT_FAILED_PREFIX.value,
        "counter_record_count": len(rows),
        "counter_record_ids": [row.record_id for row in rows],
        "work_vector": vector.to_dict(),
        "comparison_vector": comparison_vector.to_dict(),
        "actual_projection_proof": proof_document,
        "semantic_closure_replayed_from_full_roots": True,
        "v1_registry_validator_used": False,
        "formal_accounting_materialized": True,
        "terminal_artifact_issued": False,
        "certificate_issued": False,
        "official_execution_allowed": False,
        "counter_completeness_gate_passed": False,
        "workload_economics_gate_passed": False,
        "scalar_cost_defined": False,
    }
    bundle_id = content_id(
        CONSTRUCTION_K7_FORMAL_ACCOUNTING_MATERIALIZATION_BUNDLE_V1_DOMAIN,
        bundle_payload,
    )
    return _FormalReplay(
        {
            **bundle_payload,
            "formal_accounting_materialization_bundle_id": bundle_id,
        },
        vector,
        comparison_vector,
        proof_id,
        tuple(row.record_id for row in rows),
    )


def _terminal_derivation_registry_id() -> str:
    mapping = foundation_v2.EXPECTED_GENERIC_TERMINAL_MAPPING
    if (
        type(mapping) is not tuple
        or len({code for code, _terminal_class in mapping}) != len(mapping)
        or (TERMINAL_CODE, TERMINAL_CLASS) not in mapping
        or multiround_v2.PROFILE_KEY
        != foundation_v2.EXPECTED_MULTIROUND_SOURCE_PROFILE
    ):
        _fail("frozen generic/specific terminal mapping changed")
    payload = {
        "schema": "acfqp.v075_terminal_derivation_registry.v2",
        "schema_version": foundation_v2.SCHEMA_VERSION,
        "proposed_contract_version": foundation_v2.PROPOSED_CONTRACT_VERSION,
        "profile_key": foundation_v2.PROFILE_KEY,
        "generic_terminal_artifact_schema": "acfqp.terminal_artifact.v1",
        "generic_terminal_mapping": [
            {"terminal_code": code, "terminal_class": terminal_class}
            for code, terminal_class in mapping
        ],
        "specific_derivations": [
            {
                "source_profile": (
                    foundation_v2.EXPECTED_MULTIROUND_SOURCE_PROFILE
                ),
                "source_cause": SOURCE_CAUSE,
                "derived_terminal_scope": TERMINAL_SCOPE,
                "derived_terminal_class": TERMINAL_CLASS,
                "derived_terminal_code": TERMINAL_CODE,
                "specific_cause_retained": True,
                "infeasibility_mapping_allowed": False,
                "caller_terminal_self_report_authoritative": False,
            }
        ],
        "terminal_classification_must_be_recomputed": True,
        "campaign_closure_materialized": False,
    }
    domain = "acfqp:v075-terminal-derivation-registry:v2"
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _root_cap_profile_id() -> str:
    payload = {
        "schema": "acfqp.construction_k7_root_cap_semantics_profile.v1",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "proposed_contract_version": TERMINAL_CONTRACT_VERSION,
        "profile_key": TERMINAL_PROFILE_KEY,
        "source_module": "acfqp.v075_live_dynamic_acquisition_authority_v2",
        "source_schema": "acfqp.v075_live_dynamic_child_closure.v2",
        "source_profile_key": dynamic_v2.PROFILE_KEY,
        "maximum_new_child_action_rows": (
            dynamic_v2.MAXIMUM_NEW_CHILD_ACTION_ROWS
        ),
        "counted_quantity": (
            "existing_child_action_row_count_plus_"
            "unresolved_child_action_row_count"
        ),
        "cap_relation": CAP_RELATION,
        "partial_subset_selection_allowed": False,
        "caller_cap_override_allowed": False,
    }
    return _local_id(K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN, payload)


def _exact_single_role(portable: Any, role: str) -> Any:
    records = getattr(portable, "records", None)
    if type(records) is not tuple:
        _fail("portable production evidence lacks an exact record tuple")
    matches = tuple(row for row in records if getattr(row, "role", None) == role)
    if len(matches) != 1:
        _fail(f"portable production evidence lacks exactly one {role}")
    return matches[0]


def _recompute_root_cap(
    *,
    closure_replay_inputs: Mapping[str, Any],
) -> _CapReplay:
    replay_roots = closure_replay_inputs.get("replay_roots")
    claimed_occurrence = closure_replay_inputs.get("occurrence_authority")
    if type(replay_roots) is not dict:
        _fail("full replay roots are absent from semantic-closure inputs")
    try:
        occurrence = (
            occurrence_v2.replay_k7_occurrence_cutoff_semantic_authorities_v2(
                claimed_occurrence,
                **replay_roots,
            )
        )
        runtime = replay_roots["runtime_envelope"]
        request_replay = replay_roots["request_replay"]
        owned = replay_roots["owned_result"]
        output = worker_v1.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=replay_roots["operational_output_bytes"],
            expected_request_replay=request_replay,
            expected_binding=runtime.binding,
        )
        output_document = output.to_document()
        business = output_document["business_result"]
        if type(business) is not dict:
            _fail("operational output lacks the exact business-result object")
        business_raw = canonical_json_bytes(business)
        portable_document = business["portable_evidence_bundle"]
        if type(portable_document) is not dict:
            _fail("business result lacks embedded portable evidence")
        portable = (
            portable_v2.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                canonical_json_bytes(portable_document)
            )
        )
        closure_record = _exact_single_role(portable, "DYNAMIC_CHILD_CLOSURE")
        closure_verification_record = _exact_single_role(
            portable,
            "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        )
        multiround_record = _exact_single_role(portable, "MULTIROUND_RESULT")
        closure_document = closure_record.artifact_document
        closure_verification_document = (
            closure_verification_record.artifact_document
        )
        multiround_document = multiround_record.artifact_document
        result = owned.result
        route = request_replay.request.route_identity
        route_document = route.to_document()
    except ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error:
        raise
    except Exception as error:
        raise ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error(
            "production cap source failed full-root public replay"
        ) from error

    if (
        type(occurrence)
        is not occurrence_v2.K7OccurrenceCutoffSemanticAuthorityBundleV2
        or type(portable)
        is not portable_v2.V075PortableOccurrenceEvidenceBundleV2
        or type(result)
        is not multiround_v2.V075ObserverSignedMultiroundResultV2
        or type(route)
        is not route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1
        or type(route_document) is not dict
        or type(closure_document) is not dict
        or type(closure_verification_document) is not dict
        or type(multiround_document) is not dict
    ):
        _fail("cap replay returned a foreign authority type")

    occurrence_row = occurrence.occurrence_authority
    cutoff_row = occurrence.cutoff_authority
    existing = closure_document.get("existing_child_action_row_count")
    unresolved = closure_document.get("unresolved_child_action_row_count")
    maximum = closure_document.get("maximum_new_child_action_rows")
    for value, label in (
        (existing, "existing child action rows"),
        (unresolved, "unresolved child action rows"),
        (maximum, "maximum child action rows"),
    ):
        _nonnegative(value, label)

    logical = route.logical_occurrence
    attempt = route.route_attempt
    context = route.route_context
    decision = route.decision_point
    transaction = route.transaction
    business_sha = hashlib.sha256(business_raw).hexdigest()
    terminal_registry_id = _terminal_derivation_registry_id()
    if (
        result.status
        is not (
            multiround_v2.V075ObserverSignedMultiroundTerminalStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
        or result.child_closure_status
        is not (
            dynamic_v2.V075LiveDynamicChildClosureStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
        or occurrence_row.terminal_status != SOURCE_CAUSE
        or occurrence_row.terminal_kind != "COMPLETED"
        or occurrence_row.route_attempt_outcome != "FAILURE"
        or (
            occurrence_row.route_attempt_count,
            occurrence_row.route_success_count,
            occurrence_row.route_failure_count,
        )
        != (1, 0, 1)
        or closure_record.semantic_artifact_id != result.child_closure_id
        or closure_document.get("closure_id") != result.child_closure_id
        or closure_document.get("schema")
        != "acfqp.v075_live_dynamic_child_closure.v2"
        or closure_document.get("profile_key") != dynamic_v2.PROFILE_KEY
        or closure_document.get("status") != SOURCE_CAUSE
        or closure_document.get("terminal_class") != TERMINAL_CLASS
        or maximum != dynamic_v2.MAXIMUM_NEW_CHILD_ACTION_ROWS
        or unresolved <= 0
        or existing + unresolved <= maximum
        or closure_document.get("discovery_intent_ids") != []
        or closure_document.get("validation_template_ids") != []
        or closure_document.get("discovery_intents") != []
        or closure_document.get("validation_templates") != []
        or closure_document.get("all_root_support_descriptors_examined") is not True
        or closure_document.get("complete_child_catalogues") is not True
        or closure_document.get("all_or_none_child_base_authorization") is not True
        or closure_document.get("official_execution_allowed") is not False
        or closure_document.get("plan_certificate") is not False
        or closure_document.get("infeasibility_certificate") is not False
        or closure_verification_record.semantic_artifact_id
        != result.child_closure_verification_id
        or closure_verification_document.get("verification_id")
        != result.child_closure_verification_id
        or closure_verification_document.get("closure_id")
        != result.child_closure_id
        or closure_verification_document.get("status") != SOURCE_CAUSE
        or closure_verification_document.get("semantic_replay_complete") is not True
        or closure_verification_document.get("discovery_intent_ids") != []
        or closure_verification_document.get("validation_template_ids") != []
        or multiround_record.semantic_artifact_id != result.result_id
        or multiround_document.get("result_id") != result.result_id
        or multiround_document.get("status") != SOURCE_CAUSE
        or multiround_document.get("child_closure_status") != SOURCE_CAUSE
        or multiround_document.get("child_closure_id") != result.child_closure_id
        or multiround_document.get("child_closure_verification_id")
        != result.child_closure_verification_id
        or multiround_document.get("plan_certificate") is not False
        or multiround_document.get("infeasibility_certificate") is not False
        or multiround_document.get("official_execution_allowed") is not False
        or business.get("owned_partial_result_id") != owned.wrapper_id
        or business.get("portable_evidence_bundle_id") != portable.bundle_id
        or portable.bundle_id != business.get("portable_evidence_bundle_id")
        or portable.occurrence_id != occurrence_row.scientific_occurrence_id
        or output_document.get("business_result_id")
        != occurrence_row.runtime_business_result_id
        or output_document.get("business_result_sha256") != business_sha
        or output_document.get("business_result_byte_count") != len(business_raw)
        or occurrence_row.runtime_business_result_sha256 != business_sha
        or occurrence_row.runtime_business_result_byte_count != len(business_raw)
        or occurrence_row.logical_occurrence_id != logical.logical_occurrence_id
        or occurrence_row.route_attempt_id != attempt.route_attempt_id
        or occurrence_row.decision_point_id != decision.decision_point_id
        or occurrence_row.owned_partial_result_id != owned.wrapper_id
        or occurrence_row.partial_native_transcript_id
        != owned.transcript.transcript_id
        or occurrence_row.production_runtime_envelope_id != runtime.envelope_id
        or occurrence_row.portable_request_replay_id != request_replay.replay_id
        or cutoff_row.terminal_closure_observation_id
        != occurrence_row.terminal_closure_observation_id
        or logical.logical_occurrence_id != context.logical_occurrence_id
        or attempt.logical_occurrence_id != logical.logical_occurrence_id
        or attempt.route_attempt_id != context.route_attempt_id
        or attempt.build_epoch_id != context.build_epoch_id
        or logical.protocol_id != context.protocol_id
        or logical.structural_id != context.structural_id
        or logical.query_id != context.query_id
        or logical.selected_plan_id != context.selected_plan_id
        or logical.threshold_profile_id != context.threshold_profile_id
        or decision.route_decision_context_id
        != context.route_decision_context_id
        or transaction.logical_occurrence_id != logical.logical_occurrence_id
        or transaction.route_attempt_id != attempt.route_attempt_id
        or transaction.decision_point_id != decision.decision_point_id
        or transaction.transaction_index != decision.transaction_index
        or logical.rebuild_policy_id
        != campaign_v1.RebuildPolicyV1().rebuild_policy_id
        or terminal_registry_id != _terminal_derivation_registry_id()
    ):
        _fail("source cap, cause, terminal mapping, or route identity changed")

    cap_payload = {
        "schema": "acfqp.construction_k7_root_cap_exhaustion_evidence.v1",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "proposed_contract_version": TERMINAL_CONTRACT_VERSION,
        "profile_key": TERMINAL_PROFILE_KEY,
        "occurrence_authority_bundle_id": occurrence.bundle_id,
        "occurrence_authority_id": occurrence_row.authority_id,
        "operational_cutoff_authority_id": cutoff_row.authority_id,
        "production_runtime_envelope_id": occurrence_row.production_runtime_envelope_id,
        "portable_request_replay_id": occurrence_row.portable_request_replay_id,
        "owned_partial_result_id": owned.wrapper_id,
        "partial_native_transcript_id": owned.transcript.transcript_id,
        "partial_native_terminal_id": occurrence_row.transcript_terminal_id,
        "transcript_document_sha256": occurrence_row.transcript_document_sha256,
        "ordered_chain_node_count": len(occurrence_row.ordered_chain_node_ids),
        "terminal_closure_observation_id": (
            occurrence_row.terminal_closure_observation_id
        ),
        "runtime_business_result_id": occurrence_row.runtime_business_result_id,
        "runtime_business_result_sha256": (
            occurrence_row.runtime_business_result_sha256
        ),
        "runtime_business_result_byte_count": (
            occurrence_row.runtime_business_result_byte_count
        ),
        "portable_evidence_bundle_id": portable.bundle_id,
        "multiround_record_id": multiround_record.record_id,
        "multiround_result_id": result.result_id,
        "child_closure_record_id": closure_record.record_id,
        "child_closure_id": result.child_closure_id,
        "child_closure_verification_record_id": (
            closure_verification_record.record_id
        ),
        "child_closure_verification_id": result.child_closure_verification_id,
        "logical_occurrence_id": occurrence_row.logical_occurrence_id,
        "rebuild_policy_id": logical.rebuild_policy_id,
        "route_attempt_id": occurrence_row.route_attempt_id,
        "decision_point_id": occurrence_row.decision_point_id,
        "transaction_id": transaction.transaction_id,
        "transaction_index": transaction.transaction_index,
        "route_cap_profile_id": transaction.route_cap_profile_id,
        "action_row_cap_profile_id": _root_cap_profile_id(),
        "terminal_derivation_registry_id": terminal_registry_id,
        "source_cause": SOURCE_CAUSE,
        "existing_child_action_row_count": existing,
        "unresolved_child_action_row_count": unresolved,
        "total_child_action_row_count": existing + unresolved,
        "maximum_new_child_action_rows": maximum,
        "cap_relation": CAP_RELATION,
        "cap_exceeded_from_exact_source_closure": True,
        "issuer_owned_multiround_result_replayed": True,
        "actual_business_result_bytes_replayed": True,
        "full_owner_transcript_replayed": True,
        "cap_claim_derived_from_status_string_or_hash_only": False,
        "default_rebuild_policy_replayed": True,
        "rebuild_allowed": False,
        "specific_cause_retained": True,
        "worker_self_claim_accepted": False,
        "caller_cap_value_accepted": False,
        "infeasibility_mapping_allowed": False,
        "official_execution_allowed": False,
    }
    evidence_id = _local_id(
        K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN,
        cap_payload,
    )
    return _CapReplay(
        {
            **cap_payload,
            "root_cap_exhaustion_evidence_id": evidence_id,
        },
        evidence_id,
        occurrence,
        occurrence_row,
        cutoff_row,
        route,
    )


def _expected_terminal_bundle(
    *,
    formal: _FormalReplay,
    semantic_closure: closure_v1.K7SemanticEvidenceClosureV1,
    cap: _CapReplay,
) -> tuple[dict[str, Any], str, str]:
    vector = formal.vector
    values = vector.values
    context = semantic_closure.context
    occurrence = cap.occurrence_row
    route = cap.route
    route_context = route.route_context
    profile = route.profile
    if (
        context.occurrence_authority_bundle_id != cap.occurrence.bundle_id
        or context.occurrence_authority_id != occurrence.authority_id
        or context.cutoff_authority_id != cap.cutoff_row.authority_id
        or context.production_runtime_envelope_id
        != occurrence.production_runtime_envelope_id
        or context.portable_request_replay_id
        != occurrence.portable_request_replay_id
        or context.logical_occurrence_id != occurrence.logical_occurrence_id
        or context.route_attempt_id != occurrence.route_attempt_id
        or context.decision_point_id != occurrence.decision_point_id
        or context.terminal_closure_observation_id
        != occurrence.terminal_closure_observation_id
        or vector.subject_id != occurrence.logical_occurrence_id
        or vector.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or formal.comparison_vector.subject_id != vector.subject_id
        or formal.comparison_vector.route_kind
        is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or formal.comparison_vector.work_vector_id != vector.work_vector_id
        or context.counter_registry_id != profile.counter_registry_id
        or context.stage_profile_id != profile.stage_profile_id
        or context.boundary_profile_id != profile.boundary_manifest_id
        or context.execution_profile_id != profile.execution_profile_id
        or route_context.counter_registry_id != profile.counter_registry_id
        or route_context.comparison_profile_id != profile.comparison_profile_id
        or (
            values["route.attempts"],
            values["route.successes"],
            values["route.failures"],
        )
        != (1, 0, 1)
    ):
        _fail("semantic, formal, cap, and route identities do not join")

    formal_id = formal.document["formal_accounting_materialization_bundle_id"]
    terminal_payload = {
        "schema": "acfqp.construction_k7_attempt_budget_terminal_authority.v1",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "proposed_contract_version": TERMINAL_CONTRACT_VERSION,
        "profile_key": TERMINAL_PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": TERMINAL_CODE,
        "specific_cause": SOURCE_CAUSE,
        "root_cap_exhaustion_evidence_id": cap.evidence_id,
        "logical_occurrence_id": occurrence.logical_occurrence_id,
        "rebuild_policy_id": cap.document["rebuild_policy_id"],
        "route_attempt_id": occurrence.route_attempt_id,
        "decision_point_id": occurrence.decision_point_id,
        "transaction_id": route.transaction.transaction_id,
        "transaction_index": route.transaction.transaction_index,
        "route_cap_profile_id": route.transaction.route_cap_profile_id,
        "terminal_derivation_registry_id": (
            cap.document["terminal_derivation_registry_id"]
        ),
        "child_closure_id": cap.document["child_closure_id"],
        "terminal_closure_observation_id": (
            occurrence.terminal_closure_observation_id
        ),
        "formal_accounting_materialization_bundle_id": formal_id,
        "semantic_evidence_closure_id": semantic_closure.closure_id,
        "semantic_evidence_closure_context_id": context.context_id,
        "formal_actual_projection_proof_id": formal.proof_id,
        "actual_work_vector_id": vector.work_vector_id,
        "actual_comparison_vector_id": (
            formal.comparison_vector.comparison_vector_id
        ),
        "counter_record_count": len(formal.counter_record_ids),
        "counter_record_ids": list(formal.counter_record_ids),
        "route_attempt_count": values["route.attempts"],
        "route_success_count": values["route.successes"],
        "route_failure_count": values["route.failures"],
        "all_observed_work_preserved": True,
        "failed_route_work_discarded": False,
        "counter_values_rewritten_by_terminal": False,
        "worker_terminal_self_report_authoritative": False,
        "terminal_recomputed_from_source_cap_authority": True,
        "trusted_budget_replay_used": False,
        "local_transaction_budget_outcome_claimed": False,
        "construction_root_cap_derivation_rule_used": True,
        "terminal_is_infeasibility_certificate": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
        "logical_occurrence_closed": False,
        "rebuild_policy_bound_for_successor_occurrence_closure": True,
        "campaign_closure_issued": False,
        "official_execution_allowed": False,
        "counter_completeness_gate_passed": False,
        "workload_economics_gate_passed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
    }
    terminal_id = _local_id(
        K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN,
        terminal_payload,
    )
    terminal_document = {
        **terminal_payload,
        "attempt_budget_terminal_authority_id": terminal_id,
    }
    bundle_payload = {
        "schema": "acfqp.construction_k7_root_cap_terminal_accounting_bundle.v1",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "proposed_contract_version": TERMINAL_CONTRACT_VERSION,
        "profile_key": TERMINAL_PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": TERMINAL_CODE,
        "specific_cause": SOURCE_CAUSE,
        "formal_accounting_materialization_bundle": formal.document,
        "root_cap_exhaustion_evidence": cap.document,
        "attempt_budget_terminal_authority": terminal_document,
        "complete_202_path_work_embedded": True,
        "id_only_materialization_accepted": False,
        "worker_terminal_self_report_authoritative": False,
        "forged_terminal_classification_accepted": False,
        "incomplete_work_accepted": False,
        "terminal_is_infeasibility_certificate": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
        "logical_occurrence_closed": False,
        "campaign_closure_issued": False,
        "official_execution_allowed": False,
        "counter_completeness_gate_passed": False,
        "workload_economics_gate_passed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
    }
    bundle_id = _local_id(
        K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
        bundle_payload,
    )
    return (
        {
            **bundle_payload,
            "root_cap_terminal_accounting_bundle_id": bundle_id,
        },
        terminal_id,
        bundle_id,
    )


def _evaluation_record(
    *,
    registry: Any,
    terminal_bundle_id: str,
    semantic_closure_sha256: str,
    formal_materialization_sha256: str,
    terminal_bundle_sha256: str,
    route: Any,
) -> CounterRecordV1:
    path = "evaluation.semantic_protocol_checks"
    leaf = registry.by_path.get(path)
    if (
        leaf is None
        or leaf.required
        or leaf.lane is not LaneEnum.EVALUATION
        or leaf.comparison_axis is not None
    ):
        _fail("V6 evaluation verification leaf changed")
    recorder_id = _local_id(
        K7_COMPLETE_BUNDLE_EVALUATION_RECORDER_V1_DOMAIN,
        {
            "schema": "acfqp.construction_k7_production_complete_bundle_evaluation_recorder.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": (
                K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_ID_V1
            ),
            "semantic_verifier_id": (
                K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_ID_V1
            ),
            "artifact_role": ARTIFACT_ROLE,
            "artifact_id": terminal_bundle_id,
            "RouteDecisionContext_id": (
                route.route_context.route_decision_context_id
            ),
            "logical_occurrence_id": (
                route.logical_occurrence.logical_occurrence_id
            ),
            "route_attempt_id": route.route_attempt.route_attempt_id,
            "decision_point_id": route.decision_point.decision_point_id,
            "transaction_id": route.transaction.transaction_id,
            "semantic_closure_sha256": semantic_closure_sha256,
            "formal_materialization_sha256": formal_materialization_sha256,
            "terminal_bundle_sha256": terminal_bundle_sha256,
            "evaluation_event_count": 1,
            "operational_route_work": False,
        },
    )
    return CounterRecordV1(
        registry.registry_id,
        path,
        1,
        True,
        recorder_id,
        leaf.semantics_id,
        leaf.owner,
        leaf.unit,
        leaf.lane,
        leaf.scope,
        leaf.reducer,
    )


def verify_k7_production_complete_bundle_independently_v1(
    *,
    semantic_closure_raw: bytes,
    formal_materialization_raw: bytes,
    terminal_accounting_bundle_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> K7ProductionCompleteBundleVerificationV1:
    """Independently recompute the complete K7 work/cap/terminal chain."""

    semantic_document = _canonical_object(
        semantic_closure_raw,
        "semantic closure",
    )
    formal_document = _canonical_object(
        formal_materialization_raw,
        "formal materialization",
    )
    terminal_document = _canonical_object(
        terminal_accounting_bundle_raw,
        "terminal accounting bundle",
    )
    semantic_closure = _replay_semantic_closure(
        semantic_closure_raw=semantic_closure_raw,
        closure_replay_inputs=closure_replay_inputs,
    )
    if semantic_document != semantic_closure.to_document():
        _fail("semantic closure bytes differ from independent root replay")
    formal = _recompute_formal_materialization(semantic_closure)
    if formal_document != formal.document:
        _fail("formal 202-record materialization differs from independent replay")
    cap = _recompute_root_cap(closure_replay_inputs=closure_replay_inputs)
    expected_terminal, terminal_authority_id, terminal_bundle_id = (
        _expected_terminal_bundle(
            formal=formal,
            semantic_closure=semantic_closure,
            cap=cap,
        )
    )
    if (
        terminal_document != expected_terminal
        or terminal_document.get("formal_accounting_materialization_bundle")
        != formal_document
        or terminal_document.get("root_cap_exhaustion_evidence") != cap.document
        or terminal_document.get("specific_cause") != SOURCE_CAUSE
        or terminal_document.get("terminal_scope") != TERMINAL_SCOPE
        or terminal_document.get("terminal_class") != TERMINAL_CLASS
        or terminal_document.get("terminal_code") != TERMINAL_CODE
    ):
        _fail("terminal bundle, cap, cause, or classification differs from replay")

    route = cap.route
    logical = route.logical_occurrence
    attempt = route.route_attempt
    context = route.route_context
    semantic_sha = hashlib.sha256(semantic_closure_raw).hexdigest()
    formal_sha = hashlib.sha256(formal_materialization_raw).hexdigest()
    terminal_sha = hashlib.sha256(terminal_accounting_bundle_raw).hexdigest()
    registry = registry_v6.official_counter_registry_v6()
    work_record = _evaluation_record(
        registry=registry,
        terminal_bundle_id=terminal_bundle_id,
        semantic_closure_sha256=semantic_sha,
        formal_materialization_sha256=formal_sha,
        terminal_bundle_sha256=terminal_sha,
        route=route,
    )
    attestation = K7IndependentTypedVerificationAttestationV1(
        _ATTESTATION_ISSUER,
        terminal_bundle_id,
        K7_TERMINAL_BUNDLE_SCHEMA_ID_V1,
        context.route_decision_context_id,
        logical.structural_id,
        logical.query_id,
        logical.selected_plan_id,
        logical.threshold_profile_id,
        attempt.build_epoch_id,
        logical.logical_occurrence_id,
        attempt.route_attempt_id,
        route.decision_point.decision_point_id,
        route.transaction.transaction_id,
        work_record.record_id,
    )
    roles = (
        (
            "K7_SEMANTIC_EVIDENCE_CLOSURE",
            "acfqp.construction_k7_semantic_evidence_closure.v1",
            semantic_closure.closure_id,
        ),
        (
            "K7_FORMAL_ACTUAL_PROJECTION_PROOF",
            "acfqp.construction_k7_formal_actual_projection_proof.v6",
            formal.proof_id,
        ),
        (
            "K7_FORMAL_ACCOUNTING_MATERIALIZATION",
            "acfqp.construction_k7_formal_accounting_materialization_bundle.v1",
            formal.document["formal_accounting_materialization_bundle_id"],
        ),
        (
            "K7_ACTUAL_WORK_VECTOR",
            "acfqp.work_vector.v1",
            formal.vector.work_vector_id,
        ),
        (
            "K7_ACTUAL_COMPARISON_VECTOR",
            "acfqp.comparison_vector.v1",
            formal.comparison_vector.comparison_vector_id,
        ),
        (
            "K7_ROOT_CAP_EXHAUSTION_EVIDENCE",
            "acfqp.construction_k7_root_cap_exhaustion_evidence.v1",
            cap.evidence_id,
        ),
        (
            "K7_ATTEMPT_BUDGET_TERMINAL_AUTHORITY",
            "acfqp.construction_k7_attempt_budget_terminal_authority.v1",
            terminal_authority_id,
        ),
        (
            ARTIFACT_ROLE,
            "acfqp.construction_k7_root_cap_terminal_accounting_bundle.v1",
            terminal_bundle_id,
        ),
    )
    return K7ProductionCompleteBundleVerificationV1(
        _VERIFICATION_ISSUER,
        semantic_closure.closure_id,
        semantic_closure.context.context_id,
        formal.document["formal_accounting_materialization_bundle_id"],
        formal.proof_id,
        formal.vector.work_vector_id,
        formal.comparison_vector.comparison_vector_id,
        formal.counter_record_ids,
        cap.evidence_id,
        terminal_authority_id,
        terminal_bundle_id,
        roles,
        formal.vector,
        formal.comparison_vector,
        work_record,
        attestation,
        semantic_sha,
        formal_sha,
        terminal_sha,
        len(semantic_closure_raw),
        len(formal_materialization_raw),
        len(terminal_accounting_bundle_raw),
    )


def verify_k7_production_complete_bundle_verification_bytes_v1(
    *,
    raw: bytes,
    semantic_closure_raw: bytes,
    formal_materialization_raw: bytes,
    terminal_accounting_bundle_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> K7ProductionCompleteBundleVerificationV1:
    """Replay portable verification bytes from the original complete roots."""

    claimed = _canonical_object(raw, "complete-bundle verification")
    expected = verify_k7_production_complete_bundle_independently_v1(
        semantic_closure_raw=semantic_closure_raw,
        formal_materialization_raw=formal_materialization_raw,
        terminal_accounting_bundle_raw=terminal_accounting_bundle_raw,
        closure_replay_inputs=closure_replay_inputs,
    )
    if claimed != expected.to_document():
        _fail("portable complete-bundle verification differs from fresh replay")
    return expected


__all__ = (
    "ARTIFACT_ROLE",
    "ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error",
    "EXPECTED_COUNTER_RECORD_COUNT",
    "EXPECTED_PROFILE_NATIVE_ZERO_COUNT",
    "EXPECTED_PROJECTION_TERM_COUNT",
    "K7_COMPLETE_BUNDLE_EVALUATION_RECORDER_V1_DOMAIN",
    "K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_ID_V1",
    "K7_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN",
    "K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_ID_V1",
    "K7_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN",
    "K7_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN",
    "K7IndependentTypedVerificationAttestationV1",
    "K7ProductionCompleteBundleVerificationV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "VERIFICATION_RESULT",
    "verify_k7_production_complete_bundle_independently_v1",
    "verify_k7_production_complete_bundle_verification_bytes_v1",
)
