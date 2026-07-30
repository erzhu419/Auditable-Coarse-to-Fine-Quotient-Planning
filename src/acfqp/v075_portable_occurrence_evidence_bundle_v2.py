"""Portable construction evidence bundle for observer-signed V0-075 runs.

The bundle is a byte-complete, topologically ordered artifact table.  It is
deliberately a construction transport: it does not turn the in-process runner
into a production authority, a plan certificate, or held-out evidence.  A
later semantic-registry authority must independently replay every role before
production use.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field, fields, is_dataclass
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle
from acfqp import v075_batched_observer_authority_v2 as lineage
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_graph_semantics_v1 as graph


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.61.0"
PROFILE_KEY = "v075_portable_occurrence_evidence_bundle_v2"
MAX_ARTIFACT_COUNT = 131_072
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_BYTES = 512 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
SEMANTIC_REGISTRY_REPLAY_COMPLETE = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_EVIDENCE_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PRODUCTION_BLOCKER = (
    "the portable bundle proves canonical transport topology only; production "
    "IPC, a role-specific semantic registry, total-lift authority, accounting, "
    "and independent production verification remain absent"
)

DOMAIN_TAGS = {
    "derived_artifact": (
        "acfqp:v075-portable-occurrence-evidence-derived-artifact:v2"
    ),
    "record": "acfqp:v075-portable-occurrence-evidence-record:v2",
    "bundle": "acfqp:v075-portable-occurrence-evidence-bundle:v2",
}

REQUIRED_ROOT_NAMES = (
    "initial_schedule",
    "initial_schedule_verification",
    "root_execution",
    "root_model_epoch",
    "child_closure",
    "child_closure_verification",
    "child_execution_ledger",
    "child_execution_verification",
    "child_replanning_barrier",
    "child_replanning_barrier_verification",
    "promotion_decisions",
    "promotion_decision_verifications",
    "promotion_replanning_barriers",
    "promotion_replanning_barrier_verifications",
    "final_model_epoch",
    "controlled_journal_closure",
    "construction_lineage",
    "construction_lifecycle",
    "closed_planning_input",
    "closed_planning_proof",
    "closed_reconciliation",
    "multiround_result",
)


class V075PortableOccurrenceEvidenceV2InvariantViolation(ValueError):
    """A portable evidence record or graph was malformed."""


class V075PortableOccurrenceEvidenceProductionV2NotReady(RuntimeError):
    """The construction bundle cannot authorize production."""


def _fail(message: str) -> NoReturn:
    raise V075PortableOccurrenceEvidenceV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableOccurrenceEvidenceV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V075PortableOccurrenceEvidenceV2InvariantViolation(
            str(error)
        ) from error


def _strict_json_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_ARTIFACT_BYTES:
        _fail(f"{label} bytes are empty, untyped, or exceed their cap")

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{label} contains a duplicate JSON key")
            result[key] = value
        return result

    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=no_duplicates,
            parse_constant=lambda value: _fail(
                f"{label} contains forbidden numeric constant {value}"
            ),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        if type(error) is V075PortableOccurrenceEvidenceV2InvariantViolation:
            raise
        raise V075PortableOccurrenceEvidenceV2InvariantViolation(
            f"{label} is not strict UTF-8 canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


_PRIVATE_SERIALIZATION_FLAGS = frozenset(
    {
        "private_material_serialized",
        "private_law_serialized",
        "private_salt_serialized",
        "private_kernel_serialized",
        "individual_random_words_retained",
        "individual_random_words_serialized",
    }
)

_FORBIDDEN_TRUE_CLAIM_KEYS = frozenset(
    {
        "fresh_heldout_accessed",
        "infeasibility_certificate",
        "official_execution_allowed",
        "official_execution_unlocked",
        "plan_certificate",
        "production_authorizing",
        "production_positive_path_ready",
        "scientific_endpoint_credit_allowed",
        "semantic_registry_replay_complete",
    }
)

_FORBIDDEN_PRIVATE_PAYLOAD_KEYS = frozenset(
    {
        "individual_random_words",
        "private_environment",
        "private_kernel",
        "private_law",
        "private_salt",
    }
)


def _assert_public_artifact_document(value: Any) -> None:
    if type(value) is list:
        for item in value:
            _assert_public_artifact_document(item)
        return
    if type(value) is not dict:
        return
    for key, item in value.items():
        if key in _FORBIDDEN_TRUE_CLAIM_KEYS and item is not False:
            _fail("portable artifact attempts to unlock a forbidden claim")
        if key in _PRIVATE_SERIALIZATION_FLAGS and item is not False:
            _fail("portable artifact attempts to serialize private material")
        if key in _FORBIDDEN_PRIVATE_PAYLOAD_KEYS:
            _fail("portable artifact contains undeclared private material")
        _assert_public_artifact_document(item)


@dataclass(frozen=True, slots=True)
class _ArtifactSpec:
    concrete_type: type
    role: str
    schema: str
    identity_attribute: str | None


def _spec(
    concrete_type: type,
    role: str,
    schema: str,
    identity_attribute: str | None,
) -> _ArtifactSpec:
    return _ArtifactSpec(
        concrete_type,
        role,
        schema,
        identity_attribute,
    )


_STATIC_SPECS = (
    _spec(
        backend.V075BatchNativeOccurrenceIdentityV1,
        "OCCURRENCE_IDENTITY",
        "acfqp.v075_batch_native_occurrence.v1",
        "occurrence_id",
    ),
    _spec(
        acquisition.V075InitialRowIntentV2,
        "INITIAL_ROW_INTENT",
        "acfqp.v075_five_arm_initial_row_intent.v2",
        "intent_id",
    ),
    _spec(
        acquisition.V075InitialAcquisitionScheduleV2,
        "INITIAL_ACQUISITION_SCHEDULE",
        "acfqp.v075_five_arm_initial_acquisition_schedule.v2",
        "schedule_id",
    ),
    _spec(
        acquisition.V075InitialAcquisitionVerificationV2,
        "INITIAL_ACQUISITION_VERIFICATION",
        "acfqp.v075_five_arm_initial_acquisition_verification.v2",
        "verification_id",
    ),
    _spec(
        graph.V075SymbolicGraphStateV1,
        "SYMBOLIC_GRAPH_STATE",
        "acfqp.v075_heldout_symbolic_graph_state.v2",
        "state_id",
    ),
    _spec(
        graph.V075LegalActionCatalogueV1,
        "LEGAL_ACTION_CATALOGUE",
        "acfqp.v075_heldout_legal_action_catalogue.v2",
        "catalogue_id",
    ),
    _spec(
        graph.V075ObservationRowBindingV1,
        "OBSERVATION_ROW_BINDING",
        "acfqp.v075_heldout_observation_row_binding.v2",
        "row_binding_id",
    ),
    _spec(
        graph.V075BatchAggregateSupportEvidenceV1,
        "OBSERVER_SIGNED_SUPPORT_EVIDENCE",
        "acfqp.v075_batch_aggregate_support_evidence.v1",
        "evidence_id",
    ),
    _spec(
        graph.V075SharedSupportEpochV1,
        "SHARED_SUPPORT_EPOCH",
        "acfqp.v075_heldout_shared_support_epoch.v2",
        "epoch_id",
    ),
    _spec(
        graph.V075SharedSupportChainV1,
        "SHARED_SUPPORT_CHAIN",
        "acfqp.v075_heldout_shared_support_chain.v2",
        "chain_id",
    ),
    _spec(
        graph.V075FiveArmPairingAuthorityV1,
        "PAIRING_AUTHORITY",
        "acfqp.v075_five_arm_pairing_authority.v2",
        "pairing_authority_id",
    ),
    _spec(
        graph.V075TransitionStreamIdentityV1,
        "TRANSITION_STREAM",
        "acfqp.v075_arm_isolated_stream_pair.v2",
        "stream_id",
    ),
    _spec(
        observer.V075ObserverOpenAuthorityBindingV2,
        "OBSERVER_OPEN_BINDING",
        "acfqp.v075_observer_open_authority_binding.v2",
        "binding_id",
    ),
    _spec(
        observer.V075BatchObservationRequestV2,
        "SIGNED_BATCH_REQUEST",
        "acfqp.v075_batch_observation_request.v2",
        "request_id",
    ),
    _spec(
        observer.V075BatchOutcomeAggregateV2,
        "SIGNED_BATCH_OUTCOME",
        "acfqp.v075_batch_outcome_aggregate.v2",
        None,
    ),
    _spec(
        observer.V075SignedObservationBatchV2,
        "SIGNED_OBSERVATION_BATCH",
        "acfqp.v075_signed_observation_batch.v2",
        "batch_id",
    ),
    _spec(
        observer.V075ObserverBatchJournalEntryV2,
        "SIGNED_BATCH_JOURNAL_ENTRY",
        "acfqp.v075_observer_batch_journal_entry.v2",
        "entry_id",
    ),
    _spec(
        observer.V075ObserverBatchJournalClosureV2,
        "SIGNED_BATCH_JOURNAL_CLOSURE",
        "acfqp.v075_observer_batch_journal_closure.v2",
        "closure_id",
    ),
    _spec(
        observer.V075ObserverBatchClosureVerificationV2,
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
        "acfqp.v075_observer_batch_journal_closure_verification.v2",
        "verification_id",
    ),
    _spec(
        control.V075SignedBatchJournalHeadV2,
        "SIGNED_CONTROL_JOURNAL_HEAD",
        "acfqp.v075_observer_signed_batch_journal_head.v2",
        "head_id",
    ),
    _spec(
        control.V075ObserverSignedBatchAppendReceiptV2,
        "SIGNED_APPEND_RECEIPT",
        "acfqp.v075_observer_signed_batch_append_receipt.v2",
        "receipt_id",
    ),
    _spec(
        control.V075ControlledCompleteSupportFreezeV2,
        "CONTROLLED_COMPLETE_SUPPORT_FREEZE",
        "acfqp.v075_controlled_complete_support_freeze.v2",
        "freeze_id",
    ),
    _spec(
        control.V075OpenControlledBatchPrefixVerificationV2,
        "OPEN_CONTROLLED_PREFIX_VERIFICATION",
        "acfqp.v075_open_controlled_batch_prefix_verification.v2",
        "verification_id",
    ),
    _spec(
        control.V075ObserverSignedBatchControlClosureV2,
        "SIGNED_CONTROL_CLOSURE",
        "acfqp.v075_observer_signed_batch_control_closure.v2",
        "control_closure_id",
    ),
    _spec(
        control.V075SignedBatchControlReconciliationV2,
        "SIGNED_CONTROL_RECONCILIATION",
        "acfqp.v075_observer_signed_batch_control_reconciliation.v2",
        "reconciliation_id",
    ),
    _spec(
        control.V075ControlledBatchJournalClosureV2,
        "CONTROLLED_JOURNAL_CLOSURE",
        "acfqp.v075_controlled_batch_journal_closure.v2",
        None,
    ),
    _spec(
        runner.V075ObserverSignedRootExecutionV2,
        "ROOT_EXECUTION",
        "acfqp.v075_observer_signed_root_execution.v2",
        "execution_id",
    ),
    _spec(
        live_model.V075LiveModelRowSourceBindingV2,
        "LIVE_ROW_SOURCE_BINDING",
        "acfqp.v075_live_model_row_source_binding.v2",
        "binding_id",
    ),
    _spec(
        live_model.V075LiveIncrementalModelEpochV2,
        "LIVE_MODEL_EPOCH",
        "acfqp.v075_live_incremental_model_epoch.v2",
        "model_epoch_id",
    ),
    _spec(
        planning.V075NumericalModelV2,
        "NUMERICAL_MODEL",
        "acfqp.v075_batch_planning_numerical_model.v2",
        "model_id",
    ),
    _spec(
        planning.V075NumericalPlanningProofV2,
        "NUMERICAL_PLANNING_PROOF",
        "acfqp.v075_batch_planning_numerical_proof.v2",
        "proof_id",
    ),
    _spec(
        planning.V075ConstructionPlanningInputV2,
        "CONSTRUCTION_PLANNING_INPUT",
        "acfqp.v075_batch_planning_construction_input.v2",
        "input_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildCausalEdgeV2,
        "DYNAMIC_CHILD_CAUSAL_EDGE",
        "acfqp.v075_live_dynamic_child_causal_edge.v2",
        "edge_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildStateV2,
        "DYNAMIC_CHILD_STATE",
        "acfqp.v075_live_dynamic_child_state.v2",
        "child_binding_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildDiscoveryIntentV2,
        "DYNAMIC_CHILD_DISCOVERY_INTENT",
        "acfqp.v075_live_dynamic_child_acquisition_intent.v2",
        "intent_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildValidationIntentTemplateV2,
        "DYNAMIC_CHILD_VALIDATION_TEMPLATE",
        (
            "acfqp.v075_live_dynamic_child_validation_intent_template.v2"
        ),
        "template_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildClosureV2,
        "DYNAMIC_CHILD_CLOSURE",
        "acfqp.v075_live_dynamic_child_closure.v2",
        "closure_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildClosureVerificationV2,
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        "acfqp.v075_live_dynamic_child_closure_verification.v2",
        "verification_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildExecutedRowV2,
        "DYNAMIC_CHILD_EXECUTED_ROW",
        "acfqp.v075_live_dynamic_child_executed_row.v2",
        "executed_row_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildExecutionLedgerV2,
        "DYNAMIC_CHILD_EXECUTION_LEDGER",
        "acfqp.v075_live_dynamic_child_execution_ledger.v2",
        "ledger_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildExecutionVerificationV2,
        "DYNAMIC_CHILD_EXECUTION_VERIFICATION",
        "acfqp.v075_live_dynamic_child_execution_verification.v2",
        "verification_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildReplanningBarrierV2,
        "DYNAMIC_CHILD_REPLANNING_BARRIER",
        "acfqp.v075_live_dynamic_child_replanning_barrier.v2",
        "barrier_id",
    ),
    _spec(
        dynamic.V075LiveDynamicChildReplanningBarrierVerificationV2,
        "DYNAMIC_CHILD_REPLANNING_BARRIER_VERIFICATION",
        (
            "acfqp.v075_live_dynamic_child_replanning_barrier_"
            "verification.v2"
        ),
        "verification_id",
    ),
    _spec(
        dynamic.V075LivePromotionIntentV2,
        "LIVE_PROMOTION_INTENT",
        "acfqp.v075_live_promotion_authorization.v2",
        "intent_id",
    ),
    _spec(
        dynamic.V075LivePromotionDecisionV2,
        "LIVE_PROMOTION_DECISION",
        "acfqp.v075_live_promotion_decision.v2",
        "decision_id",
    ),
    _spec(
        dynamic.V075LivePromotionDecisionVerificationV2,
        "LIVE_PROMOTION_DECISION_VERIFICATION",
        "acfqp.v075_live_promotion_decision_verification.v2",
        "verification_id",
    ),
    _spec(
        dynamic.V075LivePromotionReplanningBarrierV2,
        "LIVE_PROMOTION_REPLANNING_BARRIER",
        "acfqp.v075_live_promotion_replanning_barrier.v2",
        "barrier_id",
    ),
    _spec(
        dynamic.V075LivePromotionReplanningBarrierVerificationV2,
        "LIVE_PROMOTION_REPLANNING_BARRIER_VERIFICATION",
        (
            "acfqp.v075_live_promotion_replanning_barrier_"
            "verification.v2"
        ),
        "verification_id",
    ),
    _spec(
        lineage.V075BatchPublicVerificationV2,
        "BATCH_PUBLIC_VERIFICATION",
        "acfqp.v075_batch_public_verification.v2",
        "verification_id",
    ),
    _spec(
        lineage.V075BatchSequenceVerificationV2,
        "BATCH_SEQUENCE_VERIFICATION",
        "acfqp.v075_batch_sequence_verification.v2",
        "verification_id",
    ),
    _spec(
        lineage.V075BatchOccurrenceLineageV2,
        "CONSTRUCTION_LINEAGE",
        "acfqp.v075_batch_occurrence_lineage.v2",
        "lineage_id",
    ),
    _spec(
        lifecycle.V075BatchSupportEvidenceV2,
        "LIFECYCLE_SUPPORT_EVIDENCE",
        "acfqp.v075_batch_support_evidence.v2",
        "evidence_id",
    ),
    _spec(
        lifecycle.V075BatchSupportFreezeV2,
        "LIFECYCLE_SUPPORT_FREEZE",
        "acfqp.v075_batch_support_freeze.v2",
        "freeze_id",
    ),
    _spec(
        lifecycle.V075BatchLifecycleEventV2,
        "LIFECYCLE_EVENT",
        "acfqp.v075_batch_lifecycle_event.v2",
        "event_id",
    ),
    _spec(
        lifecycle.V075BatchOccurrenceLifecycleClosureV2,
        "CONSTRUCTION_LIFECYCLE",
        "acfqp.v075_batch_occurrence_lifecycle.v2",
        "closure_id",
    ),
    _spec(
        lifecycle.V075BatchOccurrenceLifecycleVerificationV2,
        "CONSTRUCTION_LIFECYCLE_VERIFICATION",
        "acfqp.v075_batch_occurrence_lifecycle_verification.v2",
        "verification_id",
    ),
    _spec(
        runner.V075ObserverSignedClosedReconciliationV2,
        "CLOSED_RECONCILIATION",
        "acfqp.v075_observer_signed_closed_reconciliation.v2",
        "reconciliation_id",
    ),
    _spec(
        runner.V075ObserverSignedMultiroundResultV2,
        "MULTIROUND_RESULT",
        "acfqp.v075_observer_signed_multiround_occurrence_result.v2",
        "result_id",
    ),
)

_DYNAMIC_CONTROL_ROLES = {
    (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .INITIAL_SCHEDULE_ROW_INTENT
    ): "ROOT",
    (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    ): "CHILD",
    (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .LIVE_PROMOTION_AUTHORIZATION
    ): "PROMOTION",
}

_DYNAMIC_CONTROL_SCHEMAS = {
    control.V075ControlledBatchSemanticAuthorityBindingV2: (
        "CONTROLLED_{kind}_SEMANTIC_AUTHORITY",
        "acfqp.v075_controlled_batch_semantic_authority_binding.v2",
        "binding_id",
    ),
    control.V075HeadBoundExactBatchIntentV2: (
        "CONTROLLED_{kind}_INTENT",
        "acfqp.v075_head_bound_exact_batch_intent.v2",
        "intent_id",
    ),
    control.V075ControlledBatchAppendV2: (
        "CONTROLLED_{kind}_APPEND",
        "acfqp.v075_controlled_batch_append.v2",
        None,
    ),
}

_TYPE_TO_SPEC = {item.concrete_type: item for item in _STATIC_SPECS}
if len(_TYPE_TO_SPEC) != len(_STATIC_SPECS):  # pragma: no cover
    raise RuntimeError("portable artifact types must be unique")

ROLE_SCHEMA_REGISTRY = MappingProxyType(
    {
        **{item.role: item.schema for item in _STATIC_SPECS},
        **{
            role_template.format(kind=kind): schema
            for role_template, schema, _identity in (
                _DYNAMIC_CONTROL_SCHEMAS.values()
            )
            for kind in _DYNAMIC_CONTROL_ROLES.values()
        },
    }
)


def _artifact_spec(value: Any) -> _ArtifactSpec | None:
    exact_type = type(value)
    fixed = _TYPE_TO_SPEC.get(exact_type)
    if fixed is not None:
        return fixed
    dynamic_spec = _DYNAMIC_CONTROL_SCHEMAS.get(exact_type)
    if dynamic_spec is None:
        return None
    semantic = (
        value
        if exact_type is control.V075ControlledBatchSemanticAuthorityBindingV2
        else value.intent.semantic_authority
        if exact_type is control.V075ControlledBatchAppendV2
        else value.semantic_authority
    )
    kind = _DYNAMIC_CONTROL_ROLES.get(semantic.role)
    if kind is None:
        _fail("controlled evidence has an unregistered semantic role")
    role_template, schema, identity_attribute = dynamic_spec
    return _ArtifactSpec(
        exact_type,
        role_template.format(kind=kind),
        schema,
        identity_attribute,
    )


def _artifact_raw(value: Any, spec: _ArtifactSpec) -> bytes:
    to_document = getattr(value, "to_document", None)
    if not callable(to_document):
        _fail(f"{spec.role} lacks one canonical document")
    raw = canonical_json_bytes(to_document())
    document = _strict_json_document(raw, label=spec.role)
    if document.get("schema") != spec.schema:
        _fail(f"{spec.role} carries a foreign artifact schema")
    return raw


def _derived_artifact_id(*, role: str, raw: bytes) -> str:
    return hashlib.sha256(
        DOMAIN_TAGS["derived_artifact"].encode("utf-8")
        + b":"
        + role.encode("utf-8")
        + b"\x00"
        + raw
    ).hexdigest()


def _artifact_identity(
    value: Any,
    *,
    spec: _ArtifactSpec,
    raw: bytes,
) -> str:
    if spec.identity_attribute is None:
        return _derived_artifact_id(role=spec.role, raw=raw)
    return _cid(
        getattr(value, spec.identity_attribute),
        f"{spec.role} semantic artifact",
    )


def _record_domain(role: str) -> str:
    return f"{DOMAIN_TAGS['record']}:{role.lower()}"


_RECORD_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableEvidenceArtifactRecordV2:
    """One role-bound canonical artifact and its earlier dependencies."""

    _issuer: InitVar[object]
    index: int
    role: str
    artifact_schema: str
    artifact_domain_tag: str
    semantic_artifact_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes_hex: str
    _record_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RECORD_ISSUER
            or type(self.index) is not int
            or self.index < 0
            or type(self.role) is not str
            or ROLE_SCHEMA_REGISTRY.get(self.role) != self.artifact_schema
            or self.artifact_domain_tag != _record_domain(self.role)
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
            or type(self.canonical_artifact_bytes_hex) is not str
        ):
            _fail("portable evidence record is malformed or role-transplanted")
        _cid(self.semantic_artifact_id, "portable semantic artifact")
        for dependency in self.dependency_record_ids:
            _cid(dependency, "portable artifact dependency")
        try:
            raw = bytes.fromhex(self.canonical_artifact_bytes_hex)
        except ValueError as error:
            raise V075PortableOccurrenceEvidenceV2InvariantViolation(
                "portable artifact bytes are not lowercase hexadecimal"
            ) from error
        if raw.hex() != self.canonical_artifact_bytes_hex:
            _fail("portable artifact bytes are not canonical lowercase hex")
        document = _strict_json_document(raw, label=self.role)
        if document.get("schema") != self.artifact_schema:
            _fail("portable artifact raw bytes carry a foreign schema")
        _assert_public_artifact_document(document)
        _verify_declared_artifact_document_shape(
            role=self.role,
            document=document,
        )
        expected_semantic_id = self.semantic_artifact_id
        own_id_key = _ROLE_PRIMARY_DOCUMENT_ID.get(self.role)
        if own_id_key is None:
            expected_semantic_id = _derived_artifact_id(
                role=self.role,
                raw=raw,
            )
        elif document.get(own_id_key) != self.semantic_artifact_id:
            _fail("portable artifact semantic ID differs from its raw bytes")
        if expected_semantic_id != self.semantic_artifact_id:
            _fail("portable derived artifact identity changed")
        _verify_semantic_artifact_content_ids(
            role=self.role,
            document=document,
        )
        object.__setattr__(
            self,
            "_record_id",
            _hash(self.artifact_domain_tag, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_evidence_artifact_record.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "index": self.index,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "artifact_domain_tag": self.artifact_domain_tag,
            "semantic_artifact_id": self.semantic_artifact_id,
            "dependency_record_ids": list(self.dependency_record_ids),
            "canonical_artifact_bytes_hex": (
                self.canonical_artifact_bytes_hex
            ),
            "raw_bytes_complete": True,
            "private_material_serialized": False,
            "official_execution_allowed": False,
        }

    @property
    def record_id(self) -> str:
        return self._record_id

    @property
    def canonical_artifact_bytes(self) -> bytes:
        return bytes.fromhex(self.canonical_artifact_bytes_hex)

    @property
    def artifact_document(self) -> dict[str, Any]:
        return _strict_json_document(
            self.canonical_artifact_bytes,
            label=self.role,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "record_id": self.record_id}


_ROLE_PRIMARY_DOCUMENT_ID = MappingProxyType(
    {
        item.role: (
            None
            if item.identity_attribute is None
            else {
                "occurrence_id": "occurrence_id",
                "intent_id": "intent_id",
                "schedule_id": "schedule_id",
                "verification_id": "verification_id",
                "state_id": "state_id",
                "catalogue_id": "catalogue_id",
                "row_binding_id": "row_binding_id",
                "evidence_id": "evidence_id",
                "epoch_id": "epoch_id",
                "chain_id": "chain_id",
                "pairing_authority_id": "pairing_authority_id",
                "stream_id": "stream_id",
                "binding_id": "binding_id",
                "request_id": "request_id",
                "outcome_id": "outcome_id",
                "batch_id": "batch_id",
                "entry_id": "entry_id",
                "closure_id": "closure_id",
                "head_id": "head_id",
                "receipt_id": "receipt_id",
                "freeze_id": "freeze_id",
                "control_closure_id": "control_closure_id",
                "reconciliation_id": "reconciliation_id",
                "execution_id": "execution_id",
                "model_epoch_id": "model_epoch_id",
                "model_id": "model_id",
                "proof_id": "proof_id",
                "input_id": "input_id",
                "result_id": "result_id",
                "edge_id": "edge_id",
                "child_binding_id": "child_binding_id",
                "template_id": "template_id",
                "executed_row_id": "executed_row_id",
                "ledger_id": "ledger_id",
                "barrier_id": "barrier_id",
                "decision_id": "decision_id",
                "lineage_id": "lineage_id",
                "event_id": "event_id",
            }[item.identity_attribute]
        )
        for item in _STATIC_SPECS
    }
    | {
        role_template.format(kind=kind): (
            None
            if identity is None
            else {
                "binding_id": "binding_id",
                "intent_id": "intent_id",
            }[identity]
        )
        for role_template, _schema, identity in (
            _DYNAMIC_CONTROL_SCHEMAS.values()
        )
        for kind in _DYNAMIC_CONTROL_ROLES.values()
    }
)


_ROLE_DOCUMENT_KEYSET_SHA256 = MappingProxyType(
    {
        "BATCH_PUBLIC_VERIFICATION": (
            "0a5826971732384c247355608fd15cfc4bec9afc1518a9b77e1df91ab301cc4d"
        ),
        "BATCH_SEQUENCE_VERIFICATION": (
            "ee3028311ab34e5c6e483106adb6c285aff5b0b330fbaf198a789c7a2a52a76b"
        ),
        "CLOSED_RECONCILIATION": (
            "3ef39d75dade16da64151fac08e595dfa54eebaafd0992779cddf5a442812914"
        ),
        "CONSTRUCTION_LIFECYCLE": (
            "6238104a7a22f22b26fd7b65badf0d40b5a23090acdd87fec1938b1790226710"
        ),
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
            "9b2e43c943973f5f999bb0e9d68f97f54f6491d04a485b13f62836ddde20b05f"
        ),
        "CONSTRUCTION_LINEAGE": (
            "f846f508c4e61678e873d8ce6de326cc7079b27cdc472ce9032f3864cc8d2b2c"
        ),
        "CONSTRUCTION_PLANNING_INPUT": (
            "2368014978ef73122250c1680dc33379280e0b2647b17955bd9f0234d9908006"
        ),
        "CONTROLLED_CHILD_APPEND": (
            "bee467214b56feb9a8f2bf7abcb3be69d627c420abf676e7afe20784e2fb5fed"
        ),
        "CONTROLLED_CHILD_INTENT": (
            "59f6929124cd2d281ccdebd691d18290559e18a33f73078f8cc18d0dabe1bf48"
        ),
        "CONTROLLED_CHILD_SEMANTIC_AUTHORITY": (
            "ca2afab5e59f39da1d0e6c6b6bf1cfd76e09d0107fc5ff55a712a0661d1db11b"
        ),
        "CONTROLLED_COMPLETE_SUPPORT_FREEZE": (
            "b0854575e4891aec158f61f68d4b60d379ee875996d46eaa8ea303e838e26ca2"
        ),
        "CONTROLLED_JOURNAL_CLOSURE": (
            "24b098e3afc6ffc24e33f386a5fdabc5a830e75191ca9e877dbb9d15cee0adc5"
        ),
        "CONTROLLED_PROMOTION_APPEND": (
            "bee467214b56feb9a8f2bf7abcb3be69d627c420abf676e7afe20784e2fb5fed"
        ),
        "CONTROLLED_PROMOTION_INTENT": (
            "59f6929124cd2d281ccdebd691d18290559e18a33f73078f8cc18d0dabe1bf48"
        ),
        "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY": (
            "ca2afab5e59f39da1d0e6c6b6bf1cfd76e09d0107fc5ff55a712a0661d1db11b"
        ),
        "CONTROLLED_ROOT_APPEND": (
            "bee467214b56feb9a8f2bf7abcb3be69d627c420abf676e7afe20784e2fb5fed"
        ),
        "CONTROLLED_ROOT_INTENT": (
            "59f6929124cd2d281ccdebd691d18290559e18a33f73078f8cc18d0dabe1bf48"
        ),
        "CONTROLLED_ROOT_SEMANTIC_AUTHORITY": (
            "ca2afab5e59f39da1d0e6c6b6bf1cfd76e09d0107fc5ff55a712a0661d1db11b"
        ),
        "DYNAMIC_CHILD_CAUSAL_EDGE": (
            "72022868a2e93cef8752c37331f0cffd20e5d9343515f4193e0853422945fc8e"
        ),
        "DYNAMIC_CHILD_CLOSURE": (
            "f88b173f0d278cc7bedce1e2dfcf22a7f5c9bf76bb89c158621e7692873cbe74"
        ),
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION": (
            "e36453b946f5bf7e12e743f35597a4de353ced096f948436350a043bcee93206"
        ),
        "DYNAMIC_CHILD_DISCOVERY_INTENT": (
            "130d1ff882eb5bc6bd02d11cb2297f7d5d51821049291b177e9af47a8995b781"
        ),
        "DYNAMIC_CHILD_EXECUTED_ROW": (
            "24edad4174e5cf0721c8c248a974ed942582ddee54925ce4d0ed435b30e6b339"
        ),
        "DYNAMIC_CHILD_EXECUTION_LEDGER": (
            "e1b369775ac6f07037e92c309547c5646a7eed51de339e4ced7366ac78a85378"
        ),
        "DYNAMIC_CHILD_EXECUTION_VERIFICATION": (
            "18f6449f9d66c8af41e2ddfe19068397e568a1c1d51a5f1d74e04c5597853cac"
        ),
        "DYNAMIC_CHILD_REPLANNING_BARRIER": (
            "c0ba8f4e207404b491a41761b8257d9908a170bd6f78bacbe8b38d7a123824a7"
        ),
        "DYNAMIC_CHILD_REPLANNING_BARRIER_VERIFICATION": (
            "ef34a95159ed460f4219cb9e9a9b5e07560b89ec017a383d10d4fa0eea46e750"
        ),
        "DYNAMIC_CHILD_STATE": (
            "5191afe6d77833a76b25ea24559a18fdd124f817f6d1bb149f00901ebf3bc6d3"
        ),
        "DYNAMIC_CHILD_VALIDATION_TEMPLATE": (
            "362493446c8d6aa58e4e78d2ecb80962745c38a6e3f706fc0a05470158995776"
        ),
        "INITIAL_ACQUISITION_SCHEDULE": (
            "3acadf984d8643be09d03f0963555888edb398fc1a424bb618eb8a7cb448c9f8"
        ),
        "INITIAL_ACQUISITION_VERIFICATION": (
            "bc38b03b410ccb74c72aef0f0bb1bba0de670acc018054fc9f964f761a408eab"
        ),
        "INITIAL_ROW_INTENT": (
            "12b81c697ef7e5f3558bd1cc01ad1798498d97ab693ae0830e9c9b0a8ce5317e"
        ),
        "LEGAL_ACTION_CATALOGUE": (
            "142ebf97d626e456f7d5ad10d225b3066ea6ccaad13308846f7a849b7a997586"
        ),
        "LIFECYCLE_EVENT": (
            "0c32870baa0ea35e14a5c264b918214873ed8f4791f9a30385526df78a56800e"
        ),
        "LIFECYCLE_SUPPORT_EVIDENCE": (
            "979ed93808266670561c0a0bf14a3885c88d916ba8fe22540d4a4bcdd010b0a0"
        ),
        "LIFECYCLE_SUPPORT_FREEZE": (
            "64193324c9ebe7182ce84d09ae65ee541e389ca783e1a03f53ad66cd3cb0a5c1"
        ),
        "LIVE_MODEL_EPOCH": (
            "c90de81d540737f1970933dfdc8c1343c7e8173326ba385943c54be186ed9fcb"
        ),
        "LIVE_PROMOTION_DECISION": (
            "d94a7808c2ff70336a199f20fa4fcd722cb3969de785298135f3548b3844fd66"
        ),
        "LIVE_PROMOTION_DECISION_VERIFICATION": (
            "acebe246876ba5a4cba950181af0820816aaaa96964483ba3bf43d055c41e42d"
        ),
        "LIVE_PROMOTION_INTENT": (
            "65c696da7f141d685606ffbda2f0dc83e87bf6840a33d55699d09067d2a0d1f5"
        ),
        "LIVE_PROMOTION_REPLANNING_BARRIER": (
            "77e214c297c4425f847ef117b563679d810b68cf1838ebba01011946f8ad3edf"
        ),
        "LIVE_PROMOTION_REPLANNING_BARRIER_VERIFICATION": (
            "bce30b827ffab841e14bfdc6f6d22e6f44b38979627a474adac599dbf135bd29"
        ),
        "LIVE_ROW_SOURCE_BINDING": (
            "f9d8a13b5a09f8f17edc66f16dfaf3b1ac46b75236e497f96771b5669c99034e"
        ),
        "MULTIROUND_RESULT": (
            "683335e0a1d9f43929977f1414c8ded0498be206bf22d68aaf72ccc215d59a4a"
        ),
        "NUMERICAL_MODEL": (
            "226bbde8194d0ed8a04566f6045f543f238a650265ffc621dab351ad0ce97dcc"
        ),
        "NUMERICAL_PLANNING_PROOF": (
            "ebdb2100a89a798bd1487a0fd89f29d0d4b8f4a893b7c562d3da353998630883"
        ),
        "OBSERVATION_ROW_BINDING": (
            "93cf8898f8b771603a92f19e2bf82c8cf511b97378076c7b36f11287662b94ac"
        ),
        "OBSERVER_OPEN_BINDING": (
            "3e826ca19f92c25fb174f8192a8184d7ba785176a3a2e1954f7f4592aedacacc"
        ),
        "OBSERVER_SIGNED_SUPPORT_EVIDENCE": (
            "3618c51e42eed7b3275a64638b61949bbcd71749372c03e422592779e9c8e8be"
        ),
        "OCCURRENCE_IDENTITY": (
            "b479e54ee0fa1c6fbb4a201667e44dc11651debd8317b372cc8d4226cc9e45d9"
        ),
        "OPEN_CONTROLLED_PREFIX_VERIFICATION": (
            "924c7111089d908fa9be43e14b319bda97fdf9075ecd553a55ca8942158ff1f1"
        ),
        "PAIRING_AUTHORITY": (
            "6af86000963c6a3c9a972d330d0705eb6a88aca23bf7c542c741e0fda72b104d"
        ),
        "ROOT_EXECUTION": (
            "27a139af71444adf1cf041009058576966f98b60acb8aab9dd4e2813c9c08ddb"
        ),
        "SHARED_SUPPORT_CHAIN": (
            "2640693b5fe8581cf20ad4ba03ceedcbc8663510523914e250ecf508c1217880"
        ),
        "SHARED_SUPPORT_EPOCH": (
            "63d5a098c299b9c8f56d480c23af5faebd8cb00cd3fd2752c725a3fed677952e"
        ),
        "SIGNED_APPEND_RECEIPT": (
            "ed3f44d0db87f7377e2b997b0d90bfd2efab91f23232c9b7043df24097eadd49"
        ),
        "SIGNED_BATCH_JOURNAL_CLOSURE": (
            "8691cc9c92bb15051182794a2c361a4c5239937e969860574ea1f3365b8ff7ca"
        ),
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (
            "fcab01511420f0c9c7f65877693983864670bd1d109086c940abb32ea282f523"
        ),
        "SIGNED_BATCH_JOURNAL_ENTRY": (
            "f5bc843572903d6f6db2feb44faeb84a8d48334a0f5cdeaacf178c289e06caec"
        ),
        "SIGNED_BATCH_OUTCOME": (
            "a332e47b6bbfc96964f330451bddf9e731858f8e5729ce4a9e4686fe93601d09"
        ),
        "SIGNED_BATCH_REQUEST": (
            "8438d9aec51db1865c0f5c9d6ec47150c21c3dcbda652e75824419cb75ff55e0"
        ),
        "SIGNED_CONTROL_CLOSURE": (
            "bf5ebae9a8f5c220d05be899170f156e84c2454a66f60ca2a164349a2edb0e37"
        ),
        "SIGNED_CONTROL_JOURNAL_HEAD": (
            "b67ee987cbad8d10b07ba40b75ae478928a5b180bbbe2244d409dd88e5000d8e"
        ),
        "SIGNED_CONTROL_RECONCILIATION": (
            "a629e7c42c77f76bb221a1ed2bd89ebd5f0f8512b41f11f9ba9fd6367926628b"
        ),
        "SIGNED_OBSERVATION_BATCH": (
            "f7409cd713f7ef8fb495341b393fc0c47bb46680cc090e53816bdb21324689c5"
        ),
        "SYMBOLIC_GRAPH_STATE": (
            "f60b3b5cf9dfc4163b311820c933ad54c0c23501f8d30aa71aef6e05bf76e571"
        ),
        "TRANSITION_STREAM": (
            "7a0117ffda200b78170e8ca44c348d143f7395d35c0be404a34d313f4daaadd8"
        ),
    }
)


def _document_keyset_sha256(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json_bytes(sorted(document))
    ).hexdigest()


_SCHEMA_DOCUMENT_KEYSET_SHA256: dict[str, frozenset[str]] = {}
for _shape_role, _shape_schema in ROLE_SCHEMA_REGISTRY.items():
    _SCHEMA_DOCUMENT_KEYSET_SHA256[_shape_schema] = (
        _SCHEMA_DOCUMENT_KEYSET_SHA256.get(
            _shape_schema,
            frozenset(),
        )
        | frozenset({_ROLE_DOCUMENT_KEYSET_SHA256[_shape_role]})
    )
_SCHEMA_DOCUMENT_KEYSET_SHA256 = dict(
    _SCHEMA_DOCUMENT_KEYSET_SHA256
)


def _verify_declared_artifact_document_shape(
    *,
    role: str,
    document: Mapping[str, Any],
) -> None:
    expected = _ROLE_DOCUMENT_KEYSET_SHA256.get(role)
    if (
        expected is None
        or _document_keyset_sha256(document) != expected
    ):
        _fail(
            "portable artifact contains missing or undeclared raw fields"
        )

    def verify_nested(value: Any, *, outermost: bool = False) -> None:
        if type(value) is list:
            for item in value:
                verify_nested(item)
            return
        if type(value) is not dict:
            return
        if not outermost:
            schema = value.get("schema")
            allowed = _SCHEMA_DOCUMENT_KEYSET_SHA256.get(schema)
            if (
                allowed is not None
                and _document_keyset_sha256(value) not in allowed
            ):
                _fail(
                    "embedded portable artifact contains missing or "
                    "undeclared raw fields"
                )
        for item in value.values():
            verify_nested(item)

    verify_nested(document, outermost=True)


@dataclass(frozen=True, slots=True)
class _SemanticHashRule:
    hasher: Callable[[str, Mapping[str, Any]], str]
    domain: str
    id_key: str
    excluded_keys: frozenset[str] = frozenset()
    included_keys: tuple[str, ...] = ()

    def expected_id(self, document: Mapping[str, Any]) -> str:
        if self.included_keys:
            try:
                payload = {
                    key: document[key] for key in self.included_keys
                }
            except KeyError:
                _fail("semantic artifact content-ID payload is incomplete")
        else:
            payload = {
                key: value
                for key, value in document.items()
                if key != self.id_key and key not in self.excluded_keys
            }
        try:
            return _cid(
                self.hasher(self.domain, payload),
                "recomputed semantic artifact content ID",
            )
        except (KeyError, TypeError, ValueError) as error:
            raise V075PortableOccurrenceEvidenceV2InvariantViolation(
                "semantic artifact content-ID replay failed"
            ) from error


def _rule(
    hasher: Callable[[str, Mapping[str, Any]], str],
    domain: str,
    id_key: str,
    *excluded_keys: str,
    included_keys: tuple[str, ...] = (),
) -> _SemanticHashRule:
    return _SemanticHashRule(
        hasher,
        domain,
        id_key,
        frozenset(excluded_keys),
        included_keys,
    )


_SEMANTIC_HASH_RULES_MUTABLE = {
    "OCCURRENCE_IDENTITY": _rule(
        backend._hash,  # noqa: SLF001
        "occurrence",
        "occurrence_id",
        "batch_count_at_freeze",
        "frozen_before_observation",
        "kernel_calls",
        "observer_calls",
        "private_material_serialized",
        "target_accessed",
    ),
    "INITIAL_ROW_INTENT": _rule(
        acquisition._hash,  # noqa: SLF001
        "initial_intent",
        "intent_id",
        "row_binding",
    ),
    "INITIAL_ACQUISITION_SCHEDULE": _rule(
        acquisition._hash,  # noqa: SLF001
        "initial_schedule",
        "schedule_id",
        "intents",
        "occurrence",
        "profile",
        "proposal_view",
    ),
    "INITIAL_ACQUISITION_VERIFICATION": _rule(
        acquisition._hash,  # noqa: SLF001
        "verification",
        "verification_id",
    ),
    "SYMBOLIC_GRAPH_STATE": _rule(
        graph._hash, "state", "state_id", "context"  # noqa: SLF001
    ),
    "LEGAL_ACTION_CATALOGUE": _rule(
        graph._hash,  # noqa: SLF001
        "catalogue",
        "catalogue_id",
        "context",
        "state",
    ),
    "OBSERVATION_ROW_BINDING": _rule(
        graph._hash,  # noqa: SLF001
        "row",
        "row_binding_id",
        "catalogue",
        "context",
    ),
    "OBSERVER_SIGNED_SUPPORT_EVIDENCE": _rule(
        graph._hash,  # noqa: SLF001
        "batch_aggregate_support_evidence",
        "evidence_id",
        "namespace",
        "observed_state",
        "row_binding",
    ),
    "SHARED_SUPPORT_EPOCH": _rule(
        graph._hash,  # noqa: SLF001
        "support_epoch",
        "epoch_id",
        "evidence",
        "namespace",
        "row_binding",
    ),
    "SHARED_SUPPORT_CHAIN": _rule(
        graph._hash,  # noqa: SLF001
        "support_chain",
        "chain_id",
        "epochs",
        "namespace",
        "row_binding",
    ),
    "PAIRING_AUTHORITY": _rule(
        graph._hash,  # noqa: SLF001
        "five_arm_pairing",
        "pairing_authority_id",
        "namespace",
        "row_binding",
        "support_chain",
    ),
    "TRANSITION_STREAM": _rule(
        graph._hash,  # noqa: SLF001
        "stream",
        "stream_id",
        included_keys=("pair_id", "arm", "lane"),
    ),
    "OBSERVER_OPEN_BINDING": _rule(
        observer._hash, "open_binding", "binding_id"  # noqa: SLF001
    ),
    "SIGNED_BATCH_REQUEST": _rule(
        observer._hash, "batch_request", "request_id"  # noqa: SLF001
    ),
    "SIGNED_BATCH_OUTCOME": _rule(
        observer._hash,  # noqa: SLF001
        "batch_outcome",
        "outcome_id",
        included_keys=(
            "schema",
            "schema_version",
            "next_ranks",
            "failure",
            "terminal",
            "spawn_cell",
            "spawn_rank",
            "realized_row_reward",
        ),
    ),
    "SIGNED_OBSERVATION_BATCH": _rule(
        observer._hash,  # noqa: SLF001
        "batch_artifact",
        "batch_id",
        "observer_open_binding",
        "outcomes",
        "request",
    ),
    "SIGNED_BATCH_JOURNAL_ENTRY": _rule(
        observer._hash,  # noqa: SLF001
        "batch_journal_entry",
        "entry_id",
        "batch",
    ),
    "SIGNED_BATCH_JOURNAL_CLOSURE": _rule(
        observer._hash,  # noqa: SLF001
        "batch_journal_closure_artifact",
        "closure_id",
        "entries",
        "observer_open_binding",
    ),
    "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": _rule(
        observer._hash,  # noqa: SLF001
        "batch_closure_verification",
        "verification_id",
    ),
    "SIGNED_CONTROL_JOURNAL_HEAD": _rule(
        control._hash,  # noqa: SLF001
        "journal_head",
        "head_id",
        "observer_open_binding",
    ),
    "SIGNED_APPEND_RECEIPT": _rule(
        control._hash,  # noqa: SLF001
        "append_receipt",
        "receipt_id",
        "observer_open_binding",
    ),
    "CONTROLLED_COMPLETE_SUPPORT_FREEZE": _rule(
        control._hash,  # noqa: SLF001
        "support_freeze",
        "freeze_id",
        "evidence",
    ),
    "OPEN_CONTROLLED_PREFIX_VERIFICATION": _rule(
        control._hash,  # noqa: SLF001
        "open_prefix_verification",
        "verification_id",
    ),
    "SIGNED_CONTROL_CLOSURE": _rule(
        control._hash,  # noqa: SLF001
        "control_closure",
        "control_closure_id",
        "observer_open_binding",
    ),
    "SIGNED_CONTROL_RECONCILIATION": _rule(
        control._hash,  # noqa: SLF001
        "reconciliation",
        "reconciliation_id",
    ),
    "ROOT_EXECUTION": _rule(
        runner._hash, "root_execution", "execution_id"  # noqa: SLF001
    ),
    "LIVE_ROW_SOURCE_BINDING": _rule(
        live_model._hash,  # noqa: SLF001
        "row_source_binding",
        "binding_id",
    ),
    "LIVE_MODEL_EPOCH": _rule(
        live_model._hash,  # noqa: SLF001
        "model_epoch",
        "model_epoch_id",
        "model",
        "proof",
        "row_sources",
    ),
    "NUMERICAL_MODEL": _rule(
        planning._hash, "model", "model_id", "rows"  # noqa: SLF001
    ),
    "NUMERICAL_PLANNING_PROOF": _rule(
        planning._hash,  # noqa: SLF001
        "proof",
        "proof_id",
        "envelope",
        "failed_frontier",
        "model",
        "policy",
        "quotient",
    ),
    "CONSTRUCTION_PLANNING_INPUT": _rule(
        planning._hash,  # noqa: SLF001
        "input",
        "input_id",
        "evidence_bindings",
        "model",
    ),
    "DYNAMIC_CHILD_CAUSAL_EDGE": _rule(
        dynamic._hash, "child_edge", "edge_id"  # noqa: SLF001
    ),
    "DYNAMIC_CHILD_STATE": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_state",
        "child_binding_id",
        "catalogue",
        "causal_edges",
        "row_bindings",
        "state",
    ),
    "DYNAMIC_CHILD_DISCOVERY_INTENT": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_discovery_intent",
        "intent_id",
        "row_binding",
        "stream_identity",
    ),
    "DYNAMIC_CHILD_VALIDATION_TEMPLATE": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_validation_template",
        "template_id",
    ),
    "DYNAMIC_CHILD_CLOSURE": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_closure",
        "closure_id",
        "child_states",
        "discovery_intents",
        "validation_templates",
    ),
    "DYNAMIC_CHILD_CLOSURE_VERIFICATION": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_verification",
        "verification_id",
    ),
    "DYNAMIC_CHILD_EXECUTED_ROW": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_executed_row",
        "executed_row_id",
    ),
    "DYNAMIC_CHILD_EXECUTION_LEDGER": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_execution_ledger",
        "ledger_id",
        "executed_rows",
    ),
    "DYNAMIC_CHILD_EXECUTION_VERIFICATION": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_execution_verification",
        "verification_id",
    ),
    "DYNAMIC_CHILD_REPLANNING_BARRIER": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_replanning_barrier",
        "barrier_id",
    ),
    "DYNAMIC_CHILD_REPLANNING_BARRIER_VERIFICATION": _rule(
        dynamic._hash,  # noqa: SLF001
        "child_replanning_verification",
        "verification_id",
    ),
    "LIVE_PROMOTION_INTENT": _rule(
        dynamic._hash,  # noqa: SLF001
        "promotion_intent",
        "intent_id",
        "stream_identity",
    ),
    "LIVE_PROMOTION_DECISION": _rule(
        dynamic._hash,  # noqa: SLF001
        "promotion_decision",
        "decision_id",
        "intent",
    ),
    "LIVE_PROMOTION_DECISION_VERIFICATION": _rule(
        dynamic._hash,  # noqa: SLF001
        "promotion_verification",
        "verification_id",
    ),
    "LIVE_PROMOTION_REPLANNING_BARRIER": _rule(
        dynamic._hash,  # noqa: SLF001
        "promotion_replanning_barrier",
        "barrier_id",
    ),
    "LIVE_PROMOTION_REPLANNING_BARRIER_VERIFICATION": _rule(
        dynamic._hash,  # noqa: SLF001
        "promotion_replanning_verification",
        "verification_id",
    ),
    "BATCH_PUBLIC_VERIFICATION": _rule(
        lineage._hash,  # noqa: SLF001
        "batch_public_verification",
        "verification_id",
    ),
    "BATCH_SEQUENCE_VERIFICATION": _rule(
        lineage._hash,  # noqa: SLF001
        "batch_sequence_verification",
        "verification_id",
    ),
    "CONSTRUCTION_LINEAGE": _rule(
        lineage._hash, "occurrence_lineage", "lineage_id"  # noqa: SLF001
    ),
    "LIFECYCLE_SUPPORT_EVIDENCE": _rule(
        lifecycle._hash, "support_evidence", "evidence_id"  # noqa: SLF001
    ),
    "LIFECYCLE_SUPPORT_FREEZE": _rule(
        lifecycle._hash, "support_freeze", "freeze_id"  # noqa: SLF001
    ),
    "LIFECYCLE_EVENT": _rule(
        lifecycle._hash, "event", "event_id"  # noqa: SLF001
    ),
    "CONSTRUCTION_LIFECYCLE": _rule(
        lifecycle._hash,  # noqa: SLF001
        "construction_lifecycle",
        "closure_id",
        "events",
        "support_evidence",
        "support_freezes",
    ),
    "CONSTRUCTION_LIFECYCLE_VERIFICATION": _rule(
        lifecycle._hash,  # noqa: SLF001
        "construction_lifecycle_verification",
        "verification_id",
    ),
    "CLOSED_RECONCILIATION": _rule(
        runner._hash,  # noqa: SLF001
        "closed_reconciliation",
        "reconciliation_id",
    ),
    "MULTIROUND_RESULT": _rule(
        runner._hash, "result", "result_id"  # noqa: SLF001
    ),
}

for _kind in ("ROOT", "CHILD", "PROMOTION"):
    _SEMANTIC_HASH_RULES_MUTABLE[
        f"CONTROLLED_{_kind}_SEMANTIC_AUTHORITY"
    ] = _rule(
        control._hash,  # noqa: SLF001
        "semantic_authority",
        "binding_id",
    )
    _SEMANTIC_HASH_RULES_MUTABLE[
        f"CONTROLLED_{_kind}_INTENT"
    ] = _rule(
        control._hash,  # noqa: SLF001
        "batch_intent",
        "intent_id",
        "semantic_authority",
        "stream_identity",
    )

_SEMANTIC_HASH_RULES = MappingProxyType(
    dict(_SEMANTIC_HASH_RULES_MUTABLE)
)
del _SEMANTIC_HASH_RULES_MUTABLE

_ROLES_WITH_DOCUMENT_CONTENT_IDS = {
    role
    for role, key in _ROLE_PRIMARY_DOCUMENT_ID.items()
    if key is not None
} | {"SIGNED_BATCH_OUTCOME"}
if set(_SEMANTIC_HASH_RULES) != _ROLES_WITH_DOCUMENT_CONTENT_IDS:
    raise RuntimeError(
        "portable semantic content-ID registry is incomplete or overbroad"
    )
if set(_ROLE_DOCUMENT_KEYSET_SHA256) != set(ROLE_SCHEMA_REGISTRY):
    raise RuntimeError("portable role-document shape registry is incomplete")


def _verify_semantic_artifact_content_ids(
    *,
    role: str,
    document: Mapping[str, Any],
) -> None:
    rule = _SEMANTIC_HASH_RULES.get(role)
    if rule is None:
        return
    actual = _cid(
        document.get(rule.id_key),
        f"{role} raw semantic content ID",
    )
    if role == "TRANSITION_STREAM":
        payload = {
            "schema": "acfqp.v075_arm_isolated_transition_stream.v2",
            "schema_version": document["schema_version"],
            "pair_id": document["pair_id"],
            "arm": document["arm"],
            "lane": document["lane"],
        }
        expected = graph._hash("stream", payload)  # noqa: SLF001
    else:
        expected = rule.expected_id(document)
    if actual != expected:
        _fail(
            f"{role} cached content ID differs from semantic recomputation"
        )


@dataclass(frozen=True, slots=True)
class _Candidate:
    key: tuple[str, str]
    spec: _ArtifactSpec
    value: Any
    raw: bytes


def _walk_artifact_candidates(
    roots: Mapping[str, Any],
) -> tuple[
    dict[tuple[str, str], _Candidate],
    dict[str, tuple[tuple[str, str], ...]],
]:
    candidates: dict[tuple[str, str], _Candidate] = {}
    active: set[int] = set()
    completed: dict[int, frozenset[tuple[str, str]]] = {}

    def visit(value: Any) -> frozenset[tuple[str, str]]:
        if value is None or type(value) in {bool, int, str, bytes}:
            return frozenset()
        if isinstance(value, Enum):
            return frozenset()
        value_id = id(value)
        if value_id in completed:
            return completed[value_id]
        if value_id in active:
            _fail("typed evidence roots contain one object-reference cycle")
        if type(value) in {tuple, list}:
            active.add(value_id)
            nested = frozenset().union(*(visit(item) for item in value))
            active.remove(value_id)
            completed[value_id] = nested
            return nested
        if isinstance(value, Mapping):
            active.add(value_id)
            nested = frozenset().union(
                *(visit(item) for item in value.values())
            )
            active.remove(value_id)
            completed[value_id] = nested
            return nested
        if not is_dataclass(value) or isinstance(value, type):
            return frozenset()
        active.add(value_id)
        nested = frozenset().union(
            *(
                visit(getattr(value, item.name))
                for item in fields(value)
                if not item.name.startswith("_")
            )
        )
        spec = _artifact_spec(value)
        if spec is None:
            result = nested
        else:
            raw = _artifact_raw(value, spec)
            semantic_id = _artifact_identity(value, spec=spec, raw=raw)
            key = (spec.role, semantic_id)
            candidate = _Candidate(key, spec, value, raw)
            prior = candidates.get(key)
            if prior is not None and prior.raw != raw:
                _fail(
                    "one role/semantic ID maps to unequal canonical bytes: "
                    f"{spec.role}/{semantic_id}"
                )
            candidates[key] = candidate
            result = frozenset({key})
        active.remove(value_id)
        completed[value_id] = result
        return result

    root_keys = {
        name: tuple(sorted(visit(roots[name])))
        for name in REQUIRED_ROOT_NAMES
    }
    return candidates, root_keys


def _content_ids(value: Any) -> frozenset[str]:
    result: set[str] = set()
    if type(value) is str:
        try:
            result.add(parse_content_id(value))
        except ValueError:
            pass
    elif type(value) is list:
        for item in value:
            result.update(_content_ids(item))
    elif type(value) is dict:
        for item in value.values():
            result.update(_content_ids(item))
    return frozenset(result)


@dataclass(frozen=True, slots=True)
class _DependencyNode:
    key: Any
    role: str
    semantic_artifact_id: str
    raw: bytes


def _nested_documents(value: Any) -> Iterable[dict[str, Any]]:
    if type(value) is list:
        for item in value:
            yield from _nested_documents(item)
        return
    if type(value) is not dict:
        return
    yield value
    for item in value.values():
        yield from _nested_documents(item)


def _derive_dependency_graph(
    nodes: tuple[_DependencyNode, ...],
) -> dict[Any, frozenset[Any]]:
    """Derive every edge from canonical documents, never claimed topology."""

    keys_by_semantic_id: dict[str, set[Any]] = {}
    keys_by_raw: dict[bytes, set[Any]] = {}
    append_keys_by_receipt_id: dict[str, set[Any]] = {}
    documents: dict[Any, dict[str, Any]] = {}
    for node in nodes:
        keys_by_semantic_id.setdefault(
            node.semantic_artifact_id,
            set(),
        ).add(node.key)
        keys_by_raw.setdefault(node.raw, set()).add(node.key)
        document = _strict_json_document(node.raw, label=node.role)
        documents[node.key] = document
        if node.role in {
            "CONTROLLED_ROOT_APPEND",
            "CONTROLLED_CHILD_APPEND",
            "CONTROLLED_PROMOTION_APPEND",
        }:
            receipt_id = _cid(
                document.get("append_receipt_id"),
                "controlled append receipt",
            )
            append_keys_by_receipt_id.setdefault(
                receipt_id,
                set(),
            ).add(node.key)
    dependencies: dict[Any, frozenset[Any]] = {}
    append_reference_excluded_roles = {
        "SIGNED_APPEND_RECEIPT",
        "CONTROLLED_ROOT_APPEND",
        "CONTROLLED_CHILD_APPEND",
        "CONTROLLED_PROMOTION_APPEND",
    }
    for node in nodes:
        document = documents[node.key]
        referenced: set[Any] = set()
        content_ids = _content_ids(document)
        for semantic_id in content_ids:
            referenced.update(keys_by_semantic_id.get(semantic_id, ()))
        for nested in _nested_documents(document):
            nested_raw = canonical_json_bytes(nested)
            referenced.update(keys_by_raw.get(nested_raw, ()))
        if node.role not in append_reference_excluded_roles:
            for semantic_id in content_ids:
                referenced.update(
                    append_keys_by_receipt_id.get(semantic_id, ())
                )
        referenced.discard(node.key)
        dependencies[node.key] = frozenset(referenced)
    return dependencies


def _candidate_dependencies(
    candidates: Mapping[tuple[str, str], _Candidate],
) -> dict[tuple[str, str], frozenset[tuple[str, str]]]:
    return _derive_dependency_graph(
        tuple(
            _DependencyNode(
                key,
                candidate.spec.role,
                key[1],
                candidate.raw,
            )
            for key, candidate in candidates.items()
        )
    )


def _topological_keys(
    candidates: Mapping[tuple[str, str], _Candidate],
    dependencies: Mapping[
        tuple[str, str],
        frozenset[tuple[str, str]],
    ],
) -> tuple[tuple[str, str], ...]:
    remaining = set(candidates)
    ordered: list[tuple[str, str]] = []
    emitted: set[tuple[str, str]] = set()
    while remaining:
        ready = sorted(
            key for key in remaining if dependencies[key] <= emitted
        )
        if not ready:
            _fail("typed evidence dependency graph is cyclic")
        ordered.extend(ready)
        emitted.update(ready)
        remaining.difference_update(ready)
    return tuple(ordered)


def _freeze_records(
    candidates: Mapping[tuple[str, str], _Candidate],
    dependencies: Mapping[
        tuple[str, str],
        frozenset[tuple[str, str]],
    ],
    ordered_keys: tuple[tuple[str, str], ...],
) -> tuple[
    tuple[V075PortableEvidenceArtifactRecordV2, ...],
    dict[tuple[str, str], str],
]:
    key_to_record_id: dict[tuple[str, str], str] = {}
    records: list[V075PortableEvidenceArtifactRecordV2] = []
    for index, key in enumerate(ordered_keys):
        candidate = candidates[key]
        record = V075PortableEvidenceArtifactRecordV2(
            _RECORD_ISSUER,
            index,
            candidate.spec.role,
            candidate.spec.schema,
            _record_domain(candidate.spec.role),
            key[1],
            tuple(
                sorted(key_to_record_id[item] for item in dependencies[key])
            ),
            candidate.raw.hex(),
        )
        records.append(record)
        key_to_record_id[key] = record.record_id
    return tuple(records), key_to_record_id


def _derived_record_dependencies(
    records: tuple[V075PortableEvidenceArtifactRecordV2, ...],
) -> dict[str, frozenset[str]]:
    return _derive_dependency_graph(
        tuple(
            _DependencyNode(
                record.record_id,
                record.role,
                record.semantic_artifact_id,
                record.canonical_artifact_bytes,
            )
            for record in records
        )
    )


_CONTROL_KIND_BY_SEMANTIC_ROLE = {
    "INITIAL_SCHEDULE_ROW_INTENT": "ROOT",
    "DYNAMIC_CHILD_DISCOVERY_INTENT": "CHILD",
    "LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT": "CHILD",
    "LIVE_PROMOTION_AUTHORIZATION": "PROMOTION",
}


def _verify_authoritative_dynamic_control_roles(
    records: tuple[V075PortableEvidenceArtifactRecordV2, ...],
) -> None:
    controlled_intents = {
        record.semantic_artifact_id: record
        for record in records
        if record.role
        in {
            "CONTROLLED_ROOT_INTENT",
            "CONTROLLED_CHILD_INTENT",
            "CONTROLLED_PROMOTION_INTENT",
        }
    }
    if len(controlled_intents) != sum(
        record.role
        in {
            "CONTROLLED_ROOT_INTENT",
            "CONTROLLED_CHILD_INTENT",
            "CONTROLLED_PROMOTION_INTENT",
        }
        for record in records
    ):
        _fail("controlled intent semantic IDs are duplicated")
    for record in records:
        suffix = None
        semantic_role = None
        if record.role.endswith("_SEMANTIC_AUTHORITY"):
            suffix = "SEMANTIC_AUTHORITY"
            semantic_role = record.artifact_document.get(
                "semantic_authority_role"
            )
        elif record.role.endswith("_INTENT") and record.role.startswith(
            "CONTROLLED_"
        ):
            suffix = "INTENT"
            semantic_role = record.artifact_document.get(
                "semantic_authority_role"
            )
        elif record.role.endswith("_APPEND") and record.role.startswith(
            "CONTROLLED_"
        ):
            suffix = "APPEND"
            intent_id = record.artifact_document.get("intent_id")
            intent = controlled_intents.get(intent_id)
            if intent is None:
                _fail("controlled append lacks its exact controlled intent")
            semantic_role = intent.artifact_document.get(
                "semantic_authority_role"
            )
        if suffix is None:
            continue
        kind = _CONTROL_KIND_BY_SEMANTIC_ROLE.get(semantic_role)
        if kind is None or record.role != f"CONTROLLED_{kind}_{suffix}":
            _fail(
                "controlled artifact role differs from embedded semantic "
                "authority"
            )


def _record_for_semantic_id(
    records: tuple[V075PortableEvidenceArtifactRecordV2, ...],
    *,
    role: str,
    semantic_artifact_id: Any,
    label: str,
) -> str:
    semantic_id = _cid(semantic_artifact_id, label)
    matches = tuple(
        record.record_id
        for record in records
        if record.role == role
        and record.semantic_artifact_id == semantic_id
    )
    if len(matches) != 1:
        _fail(f"{label} is missing, duplicated, or role-transplanted")
    return matches[0]


def _sole_record_id(
    records: tuple[V075PortableEvidenceArtifactRecordV2, ...],
    *,
    role: str,
) -> str:
    matches = tuple(
        record.record_id for record in records if record.role == role
    )
    if len(matches) != 1:
        _fail(f"portable root role {role} is missing or duplicated")
    return matches[0]


def _optional_root_record(
    records: tuple[V075PortableEvidenceArtifactRecordV2, ...],
    *,
    role: str,
    semantic_artifact_id: Any,
    label: str,
) -> tuple[str, ...]:
    if semantic_artifact_id is None:
        return ()
    return (
        _record_for_semantic_id(
            records,
            role=role,
            semantic_artifact_id=semantic_artifact_id,
            label=label,
        ),
    )


def _derive_expected_root_bindings(
    records: tuple[V075PortableEvidenceArtifactRecordV2, ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    result_record_id = _sole_record_id(records, role="MULTIROUND_RESULT")
    result_record = next(
        record for record in records if record.record_id == result_record_id
    )
    result = result_record.artifact_document
    reconciliation_record_id = _record_for_semantic_id(
        records,
        role="CLOSED_RECONCILIATION",
        semantic_artifact_id=result["closed_reconciliation_id"],
        label="portable root closed reconciliation",
    )
    reconciliation = next(
        record.artifact_document
        for record in records
        if record.record_id == reconciliation_record_id
    )
    planning_input_id = reconciliation["closed_planning_input_id"]
    planning_input_record_id = _record_for_semantic_id(
        records,
        role="CONSTRUCTION_PLANNING_INPUT",
        semantic_artifact_id=planning_input_id,
        label="portable root planning input",
    )
    planning_input = next(
        record.artifact_document
        for record in records
        if record.record_id == planning_input_record_id
    )

    def ordered(
        role: str,
        values: Iterable[Any],
        label: str,
    ) -> tuple[str, ...]:
        return tuple(
            _record_for_semantic_id(
                records,
                role=role,
                semantic_artifact_id=value,
                label=label,
            )
            for value in values
        )

    derived = {
        "initial_schedule": (
            _record_for_semantic_id(
                records,
                role="INITIAL_ACQUISITION_SCHEDULE",
                semantic_artifact_id=result["schedule_id"],
                label="portable root initial schedule",
            ),
        ),
        "initial_schedule_verification": (
            _record_for_semantic_id(
                records,
                role="INITIAL_ACQUISITION_VERIFICATION",
                semantic_artifact_id=result["schedule_verification_id"],
                label="portable root initial verification",
            ),
        ),
        "root_execution": (
            _record_for_semantic_id(
                records,
                role="ROOT_EXECUTION",
                semantic_artifact_id=result["root_execution_id"],
                label="portable root execution",
            ),
        ),
        "root_model_epoch": (
            _record_for_semantic_id(
                records,
                role="LIVE_MODEL_EPOCH",
                semantic_artifact_id=result["root_model_epoch_id"],
                label="portable root model epoch",
            ),
        ),
        "child_closure": (
            _record_for_semantic_id(
                records,
                role="DYNAMIC_CHILD_CLOSURE",
                semantic_artifact_id=result["child_closure_id"],
                label="portable root child closure",
            ),
        ),
        "child_closure_verification": (
            _record_for_semantic_id(
                records,
                role="DYNAMIC_CHILD_CLOSURE_VERIFICATION",
                semantic_artifact_id=(
                    result["child_closure_verification_id"]
                ),
                label="portable root child closure verification",
            ),
        ),
        "child_execution_ledger": _optional_root_record(
            records,
            role="DYNAMIC_CHILD_EXECUTION_LEDGER",
            semantic_artifact_id=result["child_execution_ledger_id"],
            label="portable root child execution ledger",
        ),
        "child_execution_verification": _optional_root_record(
            records,
            role="DYNAMIC_CHILD_EXECUTION_VERIFICATION",
            semantic_artifact_id=result[
                "child_execution_verification_id"
            ],
            label="portable root child execution verification",
        ),
        "child_replanning_barrier": _optional_root_record(
            records,
            role="DYNAMIC_CHILD_REPLANNING_BARRIER",
            semantic_artifact_id=result["child_replanning_barrier_id"],
            label="portable root child replanning barrier",
        ),
        "child_replanning_barrier_verification": _optional_root_record(
            records,
            role="DYNAMIC_CHILD_REPLANNING_BARRIER_VERIFICATION",
            semantic_artifact_id=result[
                "child_replanning_barrier_verification_id"
            ],
            label="portable root child barrier verification",
        ),
        "promotion_decisions": ordered(
            "LIVE_PROMOTION_DECISION",
            result["promotion_decision_ids"],
            "portable root promotion decision",
        ),
        "promotion_decision_verifications": ordered(
            "LIVE_PROMOTION_DECISION_VERIFICATION",
            result["promotion_decision_verification_ids"],
            "portable root promotion decision verification",
        ),
        "promotion_replanning_barriers": ordered(
            "LIVE_PROMOTION_REPLANNING_BARRIER",
            result["promotion_replanning_barrier_ids"],
            "portable root promotion barrier",
        ),
        "promotion_replanning_barrier_verifications": ordered(
            "LIVE_PROMOTION_REPLANNING_BARRIER_VERIFICATION",
            result["promotion_replanning_barrier_verification_ids"],
            "portable root promotion barrier verification",
        ),
        "final_model_epoch": (
            _record_for_semantic_id(
                records,
                role="LIVE_MODEL_EPOCH",
                semantic_artifact_id=result["final_model_epoch_id"],
                label="portable root final epoch",
            ),
        ),
        "controlled_journal_closure": (
            _sole_record_id(records, role="CONTROLLED_JOURNAL_CLOSURE"),
        ),
        "construction_lineage": (
            _record_for_semantic_id(
                records,
                role="CONSTRUCTION_LINEAGE",
                semantic_artifact_id=reconciliation["lineage_id"],
                label="portable root construction lineage",
            ),
        ),
        "construction_lifecycle": (
            _record_for_semantic_id(
                records,
                role="CONSTRUCTION_LIFECYCLE",
                semantic_artifact_id=(
                    reconciliation["lifecycle_closure_id"]
                ),
                label="portable root construction lifecycle",
            ),
            _record_for_semantic_id(
                records,
                role="CONSTRUCTION_LIFECYCLE_VERIFICATION",
                semantic_artifact_id=(
                    planning_input["lifecycle_verification_id"]
                ),
                label="portable root lifecycle verification",
            ),
        ),
        "closed_planning_input": (planning_input_record_id,),
        "closed_planning_proof": (
            _record_for_semantic_id(
                records,
                role="NUMERICAL_PLANNING_PROOF",
                semantic_artifact_id=reconciliation["closed_proof_id"],
                label="portable root closed planning proof",
            ),
        ),
        "closed_reconciliation": (reconciliation_record_id,),
        "multiround_result": (result_record_id,),
    }
    return tuple((name, derived[name]) for name in REQUIRED_ROOT_NAMES)


_BUNDLE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableOccurrenceEvidenceBundleV2:
    """Complete construction artifact table plus named typed roots."""

    _issuer: InitVar[object]
    occurrence_id: str
    records: tuple[V075PortableEvidenceArtifactRecordV2, ...]
    root_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(self.occurrence_id, "portable bundle occurrence")
        if (
            _issuer is not _BUNDLE_ISSUER
            or type(self.records) is not tuple
            or not self.records
            or len(self.records) > MAX_ARTIFACT_COUNT
            or any(
                type(item) is not V075PortableEvidenceArtifactRecordV2
                for item in self.records
            )
            or tuple(item.index for item in self.records)
            != tuple(range(len(self.records)))
            or len({item.record_id for item in self.records})
            != len(self.records)
            or type(self.root_bindings) is not tuple
            or tuple(name for name, _ids in self.root_bindings)
            != REQUIRED_ROOT_NAMES
        ):
            _fail("portable occurrence evidence bundle is malformed")
        _verify_authoritative_dynamic_control_roles(self.records)
        derived_dependencies = _derived_record_dependencies(self.records)
        for record in self.records:
            expected = tuple(
                sorted(derived_dependencies[record.record_id])
            )
            if record.dependency_record_ids != expected:
                _fail(
                    "portable record dependencies differ from raw artifact "
                    "semantics"
                )
        expected_roots = _derive_expected_root_bindings(self.records)
        if self.root_bindings != expected_roots:
            _fail(
                "portable named roots differ from authoritative result "
                "lineage"
            )
        record_ids = {item.record_id for item in self.records}
        seen: set[str] = set()
        for record in self.records:
            if not set(record.dependency_record_ids) <= seen:
                _fail("portable artifact table is not topologically ordered")
            seen.add(record.record_id)
        roots: set[str] = set()
        for name, ids in self.root_bindings:
            if (
                type(name) is not str
                or type(ids) is not tuple
                or len(set(ids)) != len(ids)
                or not set(ids) <= record_ids
            ):
                _fail("portable bundle root binding is unknown or duplicated")
            roots.update(ids)
        by_id = {item.record_id: item for item in self.records}
        reachable = set(roots)
        frontier = list(roots)
        while frontier:
            record_id = frontier.pop()
            for dependency in by_id[record_id].dependency_record_ids:
                if dependency not in reachable:
                    reachable.add(dependency)
                    frontier.append(dependency)
        if reachable != record_ids:
            _fail("portable bundle contains an unreferenced artifact record")
        _verify_complete_portable_graph(self)
        object.__setattr__(
            self,
            "_bundle_id",
            _hash(DOMAIN_TAGS["bundle"], self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_occurrence_evidence_bundle.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "occurrence_id": self.occurrence_id,
            "artifact_records": [item.to_document() for item in self.records],
            "root_bindings": [
                {"name": name, "record_ids": list(ids)}
                for name, ids in self.root_bindings
            ],
            "artifact_count": len(self.records),
            "topologically_ordered": True,
            "raw_canonical_artifact_bytes_complete": True,
            "semantic_registry_replay_complete": False,
            "private_material_serialized": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_BUNDLE_BYTES:
            _fail("portable occurrence evidence bundle exceeds its byte cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}


def _records_by_role(
    bundle: V075PortableOccurrenceEvidenceBundleV2,
) -> dict[str, tuple[V075PortableEvidenceArtifactRecordV2, ...]]:
    result: dict[str, list[V075PortableEvidenceArtifactRecordV2]] = {}
    for record in bundle.records:
        result.setdefault(record.role, []).append(record)
    return {key: tuple(value) for key, value in result.items()}


def _semantic_index(
    bundle: V075PortableOccurrenceEvidenceBundleV2,
) -> dict[tuple[str, str], V075PortableEvidenceArtifactRecordV2]:
    return {
        (record.role, record.semantic_artifact_id): record
        for record in bundle.records
    }


def _require_semantic_id(
    roles: Mapping[str, tuple[V075PortableEvidenceArtifactRecordV2, ...]],
    *,
    allowed_roles: Iterable[str],
    semantic_id: Any,
    label: str,
) -> None:
    expected = _cid(semantic_id, label)
    matches = tuple(
        record
        for role in allowed_roles
        for record in roles.get(role, ())
        if record.semantic_artifact_id == expected
    )
    if len(matches) != 1:
        _fail(f"{label} is missing, duplicated, or role-transplanted")


def _verify_complete_portable_graph(
    bundle: V075PortableOccurrenceEvidenceBundleV2,
) -> None:
    """Cross-check the portable table without claiming semantic authority."""

    roles = _records_by_role(bundle)
    mandatory_singletons = (
        "INITIAL_ACQUISITION_SCHEDULE",
        "INITIAL_ACQUISITION_VERIFICATION",
        "ROOT_EXECUTION",
        "DYNAMIC_CHILD_CLOSURE",
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        "CONTROLLED_JOURNAL_CLOSURE",
        "SIGNED_BATCH_JOURNAL_CLOSURE",
        "SIGNED_CONTROL_CLOSURE",
        "SIGNED_CONTROL_RECONCILIATION",
        "CONSTRUCTION_LINEAGE",
        "CONSTRUCTION_LIFECYCLE",
        "CONSTRUCTION_LIFECYCLE_VERIFICATION",
        "CONSTRUCTION_PLANNING_INPUT",
        "CLOSED_RECONCILIATION",
        "MULTIROUND_RESULT",
    )
    if any(len(roles.get(role, ())) != 1 for role in mandatory_singletons):
        _fail("portable graph omits or duplicates a mandatory closure role")
    result = roles["MULTIROUND_RESULT"][0].artifact_document
    schedule = roles["INITIAL_ACQUISITION_SCHEDULE"][0].artifact_document
    if (
        result.get("fresh_heldout_accessed") is not False
        or result.get("official_execution_allowed") is not False
        or result.get("plan_certificate") is not False
        or result.get("infeasibility_certificate") is not False
    ):
        _fail("portable graph attempts to unlock a forbidden claim")
    if (
        type(schedule.get("occurrence")) is not dict
        or schedule["occurrence"].get("occurrence_id")
        != bundle.occurrence_id
        or roles["CONSTRUCTION_LINEAGE"][0]
        .artifact_document.get("occurrence_id")
        != bundle.occurrence_id
        or roles["CONSTRUCTION_LIFECYCLE"][0]
        .artifact_document.get("occurrence_id")
        != bundle.occurrence_id
        or roles["SIGNED_CONTROL_CLOSURE"][0]
        .artifact_document.get("occurrence_id")
        != bundle.occurrence_id
    ):
        _fail("portable occurrence roots differ from bundle identity")
    if result.get("schedule_id") is None:
        _fail("portable result lacks its schedule")
    _require_semantic_id(
        roles,
        allowed_roles=("INITIAL_ACQUISITION_SCHEDULE",),
        semantic_id=result["schedule_id"],
        label="portable result schedule",
    )
    _require_semantic_id(
        roles,
        allowed_roles=("INITIAL_ACQUISITION_VERIFICATION",),
        semantic_id=result["schedule_verification_id"],
        label="portable result schedule verification",
    )
    for key, allowed_roles in (
        ("root_execution_id", ("ROOT_EXECUTION",)),
        ("root_model_epoch_id", ("LIVE_MODEL_EPOCH",)),
        ("child_closure_id", ("DYNAMIC_CHILD_CLOSURE",)),
        (
            "child_closure_verification_id",
            ("DYNAMIC_CHILD_CLOSURE_VERIFICATION",),
        ),
        ("final_model_epoch_id", ("LIVE_MODEL_EPOCH",)),
        ("final_numerical_model_id", ("NUMERICAL_MODEL",)),
        ("final_proof_id", ("NUMERICAL_PLANNING_PROOF",)),
        ("closed_reconciliation_id", ("CLOSED_RECONCILIATION",)),
    ):
        _require_semantic_id(
            roles,
            allowed_roles=allowed_roles,
            semantic_id=result[key],
            label=f"portable result {key}",
        )
    for key, allowed_roles in (
        (
            "child_execution_ledger_id",
            ("DYNAMIC_CHILD_EXECUTION_LEDGER",),
        ),
        (
            "child_execution_verification_id",
            ("DYNAMIC_CHILD_EXECUTION_VERIFICATION",),
        ),
        (
            "child_replanning_barrier_id",
            ("DYNAMIC_CHILD_REPLANNING_BARRIER",),
        ),
        (
            "child_replanning_barrier_verification_id",
            ("DYNAMIC_CHILD_REPLANNING_BARRIER_VERIFICATION",),
        ),
    ):
        value = result[key]
        if value is not None:
            _require_semantic_id(
                roles,
                allowed_roles=allowed_roles,
                semantic_id=value,
                label=f"portable result {key}",
            )
    for key, allowed_roles in (
        ("promotion_decision_ids", ("LIVE_PROMOTION_DECISION",)),
        (
            "promotion_decision_verification_ids",
            ("LIVE_PROMOTION_DECISION_VERIFICATION",),
        ),
        (
            "promotion_replanning_barrier_ids",
            ("LIVE_PROMOTION_REPLANNING_BARRIER",),
        ),
        (
            "promotion_replanning_barrier_verification_ids",
            ("LIVE_PROMOTION_REPLANNING_BARRIER_VERIFICATION",),
        ),
    ):
        for semantic_id in result[key]:
            _require_semantic_id(
                roles,
                allowed_roles=allowed_roles,
                semantic_id=semantic_id,
                label=f"portable result {key}",
            )

    controlled = roles["CONTROLLED_JOURNAL_CLOSURE"][0].artifact_document
    head_ids = controlled.get("head_ids")
    intent_ids = controlled.get("intent_ids")
    receipt_ids = controlled.get("append_receipt_ids")
    freeze_ids = controlled.get("support_freeze_ids")
    if (
        type(head_ids) is not list
        or type(intent_ids) is not list
        or type(receipt_ids) is not list
        or type(freeze_ids) is not list
        or len(head_ids) != len(receipt_ids) + 1
        or len(intent_ids) != len(receipt_ids)
    ):
        _fail("portable controlled journal closure is incomplete")
    for semantic_id in head_ids:
        _require_semantic_id(
            roles,
            allowed_roles=("SIGNED_CONTROL_JOURNAL_HEAD",),
            semantic_id=semantic_id,
            label="portable signed control head",
        )
    intent_roles = (
        "CONTROLLED_ROOT_INTENT",
        "CONTROLLED_CHILD_INTENT",
        "CONTROLLED_PROMOTION_INTENT",
    )
    append_roles = (
        "CONTROLLED_ROOT_APPEND",
        "CONTROLLED_CHILD_APPEND",
        "CONTROLLED_PROMOTION_APPEND",
    )
    for semantic_id in intent_ids:
        _require_semantic_id(
            roles,
            allowed_roles=intent_roles,
            semantic_id=semantic_id,
            label="portable controlled intent",
        )
    for semantic_id in receipt_ids:
        _require_semantic_id(
            roles,
            allowed_roles=("SIGNED_APPEND_RECEIPT",),
            semantic_id=semantic_id,
            label="portable append receipt",
        )
        append_matches = tuple(
            record
            for role in append_roles
            for record in roles.get(role, ())
            if record.artifact_document.get("append_receipt_id")
            == semantic_id
        )
        if len(append_matches) != 1:
            _fail("portable append execution is missing or duplicated")
    for semantic_id in freeze_ids:
        _require_semantic_id(
            roles,
            allowed_roles=("CONTROLLED_COMPLETE_SUPPORT_FREEZE",),
            semantic_id=semantic_id,
            label="portable complete support freeze",
        )

    for batch in roles.get("SIGNED_OBSERVATION_BATCH", ()):
        document = batch.artifact_document
        request = document.get("request")
        outcomes = document.get("outcomes")
        if type(request) is not dict or type(outcomes) is not list:
            _fail("portable signed batch lacks request or outcomes")
        _require_semantic_id(
            roles,
            allowed_roles=("SIGNED_BATCH_REQUEST",),
            semantic_id=document["request_id"],
            label="portable signed batch request",
        )
        _require_semantic_id(
            roles,
            allowed_roles=("TRANSITION_STREAM",),
            semantic_id=document["stream_id"],
            label="portable signed batch stream",
        )
        for outcome_document in outcomes:
            matches = tuple(
                record
                for record in roles.get("SIGNED_BATCH_OUTCOME", ())
                if record.artifact_document == outcome_document
            )
            if len(matches) != 1:
                _fail(
                    "portable signed batch outcome is missing or duplicated"
                )
    if len(roles.get("SIGNED_OBSERVATION_BATCH", ())) != len(receipt_ids):
        _fail("portable signed batch count differs from controlled receipts")

    epochs = roles.get("LIVE_MODEL_EPOCH", ())
    if not epochs:
        _fail("portable graph contains no live model epoch")
    epoch_documents = {
        record.semantic_artifact_id: record.artifact_document
        for record in epochs
    }
    roots = tuple(
        (epoch_id, document)
        for epoch_id, document in epoch_documents.items()
        if document.get("parent_epoch_id") is None
    )
    if len(roots) != 1:
        _fail("portable live epoch graph lacks one unique root")
    for epoch_id, document in epoch_documents.items():
        parent_id = document.get("parent_epoch_id")
        if parent_id is not None and parent_id not in epoch_documents:
            _fail("portable live epoch parent chain is incomplete")
        _require_semantic_id(
            roles,
            allowed_roles=("NUMERICAL_MODEL",),
            semantic_id=document["numerical_model_id"],
            label="portable live epoch model",
        )
        _require_semantic_id(
            roles,
            allowed_roles=("NUMERICAL_PLANNING_PROOF",),
            semantic_id=document["numerical_proof_id"],
            label="portable live epoch proof",
        )
        if epoch_id == parent_id:
            _fail("portable live epoch self-cycle")

    reconciliation = roles["CLOSED_RECONCILIATION"][0].artifact_document
    for key, allowed_roles in (
        ("final_model_epoch_id", ("LIVE_MODEL_EPOCH",)),
        ("final_numerical_model_id", ("NUMERICAL_MODEL",)),
        ("final_proof_id", ("NUMERICAL_PLANNING_PROOF",)),
        ("lineage_id", ("CONSTRUCTION_LINEAGE",)),
        ("lifecycle_closure_id", ("CONSTRUCTION_LIFECYCLE",)),
        ("closed_planning_input_id", ("CONSTRUCTION_PLANNING_INPUT",)),
        ("closed_proof_id", ("NUMERICAL_PLANNING_PROOF",)),
    ):
        _require_semantic_id(
            roles,
            allowed_roles=allowed_roles,
            semantic_id=reconciliation[key],
            label=f"portable closed reconciliation {key}",
        )
    compiler = roles["CONSTRUCTION_PLANNING_INPUT"][0].artifact_document
    _require_semantic_id(
        roles,
        allowed_roles=("CONSTRUCTION_LIFECYCLE_VERIFICATION",),
        semantic_id=compiler["lifecycle_verification_id"],
        label="portable compiler lifecycle verification",
    )


def freeze_v075_portable_occurrence_evidence_bundle_v2(
    *,
    evidence_roots: Mapping[str, Any],
) -> V075PortableOccurrenceEvidenceBundleV2:
    """Freeze the immutable roots exported by the construction runner."""

    if (
        not isinstance(evidence_roots, Mapping)
        or tuple(evidence_roots.keys()) != REQUIRED_ROOT_NAMES
    ):
        _fail("portable evidence roots are missing, reordered, or unknown")
    exact_lineage = evidence_roots["construction_lineage"]
    exact_lifecycle = evidence_roots["construction_lifecycle"]
    if (
        type(exact_lineage) is not lineage.V075BatchOccurrenceLineageV2
        or type(exact_lifecycle)
        is not lifecycle.V075BatchOccurrenceLifecycleClosureV2
    ):
        _fail("portable evidence lacks exact lineage/lifecycle roots")
    streams = tuple(
        sorted(
            {
                entry.batch.request.stream_identity.stream_id: (
                    entry.batch.request.stream_identity
                )
                for entry in exact_lineage.closure.entries
            }.values(),
            key=lambda item: item.stream_id,
        )
    )
    try:
        replayed_lifecycle, lifecycle_verification = (
            lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2(
                lifecycle_bytes=exact_lifecycle.canonical_bytes,
                lineage_bytes=exact_lineage.canonical_bytes,
                batch_closure_bytes=(
                    exact_lineage.closure.canonical_bytes
                ),
                known_stream_identities=streams,
            )
        )
    except Exception as error:
        raise V075PortableOccurrenceEvidenceV2InvariantViolation(
            "portable lifecycle verification reconstruction failed"
        ) from error
    planning_input = evidence_roots["closed_planning_input"]
    if (
        replayed_lifecycle.canonical_bytes
        != exact_lifecycle.canonical_bytes
        or type(planning_input)
        is not planning.V075ConstructionPlanningInputV2
        or planning_input.lifecycle_verification_id
        != lifecycle_verification.verification_id
    ):
        _fail("portable lifecycle verification differs from compiler binding")
    augmented_roots = dict(evidence_roots)
    augmented_roots["construction_lifecycle"] = (
        exact_lifecycle,
        lifecycle_verification,
    )
    candidates, _root_keys = _walk_artifact_candidates(augmented_roots)
    if not candidates or len(candidates) > MAX_ARTIFACT_COUNT:
        _fail("portable evidence candidate count is empty or over cap")
    dependencies = _candidate_dependencies(candidates)
    ordered_keys = _topological_keys(candidates, dependencies)
    records, _key_to_record_id = _freeze_records(
        candidates,
        dependencies,
        ordered_keys,
    )
    root_bindings = _derive_expected_root_bindings(records)
    result = evidence_roots["multiround_result"]
    schedule = evidence_roots["initial_schedule"]
    if (
        type(result) is not runner.V075ObserverSignedMultiroundResultV2
        or type(schedule) is not acquisition.V075InitialAcquisitionScheduleV2
    ):
        _fail("portable evidence roots lack the exact multiround result")
    return V075PortableOccurrenceEvidenceBundleV2(
        _BUNDLE_ISSUER,
        schedule.occurrence.occurrence_id,
        records,
        root_bindings,
    )


_RECORD_DOCUMENT_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "index",
        "role",
        "artifact_schema",
        "artifact_domain_tag",
        "semantic_artifact_id",
        "dependency_record_ids",
        "canonical_artifact_bytes_hex",
        "raw_bytes_complete",
        "private_material_serialized",
        "official_execution_allowed",
        "record_id",
    }
)

_BUNDLE_DOCUMENT_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "terminal_scope",
        "terminal_class",
        "occurrence_id",
        "artifact_records",
        "root_bindings",
        "artifact_count",
        "topologically_ordered",
        "raw_canonical_artifact_bytes_complete",
        "semantic_registry_replay_complete",
        "private_material_serialized",
        "fresh_heldout_accessed",
        "official_execution_allowed",
        "production_authorizing",
        "scientific_endpoint_credit_allowed",
        "plan_certificate",
        "infeasibility_certificate",
        "bundle_id",
    }
)


def _raw_dependency_failure(
    raw_records: list[dict[str, Any]],
) -> str | None:
    record_ids = [item.get("record_id") for item in raw_records]
    if (
        any(type(item) is not str for item in record_ids)
        or len(set(record_ids)) != len(record_ids)
    ):
        return "duplicate or malformed"
    known = set(record_ids)
    graph_by_id: dict[str, tuple[str, ...]] = {}
    for item in raw_records:
        dependencies = item.get("dependency_record_ids")
        if type(dependencies) is not list:
            return "malformed"
        if any(dependency not in known for dependency in dependencies):
            return "missing"
        graph_by_id[item["record_id"]] = tuple(dependencies)
    visiting: set[str] = set()
    visited: set[str] = set()

    def cyclic(record_id: str) -> bool:
        if record_id in visiting:
            return True
        if record_id in visited:
            return False
        visiting.add(record_id)
        if any(cyclic(item) for item in graph_by_id[record_id]):
            return True
        visiting.remove(record_id)
        visited.add(record_id)
        return False

    if any(cyclic(record_id) for record_id in graph_by_id):
        return "cyclic"
    position = {
        record_id: index for index, record_id in enumerate(record_ids)
    }
    if any(
        position[dependency] >= position[record_id]
        for record_id, dependencies in graph_by_id.items()
        for dependency in dependencies
    ):
        return "out-of-order"
    return None


def verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
    raw: bytes,
) -> V075PortableOccurrenceEvidenceBundleV2:
    """Strict raw-byte reconstruction of the portable table and topology."""

    if type(raw) is not bytes or not raw or len(raw) > MAX_BUNDLE_BYTES:
        _fail("portable bundle bytes are empty, untyped, or exceed their cap")
    document = _strict_json_document(raw, label="portable bundle")
    if set(document) != _BUNDLE_DOCUMENT_KEYS:
        _fail("portable bundle contains missing or hidden extra fields")
    if (
        document.get("schema")
        != "acfqp.v075_portable_occurrence_evidence_bundle.v2"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version")
        != PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("terminal_scope") != TERMINAL_SCOPE
        or document.get("terminal_class") != TERMINAL_CLASS
        or document.get("semantic_registry_replay_complete") is not False
        or document.get("private_material_serialized") is not False
        or document.get("fresh_heldout_accessed") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("production_authorizing") is not False
        or document.get("scientific_endpoint_credit_allowed") is not False
        or document.get("plan_certificate") is not False
        or document.get("infeasibility_certificate") is not False
    ):
        _fail("portable bundle metadata or construction locks changed")
    raw_records = document.get("artifact_records")
    if (
        type(raw_records) is not list
        or not raw_records
        or len(raw_records) > MAX_ARTIFACT_COUNT
        or document.get("artifact_count") != len(raw_records)
        or document.get("topologically_ordered") is not True
        or document.get("raw_canonical_artifact_bytes_complete") is not True
    ):
        _fail("portable bundle artifact table is malformed")
    if any(
        type(item) is not dict or set(item) != _RECORD_DOCUMENT_KEYS
        for item in raw_records
    ):
        _fail("portable record contains missing or hidden extra fields")
    dependency_failure = _raw_dependency_failure(raw_records)
    if dependency_failure is not None:
        _fail(f"portable dependency graph is {dependency_failure}")
    records: list[V075PortableEvidenceArtifactRecordV2] = []
    for index, claimed in enumerate(raw_records):
        if claimed.get("index") != index:
            _fail("portable record index is gapped or reordered")
        if (
            claimed.get("schema")
            != "acfqp.v075_portable_evidence_artifact_record.v2"
            or claimed.get("schema_version") != SCHEMA_VERSION
            or claimed.get("profile_key") != PROFILE_KEY
            or claimed.get("raw_bytes_complete") is not True
            or claimed.get("private_material_serialized") is not False
            or claimed.get("official_execution_allowed") is not False
        ):
            _fail("portable record metadata changed")
        record = V075PortableEvidenceArtifactRecordV2(
            _RECORD_ISSUER,
            index,
            claimed["role"],
            claimed["artifact_schema"],
            claimed["artifact_domain_tag"],
            claimed["semantic_artifact_id"],
            tuple(claimed["dependency_record_ids"]),
            claimed["canonical_artifact_bytes_hex"],
        )
        if record.record_id != claimed["record_id"]:
            _fail("portable record content ID differs from raw bytes")
        records.append(record)
    raw_roots = document.get("root_bindings")
    if (
        type(raw_roots) is not list
        or len(raw_roots) != len(REQUIRED_ROOT_NAMES)
        or any(
            type(item) is not dict
            or set(item) != {"name", "record_ids"}
            or type(item.get("record_ids")) is not list
            for item in raw_roots
        )
    ):
        _fail("portable root bindings contain hidden or missing fields")
    root_bindings = tuple(
        (item["name"], tuple(item["record_ids"])) for item in raw_roots
    )
    bundle = V075PortableOccurrenceEvidenceBundleV2(
        _BUNDLE_ISSUER,
        document["occurrence_id"],
        tuple(records),
        root_bindings,
    )
    if (
        bundle.bundle_id != document["bundle_id"]
        or bundle.canonical_bytes != raw
    ):
        _fail("portable bundle identity or canonical replay changed")
    return bundle


def run_and_freeze_v075_portable_occurrence_evidence_bundle_v2(
    **runner_arguments: Any,
) -> tuple[
    runner.V075ObserverSignedMultiroundResultV2,
    V075PortableOccurrenceEvidenceBundleV2,
]:
    """Run the construction occurrence and freeze its post-closure roots."""

    if "evidence_sink" in runner_arguments:
        _fail("portable runner wrapper exclusively owns the evidence sink")
    captured: dict[str, Any] = {}

    def sink(roots: Mapping[str, Any]) -> None:
        if captured:
            _fail("construction runner emitted evidence roots more than once")
        captured.update(roots)

    result = (
        runner.run_v075_construction_observer_signed_multiround_occurrence_v2(
            **runner_arguments,
            evidence_sink=sink,
        )
    )
    if tuple(captured) != REQUIRED_ROOT_NAMES:
        _fail("construction runner did not emit the complete closed roots")
    bundle = freeze_v075_portable_occurrence_evidence_bundle_v2(
        evidence_roots=MappingProxyType(captured),
    )
    replayed = verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
        bundle.canonical_bytes
    )
    if replayed.bundle_id != bundle.bundle_id:
        _fail("fresh portable evidence bundle failed immediate raw replay")
    return result, bundle


def open_v075_production_portable_occurrence_evidence_bundle_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortableOccurrenceEvidenceProductionV2NotReady(
        PRODUCTION_BLOCKER
    )


__all__ = [
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "MAX_ARTIFACT_BYTES",
    "MAX_ARTIFACT_COUNT",
    "MAX_BUNDLE_BYTES",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PROFILE_KEY",
    "PRODUCTION_AUTHORIZING",
    "PROPOSED_CONTRACT_VERSION",
    "REQUIRED_ROOT_NAMES",
    "ROLE_SCHEMA_REGISTRY",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SEMANTIC_REGISTRY_REPLAY_COMPLETE",
    "TERMINAL_CLASS",
    "TERMINAL_SCOPE",
    "V075PortableEvidenceArtifactRecordV2",
    "V075PortableOccurrenceEvidenceBundleV2",
    "V075PortableOccurrenceEvidenceProductionV2NotReady",
    "V075PortableOccurrenceEvidenceV2InvariantViolation",
    "freeze_v075_portable_occurrence_evidence_bundle_v2",
    "open_v075_production_portable_occurrence_evidence_bundle_v2",
    "run_and_freeze_v075_portable_occurrence_evidence_bundle_v2",
    "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
]
