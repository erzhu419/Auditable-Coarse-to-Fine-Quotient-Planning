"""Portable construction closed-reconciliation replay authority for V0-075.

Contract 1.80 starts with the exact five-input contract-1.79 replay.  Only
after that raw authority succeeds does this module inspect the portable
bundle and invoke the occurrence-runner-owned closed-reconciliation freezer.
The resulting reconciliation must equal the sole portable
``CLOSED_RECONCILIATION`` record byte-for-byte and by semantic identity.

Every owner input is selected from the fresh producer graph by its registered
semantic identity.  In particular, this authority never takes the first live
epoch, numerical model, or proof when several records are present.  The final
epoch must be both the reconciliation-named epoch and the unique maximum
epoch.  The exact controlled closure comes from the M1B typed graph; schedule,
lineage, lifecycle, and planning input come from the fresh 1.79 graph.

This remains an in-memory construction cut.  Private inputs are passed only
to raw 1.79, are not retained or serialized, are not directly hashed here,
and do not produce a secret digest.  Currentness requires another explicit
five-input raw replay.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import heapq
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle
from acfqp import v075_batched_observer_authority_v2 as lineage_authority
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import (
    v075_observer_signed_multiround_occurrence_runner_v2 as owner,
)
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import (
    v075_portable_construction_planning_input_authority_v2 as input_authority,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.80.0"
PROFILE_KEY = (
    "v075_portable_construction_closed_reconciliation_authority_v2"
)

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED = True
CONSTRUCTION_PLANNING_INPUT_REPLAY_REQUIRED = True
CONSTRUCTION_CLOSED_RECONCILIATION_REPLAYED = True
PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED = False
PRODUCTION_RECONCILIATION_ALLOWED = False
B3_INPUT_ALLOWED = False
K7_INPUT_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
J0_ACCESS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False
WORKER_LAUNCH_ALLOWED = False
OPERATIONAL_REGISTRIES_ALLOWED = False
ACCOUNTING_GATE_PASSED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_CLOSED_RECONCILIATION_REPLAY_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY_COMPLETE_"
    "MULTIROUND_RESULT_AUTHORITY_UNRESOLVED"
)
MAX_DEPENDENCY_NODES = 4096
MAX_OUTPUT_BYTES = 64 * 1024 * 1024

ROLE_ORDER = (
    "CONSTRUCTION_PLANNING_INPUT",
    "CLOSED_RECONCILIATION",
    "MULTIROUND_RESULT",
)
SOURCE_ROLE_ORDER = tuple(
    sorted(
        (
            "CONSTRUCTION_LIFECYCLE",
            "CONSTRUCTION_LINEAGE",
            "CONSTRUCTION_PLANNING_INPUT",
            "CONTROLLED_JOURNAL_CLOSURE",
            "INITIAL_ACQUISITION_SCHEDULE",
            "LIVE_MODEL_EPOCH",
            "NUMERICAL_MODEL",
            "NUMERICAL_PLANNING_PROOF",
            "SIGNED_BATCH_JOURNAL_CLOSURE",
            "SIGNED_CONTROL_CLOSURE",
        )
    )
)
_ROLE_SET = frozenset(ROLE_ORDER)
_SOURCE_ROLE_SET = frozenset(SOURCE_ROLE_ORDER)

DOMAIN_TAGS = MappingProxyType(
    {
        "source_binding": (
            "acfqp:v075-portable-construction-closed-reconciliation-"
            "source:v2"
        ),
        "typed_graph": (
            "acfqp:v075-portable-construction-closed-reconciliation-graph:v2"
        ),
        "dependency_dag": (
            "acfqp:v075-portable-construction-closed-reconciliation-dag:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-construction-closed-reconciliation-"
            "closure:v2"
        ),
        "aggregate": (
            "acfqp:v075-portable-construction-closed-reconciliation-"
            "authority:v2"
        ),
    }
)

_REPLAY_MISMATCH = (
    "construction closed-reconciliation replay did not match registered "
    "evidence"
)


class V075PortableConstructionClosedReconciliationV2InvariantViolation(
    ValueError
):
    """Raw replay, owner replay, exact binding, or dependency closure failed."""


class V075PortableConstructionClosedReconciliationProductionV2NotReady(
    RuntimeError
):
    """Contract 1.80 cannot authorize a production occurrence."""


class V075ConstructionClosedReconciliationRoleStatusV2(str, Enum):
    FULL_CONSTRUCTION_COMPILER_REPLAY = (
        "FULL_CONSTRUCTION_COMPILER_REPLAY"
    )
    FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY = (
        "FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"
    )
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )


class V075ConstructionClosedReconciliationResolverKindV2(str, Enum):
    UPSTREAM_CONSTRUCTION_PLANNING_INPUT_REPLAY = (
        "UPSTREAM_CONSTRUCTION_PLANNING_INPUT_REPLAY"
    )
    CONSTRUCTION_CLOSED_RECONCILIATION_OWNER_REPLAY = (
        "CONSTRUCTION_CLOSED_RECONCILIATION_OWNER_REPLAY"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


class V075ConstructionClosedReconciliationAuthorityScopeV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    FULL_CONSTRUCTION_PRIVATE_REPLAY = (
        "FULL_CONSTRUCTION_PRIVATE_REPLAY"
    )
    FULL_CONSTRUCTION_COMPILER_REPLAY = (
        "FULL_CONSTRUCTION_COMPILER_REPLAY"
    )
    FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY = (
        "FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"
    )
    FULL_CONSTRUCTION_TRANSITIVE = "FULL_CONSTRUCTION_TRANSITIVE"
    UNRESOLVED = "UNRESOLVED"


def _fail(message: str) -> NoReturn:
    raise V075PortableConstructionClosedReconciliationV2InvariantViolation(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise (
            V075PortableConstructionClosedReconciliationV2InvariantViolation(
                f"{label} must be one lowercase SHA-256 content ID"
            )
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise (
            V075PortableConstructionClosedReconciliationV2InvariantViolation(
                "closed-reconciliation public identity is malformed"
            )
        ) from error


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _sole_by_role(
    values: tuple[Any, ...],
    role: str,
    label: str,
) -> Any:
    matches = tuple(item for item in values if item.role == role)
    if len(matches) != 1:
        _fail(f"{label} role {role} is absent or duplicated")
    return matches[0]


def _unique_by_semantic_id(
    values: tuple[Any, ...],
    *,
    semantic_id: str,
    identity_attribute: str,
    label: str,
) -> Any:
    """Select one typed producer by semantic ID, never by tuple position."""

    semantic_id = _cid(semantic_id, label)
    matches = tuple(
        item
        for item in values
        if getattr(item, identity_attribute, None) == semantic_id
    )
    if len(matches) != 1:
        _fail(f"{label} is absent or duplicated")
    return matches[0]


def _portable_record(
    records: tuple[Any, ...],
    *,
    role: str,
    semantic_id: str | None = None,
    expected_raw: bytes | None = None,
    label: str,
) -> Any:
    """Select one exact role/semantic record and optionally bind its bytes."""

    if type(records) is not tuple:
        _fail(f"{label} registry is malformed")
    if semantic_id is not None:
        semantic_id = _cid(semantic_id, label)
    matches = tuple(
        item
        for item in records
        if getattr(item, "role", None) == role
        and (
            semantic_id is None
            or getattr(item, "semantic_artifact_id", None) == semantic_id
        )
    )
    if len(matches) != 1:
        _fail(f"{label} is absent, duplicated, or role-transplanted")
    record = matches[0]
    if (
        expected_raw is not None
        and getattr(record, "canonical_artifact_bytes", None) != expected_raw
    ):
        _fail(f"{label} bytes differ from the exact producer")
    return record


def _exact_chain(
    replayed: input_authority.V075PortableConstructionPlanningInputReplayV2,
) -> tuple[Any, ...]:
    """Extract the exact owner inputs and public typed registries from 1.79."""

    if (
        type(replayed)
        is not input_authority.V075PortableConstructionPlanningInputReplayV2
    ):
        _fail("closed reconciliation requires exact raw contract 1.79")
    _ = replayed.result_id
    try:
        input_graph = replayed.typed_graph
        private_result = input_graph.private_replay_result
        hardened = private_result.typed_graph.hardened_planning_result
        dynamic = hardened.typed_graph.m2_dynamic_child_result
        live_result = dynamic.typed_graph.m2_live_epoch_result
        lifecycle_result = live_result.typed_graph.m2_lifecycle_result
        lineage_result = lifecycle_result.typed_graph.m2_lineage_result
        root_result = lineage_result.typed_graph.m2_result
        root_graph = root_result.typed_graph
        m1b_result = root_graph.m1b_result
        m1b_graph = m1b_result.typed_graph
        m1a_result = m1b_graph.m1a_result
        m1a_graph = m1a_result.typed_graph
        m0_result = m1a_graph.m0_result
        m0_graph = m0_result.typed_graph
        schedule = input_graph.schedule
        lineage = private_result.typed_graph.construction_lineage
        lifecycle_value = (
            private_result.typed_graph.construction_lifecycle
        )
        lifecycle_verification = (
            private_result.typed_graph
            .construction_lifecycle_verification
        )
        controlled_closure = m1b_graph.controlled_closure
        epochs = live_result.typed_graph.epochs
        compiled_input = input_graph.construction_planning_input
    except (AttributeError, TypeError) as error:
        raise (
            V075PortableConstructionClosedReconciliationV2InvariantViolation(
                "contract 1.79 omitted its exact owner producer graph"
            )
        ) from error
    if (
        type(schedule) is not acquisition.V075InitialAcquisitionScheduleV2
        or type(lineage)
        is not lineage_authority.V075BatchOccurrenceLineageV2
        or type(lifecycle_value)
        is not lifecycle.V075BatchOccurrenceLifecycleClosureV2
        or type(controlled_closure)
        is not control.V075ControlledBatchJournalClosureV2
        or type(compiled_input)
        is not planning.V075ConstructionPlanningInputV2
        or type(epochs) is not tuple
        or not epochs
        or any(
            type(item) is not live_model.V075LiveIncrementalModelEpochV2
            for item in epochs
        )
        or schedule is not m0_graph.schedule
        or schedule.occurrence != lineage.occurrence_identity
        or compiled_input is not input_graph.construction_planning_input
        or compiled_input.schedule_id != schedule.schedule_id
        or compiled_input.lineage_id != lineage.lineage_id
        or compiled_input.lifecycle_closure_id
        != lifecycle_value.closure_id
        or compiled_input.lifecycle_verification_id
        != lifecycle_verification.verification_id
        or replayed.bundle_id != hardened.bundle_id
        or replayed.occurrence_id != schedule.occurrence.occurrence_id
    ):
        _fail("contract 1.79 owner inputs crossed exact producer identities")
    return (
        hardened,
        m0_result,
        m1b_result,
        live_result,
        schedule,
        controlled_closure,
        lineage,
        lifecycle_value,
        lifecycle_verification,
        compiled_input,
        epochs,
    )


def _exact_final_epoch(
    *,
    epochs: tuple[live_model.V075LiveIncrementalModelEpochV2, ...],
    reconciliation_document: Mapping[str, Any],
) -> live_model.V075LiveIncrementalModelEpochV2:
    epoch_id = _cid(
        reconciliation_document.get("final_model_epoch_id"),
        "closed reconciliation final epoch",
    )
    selected = _unique_by_semantic_id(
        epochs,
        semantic_id=epoch_id,
        identity_attribute="model_epoch_id",
        label="closed reconciliation final epoch",
    )
    maximum_index = max(item.epoch_index for item in epochs)
    maxima = tuple(item for item in epochs if item.epoch_index == maximum_index)
    if len(maxima) != 1 or selected is not maxima[0]:
        _fail("reconciliation final epoch is not the unique maximum epoch")
    return selected


def _exact_model_and_proof(
    *,
    hardened: Any,
    final_epoch: live_model.V075LiveIncrementalModelEpochV2,
    reconciliation_document: Mapping[str, Any],
) -> tuple[planning.V075NumericalModelV2, planning.V075NumericalPlanningProofV2]:
    model_id = _cid(
        reconciliation_document.get("final_numerical_model_id"),
        "closed reconciliation final model",
    )
    proof_id = _cid(
        reconciliation_document.get("final_proof_id"),
        "closed reconciliation final proof",
    )
    closed_proof_id = _cid(
        reconciliation_document.get("closed_proof_id"),
        "closed reconciliation closed proof",
    )
    model = _unique_by_semantic_id(
        hardened.typed_graph.models,
        semantic_id=model_id,
        identity_attribute="model_id",
        label="closed reconciliation final model",
    )
    proof = _unique_by_semantic_id(
        hardened.typed_graph.proofs,
        semantic_id=proof_id,
        identity_attribute="proof_id",
        label="closed reconciliation final proof",
    )
    model_bindings = tuple(
        item
        for item in hardened.typed_graph.target_record_bindings
        if item.role == "NUMERICAL_MODEL"
        and item.semantic_artifact_id == model_id
    )
    proof_bindings = tuple(
        item
        for item in hardened.typed_graph.target_record_bindings
        if item.role == "NUMERICAL_PLANNING_PROOF"
        and item.semantic_artifact_id == proof_id
    )
    if (
        len(model_bindings) != 1
        or len(proof_bindings) != 1
        or model_id != final_epoch.model.model_id
        or proof_id != final_epoch.proof.proof_id
        or proof_id != closed_proof_id
        or _raw(model) != _raw(final_epoch.model)
        or _raw(proof) != _raw(final_epoch.proof)
        or model_bindings[0].canonical_artifact_bytes != _raw(model)
        or proof_bindings[0].canonical_artifact_bytes != _raw(proof)
    ):
        _fail("final model/proof differ from the exact all-epoch registry")
    return model, proof


def _exact_portable_sources(
    *,
    records: tuple[Any, ...],
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    controlled_closure: control.V075ControlledBatchJournalClosureV2,
    final_epoch: live_model.V075LiveIncrementalModelEpochV2,
    final_model: planning.V075NumericalModelV2,
    final_proof: planning.V075NumericalPlanningProofV2,
    lineage: lineage_authority.V075BatchOccurrenceLineageV2,
    lifecycle_value: lifecycle.V075BatchOccurrenceLifecycleClosureV2,
    planning_input: planning.V075ConstructionPlanningInputV2,
) -> tuple[Any, ...]:
    """Bind every direct owner input/output component to one portable record."""

    values = (
        _portable_record(
            records,
            role="CONSTRUCTION_LIFECYCLE",
            semantic_id=lifecycle_value.closure_id,
            expected_raw=_raw(lifecycle_value),
            label="closed reconciliation lifecycle record",
        ),
        _portable_record(
            records,
            role="CONSTRUCTION_LINEAGE",
            semantic_id=lineage.lineage_id,
            expected_raw=_raw(lineage),
            label="closed reconciliation lineage record",
        ),
        _portable_record(
            records,
            role="CONSTRUCTION_PLANNING_INPUT",
            semantic_id=planning_input.input_id,
            expected_raw=_raw(planning_input),
            label="closed reconciliation planning-input record",
        ),
        _portable_record(
            records,
            role="CONTROLLED_JOURNAL_CLOSURE",
            expected_raw=_raw(controlled_closure),
            label="closed reconciliation controlled closure record",
        ),
        _portable_record(
            records,
            role="INITIAL_ACQUISITION_SCHEDULE",
            semantic_id=schedule.schedule_id,
            expected_raw=_raw(schedule),
            label="closed reconciliation schedule record",
        ),
        _portable_record(
            records,
            role="LIVE_MODEL_EPOCH",
            semantic_id=final_epoch.model_epoch_id,
            expected_raw=_raw(final_epoch),
            label="closed reconciliation final epoch record",
        ),
        _portable_record(
            records,
            role="NUMERICAL_MODEL",
            semantic_id=final_model.model_id,
            expected_raw=_raw(final_model),
            label="closed reconciliation final model record",
        ),
        _portable_record(
            records,
            role="NUMERICAL_PLANNING_PROOF",
            semantic_id=final_proof.proof_id,
            expected_raw=_raw(final_proof),
            label="closed reconciliation final proof record",
        ),
        _portable_record(
            records,
            role="SIGNED_BATCH_JOURNAL_CLOSURE",
            semantic_id=controlled_closure.batch_closure.closure_id,
            expected_raw=_raw(controlled_closure.batch_closure),
            label="closed reconciliation signed batch closure record",
        ),
        _portable_record(
            records,
            role="SIGNED_CONTROL_CLOSURE",
            semantic_id=(
                controlled_closure.control_closure.control_closure_id
            ),
            expected_raw=_raw(controlled_closure.control_closure),
            label="closed reconciliation signed control closure record",
        ),
    )
    by_role = {item.role: item for item in values}
    if (
        set(by_role) != _SOURCE_ROLE_SET
        or len(by_role) != len(values)
    ):
        _fail("closed reconciliation source registry is incomplete")
    return tuple(by_role[role] for role in SOURCE_ROLE_ORDER)


_SOURCE_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionClosedReconciliationSourceBindingV2:
    _issuer: InitVar[object]
    target_record_id: str
    target_semantic_artifact_id: str
    source_records: tuple[tuple[str, str], ...]
    portable_bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    planning_input_replay_result_id: str
    schedule_id: str
    controlled_journal_record_id: str
    signed_control_closure_id: str
    signed_batch_closure_id: str
    final_model_epoch_id: str
    final_numerical_model_id: str
    final_proof_id: str
    lineage_id: str
    lifecycle_closure_id: str
    closed_planning_input_id: str
    producer_artifact_sha256: str
    producer_artifact_byte_count: int
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_BINDING_ISSUER:
            _fail("closed reconciliation source is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_binding_id",
            _hash("source_binding", self._payload()),
        )

    @property
    def source_dependency_record_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(record_id for _role, record_id in self.source_records)
        )

    def _validate(self) -> None:
        identifiers = (
            (self.target_record_id, "closed target record"),
            (
                self.target_semantic_artifact_id,
                "closed target semantic artifact",
            ),
            (self.portable_bundle_id, "closed portable bundle"),
            (self.occurrence_id, "closed occurrence"),
            (self.public_context_closure_id, "closed public context"),
            (
                self.planning_input_replay_result_id,
                "closed upstream replay",
            ),
            (self.schedule_id, "closed schedule"),
            (
                self.controlled_journal_record_id,
                "closed controlled journal record",
            ),
            (
                self.signed_control_closure_id,
                "closed signed control closure",
            ),
            (
                self.signed_batch_closure_id,
                "closed signed batch closure",
            ),
            (self.final_model_epoch_id, "closed final epoch"),
            (self.final_numerical_model_id, "closed final model"),
            (self.final_proof_id, "closed final proof"),
            (self.lineage_id, "closed lineage"),
            (self.lifecycle_closure_id, "closed lifecycle"),
            (self.closed_planning_input_id, "closed planning input"),
            (
                self.producer_artifact_sha256,
                "closed reconciliation bytes",
            ),
        )
        for value, label in identifiers:
            _cid(value, label)
        if (
            type(self.source_records) is not tuple
            or tuple(sorted(self.source_records)) != self.source_records
            or tuple(role for role, _record_id in self.source_records)
            != SOURCE_ROLE_ORDER
            or len({record_id for _role, record_id in self.source_records})
            != len(self.source_records)
            or any(
                role not in _SOURCE_ROLE_SET
                for role, _record_id in self.source_records
            )
            or any(
                role == "MULTIROUND_RESULT"
                for role, _record_id in self.source_records
            )
            or type(self.producer_artifact_byte_count) is not int
            or self.producer_artifact_byte_count <= 0
        ):
            _fail("closed reconciliation source binding is malformed")
        for _role, record_id in self.source_records:
            _cid(record_id, "closed reconciliation source record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_closed_reconciliation_"
                "source_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_record_id": self.target_record_id,
            "target_role": "CLOSED_RECONCILIATION",
            "target_semantic_artifact_id": (
                self.target_semantic_artifact_id
            ),
            "resolver_kind": (
                V075ConstructionClosedReconciliationResolverKindV2
                .CONSTRUCTION_CLOSED_RECONCILIATION_OWNER_REPLAY.value
            ),
            "source_records": [
                {"role": role, "record_id": record_id}
                for role, record_id in self.source_records
            ],
            "source_dependency_record_ids": list(
                self.source_dependency_record_ids
            ),
            "portable_bundle_id": self.portable_bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "planning_input_replay_result_id": (
                self.planning_input_replay_result_id
            ),
            "schedule_id": self.schedule_id,
            "controlled_journal_record_id": (
                self.controlled_journal_record_id
            ),
            "signed_control_closure_id": (
                self.signed_control_closure_id
            ),
            "signed_batch_closure_id": self.signed_batch_closure_id,
            "final_model_epoch_id": self.final_model_epoch_id,
            "final_numerical_model_id": self.final_numerical_model_id,
            "final_proof_id": self.final_proof_id,
            "lineage_id": self.lineage_id,
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "closed_planning_input_id": self.closed_planning_input_id,
            "producer_artifact_sha256": self.producer_artifact_sha256,
            "producer_artifact_byte_count": self.producer_artifact_byte_count,
            "multiround_result_used_as_source": False,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def binding_id(self) -> str:
        self._validate()
        if self._binding_id != _hash("source_binding", self._payload()):
            _fail("closed reconciliation source identity is stale")
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "closed reconciliation source binding is in-memory-only"
        )


def _build_source_binding(
    *,
    replayed: input_authority.V075PortableConstructionPlanningInputReplayV2,
    target_record: portable.V075PortableEvidenceArtifactRecordV2,
    source_records: tuple[
        portable.V075PortableEvidenceArtifactRecordV2, ...
    ],
    reconciliation: owner.V075ObserverSignedClosedReconciliationV2,
) -> V075ConstructionClosedReconciliationSourceBindingV2:
    by_role = {item.role: item for item in source_records}
    if (
        type(target_record)
        is not portable.V075PortableEvidenceArtifactRecordV2
        or any(
            type(item)
            is not portable.V075PortableEvidenceArtifactRecordV2
            for item in source_records
        )
        or tuple(by_role) != SOURCE_ROLE_ORDER
    ):
        _fail("closed reconciliation portable records are not exact")
    raw = _raw(reconciliation)
    return V075ConstructionClosedReconciliationSourceBindingV2(
        _SOURCE_BINDING_ISSUER,
        target_record.record_id,
        target_record.semantic_artifact_id,
        tuple((item.role, item.record_id) for item in source_records),
        replayed.bundle_id,
        replayed.occurrence_id,
        replayed.public_context_closure_id,
        replayed.result_id,
        reconciliation.planning_input.schedule_id,
        by_role["CONTROLLED_JOURNAL_CLOSURE"].record_id,
        reconciliation.controlled_closure.control_closure.control_closure_id,
        reconciliation.controlled_closure.batch_closure.closure_id,
        reconciliation.final_epoch.model_epoch_id,
        reconciliation.final_epoch.model.model_id,
        reconciliation.closed_proof.proof_id,
        reconciliation.lineage.lineage_id,
        reconciliation.lifecycle.closure_id,
        reconciliation.planning_input.input_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionClosedReconciliationTypedGraphV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    planning_input_replay: (
        input_authority.V075PortableConstructionPlanningInputReplayV2
    ) = field(repr=False)
    schedule: acquisition.V075InitialAcquisitionScheduleV2 = field(
        repr=False
    )
    controlled_closure: control.V075ControlledBatchJournalClosureV2 = field(
        repr=False
    )
    final_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(
        repr=False
    )
    final_model: planning.V075NumericalModelV2 = field(repr=False)
    final_proof: planning.V075NumericalPlanningProofV2 = field(repr=False)
    lineage: lineage_authority.V075BatchOccurrenceLineageV2 = field(
        repr=False
    )
    lifecycle: lifecycle.V075BatchOccurrenceLifecycleClosureV2 = field(
        repr=False
    )
    planning_input: planning.V075ConstructionPlanningInputV2 = field(
        repr=False
    )
    reconciliation: owner.V075ObserverSignedClosedReconciliationV2 = field(
        repr=False
    )
    target_record: portable.V075PortableEvidenceArtifactRecordV2 = field(
        repr=False
    )
    source_records: tuple[
        portable.V075PortableEvidenceArtifactRecordV2, ...
    ] = field(repr=False)
    source_binding: V075ConstructionClosedReconciliationSourceBindingV2
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("closed reconciliation graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "closed graph bundle"),
            (self.occurrence_id, "closed graph occurrence"),
            (self.public_context_closure_id, "closed graph context"),
        ):
            _cid(value, label)
        if (
            type(self.planning_input_replay)
            is not input_authority
            .V075PortableConstructionPlanningInputReplayV2
            or type(self.schedule)
            is not acquisition.V075InitialAcquisitionScheduleV2
            or type(self.controlled_closure)
            is not control.V075ControlledBatchJournalClosureV2
            or type(self.final_epoch)
            is not live_model.V075LiveIncrementalModelEpochV2
            or type(self.final_model) is not planning.V075NumericalModelV2
            or type(self.final_proof)
            is not planning.V075NumericalPlanningProofV2
            or type(self.lineage)
            is not lineage_authority.V075BatchOccurrenceLineageV2
            or type(self.lifecycle)
            is not lifecycle.V075BatchOccurrenceLifecycleClosureV2
            or type(self.planning_input)
            is not planning.V075ConstructionPlanningInputV2
            or type(self.reconciliation)
            is not owner.V075ObserverSignedClosedReconciliationV2
            or type(self.target_record)
            is not portable.V075PortableEvidenceArtifactRecordV2
            or type(self.source_records) is not tuple
            or any(
                type(item)
                is not portable.V075PortableEvidenceArtifactRecordV2
                for item in self.source_records
            )
            or type(self.source_binding)
            is not V075ConstructionClosedReconciliationSourceBindingV2
        ):
            _fail("closed reconciliation graph is malformed")
        _ = self.planning_input_replay.result_id
        _ = self.source_binding.binding_id
        (
            hardened,
            _m0_result,
            _m1b_result,
            _live_result,
            exact_schedule,
            exact_controlled_closure,
            exact_lineage,
            exact_lifecycle,
            _lifecycle_verification,
            exact_planning_input,
            epochs,
        ) = _exact_chain(self.planning_input_replay)
        reconciliation = self.reconciliation
        raw = _raw(reconciliation)
        exact_final_epoch = _exact_final_epoch(
            epochs=epochs,
            reconciliation_document=self.target_record.artifact_document,
        )
        exact_final_model, exact_final_proof = _exact_model_and_proof(
            hardened=hardened,
            final_epoch=exact_final_epoch,
            reconciliation_document=self.target_record.artifact_document,
        )
        source_by_role = {item.role: item for item in self.source_records}
        claimed_sources = dict(self.source_binding.source_records)
        if (
            len(source_by_role) != len(self.source_records)
            or tuple(source_by_role) != SOURCE_ROLE_ORDER
            or set(claimed_sources) != _SOURCE_ROLE_SET
            or any(
                claimed_sources[role] != source_by_role[role].record_id
                for role in SOURCE_ROLE_ORDER
            )
            or self.planning_input_replay.bundle_id != self.bundle_id
            or self.planning_input_replay.occurrence_id != self.occurrence_id
            or self.planning_input_replay.public_context_closure_id
            != self.public_context_closure_id
            or self.source_binding.portable_bundle_id != self.bundle_id
            or self.source_binding.occurrence_id != self.occurrence_id
            or self.source_binding.public_context_closure_id
            != self.public_context_closure_id
            or self.source_binding.planning_input_replay_result_id
            != self.planning_input_replay.result_id
            or self.target_record.role != "CLOSED_RECONCILIATION"
            or self.target_record.record_id
            != self.source_binding.target_record_id
            or self.target_record.semantic_artifact_id
            != reconciliation.reconciliation_id
            or self.target_record.semantic_artifact_id
            != self.source_binding.target_semantic_artifact_id
            or self.target_record.canonical_artifact_bytes != raw
            or self.source_binding.producer_artifact_sha256
            != hashlib.sha256(raw).hexdigest()
            or self.source_binding.producer_artifact_byte_count != len(raw)
            or self.schedule is not exact_schedule
            or self.controlled_closure is not exact_controlled_closure
            or self.final_epoch is not exact_final_epoch
            or self.final_model is not exact_final_model
            or self.final_proof is not exact_final_proof
            or self.lineage is not exact_lineage
            or self.lifecycle is not exact_lifecycle
            or self.planning_input is not exact_planning_input
        ):
            _fail("closed reconciliation graph crossed portable identities")
        upstream_graph = self.planning_input_replay.typed_graph
        if (
            self.schedule is not upstream_graph.schedule
            or self.lineage
            is not (
                upstream_graph.private_replay_result.typed_graph
                .construction_lineage
            )
            or self.lifecycle
            is not (
                upstream_graph.private_replay_result.typed_graph
                .construction_lifecycle
            )
            or self.planning_input
            is not upstream_graph.construction_planning_input
            or reconciliation.final_epoch.model_epoch_id
            != self.final_epoch.model_epoch_id
            or _raw(reconciliation.final_epoch) != _raw(self.final_epoch)
            or _raw(reconciliation.controlled_closure)
            != _raw(self.controlled_closure)
            or reconciliation.lineage.lineage_id != self.lineage.lineage_id
            or _raw(reconciliation.lineage) != _raw(self.lineage)
            or reconciliation.lifecycle.closure_id
            != self.lifecycle.closure_id
            or _raw(reconciliation.lifecycle) != _raw(self.lifecycle)
            or _raw(reconciliation.planning_input)
            != _raw(self.planning_input)
            or reconciliation.planning_input.input_id
            != self.planning_input.input_id
            or _raw(reconciliation.closed_proof) != _raw(self.final_proof)
            or reconciliation.closed_proof.proof_id
            != self.final_proof.proof_id
            or _raw(self.final_epoch.model) != _raw(self.final_model)
            or _raw(self.final_epoch.proof) != _raw(self.final_proof)
        ):
            _fail("owner replay crossed its exact typed producer objects")
        expected_raw_by_role = {
            "CONSTRUCTION_LIFECYCLE": _raw(self.lifecycle),
            "CONSTRUCTION_LINEAGE": _raw(self.lineage),
            "CONSTRUCTION_PLANNING_INPUT": _raw(self.planning_input),
            "CONTROLLED_JOURNAL_CLOSURE": _raw(self.controlled_closure),
            "INITIAL_ACQUISITION_SCHEDULE": _raw(self.schedule),
            "LIVE_MODEL_EPOCH": _raw(self.final_epoch),
            "NUMERICAL_MODEL": _raw(self.final_model),
            "NUMERICAL_PLANNING_PROOF": _raw(self.final_proof),
            "SIGNED_BATCH_JOURNAL_CLOSURE": _raw(
                self.controlled_closure.batch_closure
            ),
            "SIGNED_CONTROL_CLOSURE": _raw(
                self.controlled_closure.control_closure
            ),
        }
        expected_semantic_by_role = {
            "CONSTRUCTION_LIFECYCLE": self.lifecycle.closure_id,
            "CONSTRUCTION_LINEAGE": self.lineage.lineage_id,
            "CONSTRUCTION_PLANNING_INPUT": self.planning_input.input_id,
            "INITIAL_ACQUISITION_SCHEDULE": self.schedule.schedule_id,
            "LIVE_MODEL_EPOCH": self.final_epoch.model_epoch_id,
            "NUMERICAL_MODEL": self.final_model.model_id,
            "NUMERICAL_PLANNING_PROOF": self.final_proof.proof_id,
            "SIGNED_BATCH_JOURNAL_CLOSURE": (
                self.controlled_closure.batch_closure.closure_id
            ),
            "SIGNED_CONTROL_CLOSURE": (
                self.controlled_closure.control_closure.control_closure_id
            ),
        }
        if any(
            source_by_role[role].canonical_artifact_bytes
            != expected_raw_by_role[role]
            or (
                role in expected_semantic_by_role
                and source_by_role[role].semantic_artifact_id
                != expected_semantic_by_role[role]
            )
            for role in SOURCE_ROLE_ORDER
        ):
            _fail("closed reconciliation source record was transplanted")
        controlled_record = source_by_role["CONTROLLED_JOURNAL_CLOSURE"]
        if (
            self.source_binding.schedule_id != self.schedule.schedule_id
            or self.source_binding.controlled_journal_record_id
            != controlled_record.record_id
            or self.source_binding.signed_control_closure_id
            != self.controlled_closure.control_closure.control_closure_id
            or self.source_binding.signed_batch_closure_id
            != self.controlled_closure.batch_closure.closure_id
            or self.source_binding.final_model_epoch_id
            != self.final_epoch.model_epoch_id
            or self.source_binding.final_numerical_model_id
            != self.final_model.model_id
            or self.source_binding.final_proof_id
            != self.final_proof.proof_id
            or self.source_binding.lineage_id != self.lineage.lineage_id
            or self.source_binding.lifecycle_closure_id
            != self.lifecycle.closure_id
            or self.source_binding.closed_planning_input_id
            != self.planning_input.input_id
        ):
            _fail("closed reconciliation source claim changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_closed_reconciliation_"
                "typed_graph.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "planning_input_replay_result_id": (
                self.planning_input_replay.result_id
            ),
            "schedule_id": self.schedule.schedule_id,
            "controlled_journal_record_id": (
                self.source_binding.controlled_journal_record_id
            ),
            "signed_control_closure_id": (
                self.controlled_closure.control_closure.control_closure_id
            ),
            "signed_batch_closure_id": (
                self.controlled_closure.batch_closure.closure_id
            ),
            "final_model_epoch_id": self.final_epoch.model_epoch_id,
            "final_numerical_model_id": self.final_model.model_id,
            "final_proof_id": self.final_proof.proof_id,
            "construction_lineage_id": self.lineage.lineage_id,
            "construction_lifecycle_id": self.lifecycle.closure_id,
            "closed_planning_input_id": self.planning_input.input_id,
            "closed_reconciliation_id": (
                self.reconciliation.reconciliation_id
            ),
            "target_record_id": self.target_record.record_id,
            "ordered_source_record_ids": [
                item.record_id for item in self.source_records
            ],
            "source_binding_id": self.source_binding.binding_id,
            "owner_only_reconciliation_producer_used": True,
            "planning_input_bytes_equal_contract_179": True,
            "final_epoch_is_unique_maximum": True,
            "all_owner_components_portable_byte_exact": True,
            "multiround_result_used_as_source": False,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
        }

    @property
    def graph_id(self) -> str:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._payload()):
            _fail("closed reconciliation graph identity is stale")
        return self._graph_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "typed_graph_id": self.graph_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("closed reconciliation graph is in-memory-only")


@dataclass(frozen=True, slots=True)
class V075ConstructionClosedReconciliationDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    source_binding_id: str | None
    resolver_kind: V075ConstructionClosedReconciliationResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    authority_scope: V075ConstructionClosedReconciliationAuthorityScopeV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int

    def __post_init__(self) -> None:
        _cid(self.record_id, "closed dependency node")
        sequences = (
            self.portable_declared_dependency_record_ids,
            self.authority_local_semantic_dependency_record_ids,
            self.effective_dependency_record_ids,
            self.unresolved_frontier_record_ids,
            self.unresolved_frontier_roles,
        )
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or any(
                type(values) is not tuple
                or tuple(sorted(set(values))) != values
                for values in sequences
            )
            or set(self.effective_dependency_record_ids)
            != set(self.portable_declared_dependency_record_ids)
            | set(self.authority_local_semantic_dependency_record_ids)
            or type(self.resolver_kind)
            is not V075ConstructionClosedReconciliationResolverKindV2
            or type(self.local_semantic_authority_resolved) is not bool
            or type(self.semantically_resolved) is not bool
            or type(self.authority_scope)
            is not V075ConstructionClosedReconciliationAuthorityScopeV2
            or type(self.dependency_depth) is not int
            or not 0 < self.dependency_depth <= MAX_DEPENDENCY_NODES
            or self.semantically_resolved
            != (
                self.authority_scope
                is not V075ConstructionClosedReconciliationAuthorityScopeV2
                .UNRESOLVED
            )
            or (
                self.semantically_resolved
                and (
                    self.unresolved_frontier_record_ids
                    or self.unresolved_frontier_roles
                )
            )
            or (
                not self.semantically_resolved
                and not self.unresolved_frontier_record_ids
            )
        ):
            _fail("closed reconciliation dependency node is malformed")
        if self.source_binding_id is not None:
            _cid(self.source_binding_id, "closed dependency source")
        for value in (
            *self.effective_dependency_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "closed reconciliation dependency edge")

    def to_document(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "portable_declared_dependency_record_ids": list(
                self.portable_declared_dependency_record_ids
            ),
            "authority_local_semantic_dependency_record_ids": list(
                self.authority_local_semantic_dependency_record_ids
            ),
            "effective_dependency_record_ids": list(
                self.effective_dependency_record_ids
            ),
            "source_binding_id": self.source_binding_id,
            "resolver_kind": self.resolver_kind.value,
            "local_semantic_authority_resolved": (
                self.local_semantic_authority_resolved
            ),
            "semantically_resolved": self.semantically_resolved,
            "authority_scope": self.authority_scope.value,
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
            "dependency_depth": self.dependency_depth,
        }


def _scope_from_upstream(
    value: Any,
) -> V075ConstructionClosedReconciliationAuthorityScopeV2:
    raw = getattr(getattr(value, "authority_scope", None), "value", None)
    try:
        return V075ConstructionClosedReconciliationAuthorityScopeV2(raw)
    except ValueError:
        _fail("closed reconciliation upstream authority scope is unknown")


def _iterative_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    source_binding: V075ConstructionClosedReconciliationSourceBindingV2,
) -> tuple[V075ConstructionClosedReconciliationDependencyNodeV2, ...]:
    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or len(upstream_nodes) > MAX_DEPENDENCY_NODES
    ):
        _fail("closed reconciliation requires one bounded exact DAG")
    if (
        type(source_binding)
        is not V075ConstructionClosedReconciliationSourceBindingV2
    ):
        _fail("closed reconciliation source binding is not exact")
    _ = source_binding.binding_id
    by_id: dict[str, Any] = {}
    for expected_index, item in enumerate(upstream_nodes):
        portable_lane = tuple(
            item.portable_declared_dependency_record_ids
        )
        local_lane = tuple(
            item.authority_local_semantic_dependency_record_ids
        )
        effective_lane = tuple(item.effective_dependency_record_ids)
        if (
            item.record_index != expected_index
            or item.record_id in by_id
            or tuple(sorted(set(portable_lane))) != portable_lane
            or tuple(sorted(set(local_lane))) != local_lane
            or tuple(sorted(set(effective_lane))) != effective_lane
            or set(effective_lane)
            != set(portable_lane) | set(local_lane)
        ):
            _fail("closed reconciliation upstream DAG lanes are malformed")
        by_id[item.record_id] = item
    all_ids = set(by_id)
    role_by_id = {
        record_id: item.role for record_id, item in by_id.items()
    }
    closed = tuple(
        record_id
        for record_id, role in role_by_id.items()
        if role == "CLOSED_RECONCILIATION"
    )
    if closed != (source_binding.target_record_id,):
        _fail("closed reconciliation source target is transplanted")
    source_pairs = dict(source_binding.source_records)
    if (
        set(source_pairs) != _SOURCE_ROLE_SET
        or any(
            source_pairs[role] not in all_ids
            or role_by_id[source_pairs[role]] != role
            for role in SOURCE_ROLE_ORDER
        )
        or any(
            role_by_id[record_id] == "MULTIROUND_RESULT"
            for record_id in source_binding.source_dependency_record_ids
        )
    ):
        _fail("closed reconciliation source registry is transplanted")

    portable_by_id: dict[str, tuple[str, ...]] = {}
    local_by_id: dict[str, tuple[str, ...]] = {}
    effective_by_id: dict[str, tuple[str, ...]] = {}
    local_resolved_by_id: dict[str, bool] = {}
    resolver_by_id: dict[
        str, V075ConstructionClosedReconciliationResolverKindV2
    ] = {}
    source_id_by_id: dict[str, str | None] = {}
    upstream_scope_by_id: dict[
        str, V075ConstructionClosedReconciliationAuthorityScopeV2
    ] = {}
    for record_id, upstream in by_id.items():
        portable_dependencies = tuple(
            upstream.portable_declared_dependency_record_ids
        )
        inherited_local = tuple(
            upstream.authority_local_semantic_dependency_record_ids
        )
        role = role_by_id[record_id]
        if role == "CLOSED_RECONCILIATION":
            added = source_binding.source_dependency_record_ids
            local_resolved = True
            resolver = (
                V075ConstructionClosedReconciliationResolverKindV2
                .CONSTRUCTION_CLOSED_RECONCILIATION_OWNER_REPLAY
            )
            source_id = source_binding.binding_id
        else:
            added = ()
            local_resolved = bool(
                upstream.local_semantic_authority_resolved
            )
            resolver = (
                V075ConstructionClosedReconciliationResolverKindV2
                .UPSTREAM_CONSTRUCTION_PLANNING_INPUT_REPLAY
                if local_resolved
                else V075ConstructionClosedReconciliationResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
            )
            source_id = upstream.source_binding_id
        local_dependencies = tuple(
            sorted(set(inherited_local) | set(added))
        )
        effective_dependencies = tuple(
            sorted(set(portable_dependencies) | set(local_dependencies))
        )
        if (
            record_id in effective_dependencies
            or any(item not in all_ids for item in effective_dependencies)
            or (
                role == "CLOSED_RECONCILIATION"
                and any(
                    role_by_id[item] == "MULTIROUND_RESULT"
                    for item in effective_dependencies
                )
            )
        ):
            _fail("closed reconciliation dependency edge is foreign")
        portable_by_id[record_id] = portable_dependencies
        local_by_id[record_id] = local_dependencies
        effective_by_id[record_id] = effective_dependencies
        local_resolved_by_id[record_id] = local_resolved
        resolver_by_id[record_id] = resolver
        source_id_by_id[record_id] = source_id
        upstream_scope_by_id[record_id] = _scope_from_upstream(upstream)

    indegree = {
        record_id: len(dependencies)
        for record_id, dependencies in effective_by_id.items()
    }
    successors = {record_id: [] for record_id in all_ids}
    for record_id, dependencies in effective_by_id.items():
        for dependency in dependencies:
            successors[dependency].append(record_id)
    ready = [
        (by_id[record_id].record_index, record_id)
        for record_id, degree in indegree.items()
        if degree == 0
    ]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        _index, record_id = heapq.heappop(ready)
        order.append(record_id)
        for successor in successors[record_id]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(
                    ready,
                    (by_id[successor].record_index, successor),
                )
    if len(order) != len(all_ids):
        _fail("closed reconciliation effective DAG contains a cycle")

    scopes = V075ConstructionClosedReconciliationAuthorityScopeV2
    resolved: dict[str, bool] = {}
    scope_by_id: dict[
        str, V075ConstructionClosedReconciliationAuthorityScopeV2
    ] = {}
    frontiers: dict[str, tuple[str, ...]] = {}
    depths: dict[str, int] = {}
    nodes: dict[
        str, V075ConstructionClosedReconciliationDependencyNodeV2
    ] = {}
    for record_id in order:
        dependencies = effective_by_id[record_id]
        is_resolved = local_resolved_by_id[record_id] and all(
            resolved[item] for item in dependencies
        )
        role = role_by_id[record_id]
        inherited_scope = upstream_scope_by_id[record_id]
        if not is_resolved:
            scope = scopes.UNRESOLVED
        elif role == "CLOSED_RECONCILIATION":
            scope = scopes.FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY
        elif inherited_scope is not scopes.UNRESOLVED:
            scope = inherited_scope
        elif any(
            scope_by_id[item] is not scopes.FULL_PUBLIC
            for item in dependencies
        ):
            scope = scopes.FULL_CONSTRUCTION_TRANSITIVE
        else:
            scope = scopes.FULL_PUBLIC
        if is_resolved:
            frontier: tuple[str, ...] = ()
        elif not local_resolved_by_id[record_id]:
            frontier = (record_id,)
        else:
            unresolved: set[str] = set()
            for dependency in dependencies:
                unresolved.update(frontiers[dependency])
            frontier = tuple(sorted(unresolved))
            if not frontier:
                _fail("unresolved closed node lacks exact frontier")
        depth = 1 + max(
            (depths[item] for item in dependencies),
            default=0,
        )
        if depth > MAX_DEPENDENCY_NODES:
            _fail("closed reconciliation dependency depth exceeded")
        node = V075ConstructionClosedReconciliationDependencyNodeV2(
            record_id,
            by_id[record_id].record_index,
            role,
            portable_by_id[record_id],
            local_by_id[record_id],
            effective_by_id[record_id],
            source_id_by_id[record_id],
            resolver_by_id[record_id],
            local_resolved_by_id[record_id],
            is_resolved,
            scope,
            frontier,
            tuple(sorted({role_by_id[item] for item in frontier})),
            depth,
        )
        nodes[record_id] = node
        resolved[record_id] = is_resolved
        scope_by_id[record_id] = scope
        frontiers[record_id] = frontier
        depths[record_id] = depth
    return tuple(
        nodes[item.record_id]
        for item in sorted(
            upstream_nodes,
            key=lambda value: value.record_index,
        )
    )


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionClosedReconciliationDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    planning_input_replay: (
        input_authority.V075PortableConstructionPlanningInputReplayV2
    ) = field(repr=False)
    source_binding: V075ConstructionClosedReconciliationSourceBindingV2
    nodes: tuple[
        V075ConstructionClosedReconciliationDependencyNodeV2, ...
    ]
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("closed reconciliation DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "closed reconciliation DAG bundle")
        _cid(self.typed_graph_id, "closed reconciliation DAG graph")
        if (
            type(self.planning_input_replay)
            is not input_authority
            .V075PortableConstructionPlanningInputReplayV2
            or type(self.source_binding)
            is not V075ConstructionClosedReconciliationSourceBindingV2
            or type(self.nodes) is not tuple
            or not self.nodes
            or any(
                type(item)
                is not V075ConstructionClosedReconciliationDependencyNodeV2
                for item in self.nodes
            )
        ):
            _fail("closed reconciliation DAG is malformed")
        expected = _iterative_dependency_nodes(
            upstream_nodes=self.planning_input_replay.dependency_dag.nodes,
            source_binding=self.source_binding,
        )
        if tuple(item.to_document() for item in self.nodes) != tuple(
            item.to_document() for item in expected
        ):
            _fail("closed reconciliation DAG is stale")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_closed_reconciliation_"
                "dependency_dag.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "typed_graph_id": self.typed_graph_id,
            "planning_input_replay_result_id": (
                self.planning_input_replay.result_id
            ),
            "source_binding_id": self.source_binding.binding_id,
            "nodes": [item.to_document() for item in self.nodes],
            "portable_declared_dependency_lane_preserved": True,
            "authority_local_dependency_lane_preserved": True,
            "effective_dependency_lane_recomputed": True,
            "authority_scope_lattice_propagated": True,
            "multiround_reverse_dependency_forbidden": True,
            "iterative_kahn_walk_used": True,
            "maximum_dependency_nodes": MAX_DEPENDENCY_NODES,
        }

    @property
    def dag_id(self) -> str:
        self._validate()
        if self._dag_id != _hash("dependency_dag", self._payload()):
            _fail("closed reconciliation DAG identity is stale")
        return self._dag_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "dependency_dag_id": self.dag_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("closed reconciliation DAG is in-memory-only")


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionClosedReconciliationRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    dependency_dag_id: str
    role: str
    record_ids: tuple[str, ...]
    status: V075ConstructionClosedReconciliationRoleStatusV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("closed reconciliation closure is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "closed role closure bundle")
        _cid(self.dependency_dag_id, "closed role closure DAG")
        if (
            self.role not in _ROLE_SET
            or type(self.record_ids) is not tuple
            or len(self.record_ids) != 1
            or type(self.status)
            is not V075ConstructionClosedReconciliationRoleStatusV2
            or tuple(sorted(set(self.unresolved_frontier_record_ids)))
            != self.unresolved_frontier_record_ids
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
            or (
                self.status
                is V075ConstructionClosedReconciliationRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
                and not self.unresolved_frontier_record_ids
            )
            or (
                self.status
                is not V075ConstructionClosedReconciliationRoleStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
                and (
                    self.unresolved_frontier_record_ids
                    or self.unresolved_frontier_roles
                )
            )
        ):
            _fail("closed reconciliation role closure is malformed")
        _cid(self.record_ids[0], "closed role closure record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_closed_reconciliation_"
                "role_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "dependency_dag_id": self.dependency_dag_id,
            "role": self.role,
            "record_ids": list(self.record_ids),
            "status": self.status.value,
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
        }

    @property
    def closure_id(self) -> str:
        self._validate()
        if self._closure_id != _hash("role_closure", self._payload()):
            _fail("closed reconciliation role closure identity is stale")
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "closed reconciliation role closure is in-memory-only"
        )


def _build_role_closures(
    *,
    bundle_id: str,
    dependency_dag_id: str,
    nodes: tuple[
        V075ConstructionClosedReconciliationDependencyNodeV2, ...
    ],
) -> tuple[V075ConstructionClosedReconciliationRoleClosureV2, ...]:
    result = []
    statuses = V075ConstructionClosedReconciliationRoleStatusV2
    scopes = V075ConstructionClosedReconciliationAuthorityScopeV2
    for role in ROLE_ORDER:
        members = tuple(item for item in nodes if item.role == role)
        if len(members) != 1:
            _fail(f"closed reconciliation role {role} is not singleton")
        member = members[0]
        if role == "CONSTRUCTION_PLANNING_INPUT":
            status = statuses.FULL_CONSTRUCTION_COMPILER_REPLAY
            if (
                not member.semantically_resolved
                or member.authority_scope
                is not scopes.FULL_CONSTRUCTION_COMPILER_REPLAY
            ):
                _fail("existing planning-input authority scope changed")
        elif role == "CLOSED_RECONCILIATION":
            status = (
                statuses
                .FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY
            )
            if (
                not member.semantically_resolved
                or member.authority_scope
                is not scopes
                .FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY
            ):
                _fail("closed reconciliation did not close")
        else:
            status = statuses.STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            if (
                member.semantically_resolved
                or member.authority_scope is not scopes.UNRESOLVED
                or member.unresolved_frontier_record_ids
                != (member.record_id,)
                or member.unresolved_frontier_roles != (role,)
            ):
                _fail("MULTIROUND_RESULT was falsely closed")
        result.append(
            V075ConstructionClosedReconciliationRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                dependency_dag_id,
                role,
                (member.record_id,),
                status,
                member.unresolved_frontier_record_ids,
                member.unresolved_frontier_roles,
            )
        )
    return tuple(result)


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableConstructionClosedReconciliationReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075ConstructionClosedReconciliationTypedGraphV2 = field(
        repr=False
    )
    dependency_dag: (
        V075ConstructionClosedReconciliationDependencyDAGV2
    ) = field(repr=False)
    role_closures: tuple[
        V075ConstructionClosedReconciliationRoleClosureV2, ...
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("closed reconciliation result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "closed result bundle"),
            (self.occurrence_id, "closed result occurrence"),
            (self.public_context_closure_id, "closed result context"),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph)
            is not V075ConstructionClosedReconciliationTypedGraphV2
            or type(self.dependency_dag)
            is not V075ConstructionClosedReconciliationDependencyDAGV2
            or type(self.role_closures) is not tuple
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or any(
                type(item)
                is not V075ConstructionClosedReconciliationRoleClosureV2
                for item in self.role_closures
            )
            or self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.typed_graph_id
            != self.typed_graph.graph_id
            or self.dependency_dag.planning_input_replay
            is not self.typed_graph.planning_input_replay
            or self.dependency_dag.source_binding
            is not self.typed_graph.source_binding
        ):
            _fail("closed reconciliation result is malformed")
        expected = _build_role_closures(
            bundle_id=self.bundle_id,
            dependency_dag_id=self.dependency_dag.dag_id,
            nodes=self.dependency_dag.nodes,
        )
        if tuple(item.to_document() for item in self.role_closures) != tuple(
            item.to_document() for item in expected
        ):
            _fail("closed reconciliation closures are stale")

    def _payload(self) -> dict[str, Any]:
        unresolved = tuple(
            sorted(
                {
                    role
                    for item in self.dependency_dag.nodes
                    if not item.semantically_resolved
                    for role in item.unresolved_frontier_roles
                }
            )
        )
        return {
            "schema": (
                "acfqp.v075_portable_construction_closed_reconciliation_"
                "replay.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "typed_graph_id": self.typed_graph.graph_id,
            "dependency_dag_id": self.dependency_dag.dag_id,
            "closed_reconciliation_id": (
                self.typed_graph.reconciliation.reconciliation_id
            ),
            "role_statuses": {
                item.role: item.status.value for item in self.role_closures
            },
            "role_closure_ids": [
                item.closure_id for item in self.role_closures
            ],
            "remaining_unresolved_frontier_roles": list(unresolved),
            "raw_contract_179_replayed_first": True,
            "owner_closed_reconciliation_replayed": True,
            "aggregate_currentness_requires_explicit_raw_replay": True,
            "no_argument_currentness_claim_available": False,
            "private_values_retained": False,
            "private_values_serialized": False,
            "private_values_directly_hashed_by_this_authority": False,
            "private_secret_digest_emitted": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "portable_semantic_registry_complete": False,
            "fresh_heldout_accessed": False,
            "accounting_gate_passed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def result_id(self) -> str:
        self._validate()
        if self._result_id != _hash("aggregate", self._payload()):
            _fail("closed reconciliation result identity is stale")
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}

    def assert_current(
        self,
        *,
        repository_root: str | Path,
        portable_bundle_bytes: bytes,
        public_context_closure_bytes: bytes,
        private_generation_seed: bytes,
        private_salt: bytes,
    ) -> None:
        replayed = (
            replay_v075_portable_construction_closed_reconciliation_v2(
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        if replayed.to_document() != self.to_document():
            _fail("closed reconciliation currentness check changed")

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "closed reconciliation replay is in-memory-only"
        )


def replay_v075_portable_construction_closed_reconciliation_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
    private_generation_seed: bytes,
    private_salt: bytes,
) -> V075PortableConstructionClosedReconciliationReplayV2:
    """Replay raw 1.79 first, then the sole owner reconciliation producer."""

    # This must remain the first operation.  No argument is inspected,
    # type-checked, parsed, hashed, or retained before raw 1.79 succeeds.
    try:
        upstream = (
            input_authority
            .replay_v075_portable_construction_planning_input_v2(
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
                private_generation_seed=private_generation_seed,
                private_salt=private_salt,
            )
        )
        (
            hardened,
            _m0_result,
            _m1b_result,
            _live_result,
            schedule,
            controlled_closure,
            lineage,
            lifecycle_value,
            _lifecycle_verification,
            planning_input,
            epochs,
        ) = _exact_chain(upstream)
        bundle = (
            portable.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
        if (
            type(bundle)
            is not portable.V075PortableOccurrenceEvidenceBundleV2
            or bundle.bundle_id != upstream.bundle_id
            or bundle.occurrence_id != upstream.occurrence_id
        ):
            _fail(_REPLAY_MISMATCH)
        target = _portable_record(
            bundle.records,
            role="CLOSED_RECONCILIATION",
            label="portable closed reconciliation target",
        )
        target_document = target.artifact_document
        final_epoch = _exact_final_epoch(
            epochs=epochs,
            reconciliation_document=target_document,
        )
        final_model, final_proof = _exact_model_and_proof(
            hardened=hardened,
            final_epoch=final_epoch,
            reconciliation_document=target_document,
        )
        if (
            target_document.get("controlled_journal_closure_id")
            != controlled_closure.control_closure.control_closure_id
            or target_document.get("batch_closure_id")
            != controlled_closure.batch_closure.closure_id
            or target_document.get("lineage_id") != lineage.lineage_id
            or target_document.get("lifecycle_closure_id")
            != lifecycle_value.closure_id
            or target_document.get("closed_planning_input_id")
            != planning_input.input_id
        ):
            _fail(_REPLAY_MISMATCH)
        reconciliation = (
            owner.freeze_v075_construction_closed_reconciliation_v2(
                repository_root=repository_root,
                schedule=schedule,
                final_epoch=final_epoch,
                controlled_closure=controlled_closure,
                lineage=lineage,
                lifecycle=lifecycle_value,
            )
        )
        if (
            type(reconciliation)
            is not owner.V075ObserverSignedClosedReconciliationV2
            or reconciliation.reconciliation_id
            != target.semantic_artifact_id
            or _raw(reconciliation) != target.canonical_artifact_bytes
            or reconciliation.planning_input.input_id
            != planning_input.input_id
            or _raw(reconciliation.planning_input)
            != _raw(planning_input)
            or reconciliation.closed_proof.proof_id
            != final_proof.proof_id
            or _raw(reconciliation.closed_proof) != _raw(final_proof)
            or reconciliation.final_epoch.model_epoch_id
            != final_epoch.model_epoch_id
            or _raw(reconciliation.final_epoch) != _raw(final_epoch)
            or _raw(reconciliation.controlled_closure)
            != _raw(controlled_closure)
            or reconciliation.lineage.lineage_id != lineage.lineage_id
            or _raw(reconciliation.lineage) != _raw(lineage)
            or reconciliation.lifecycle.closure_id
            != lifecycle_value.closure_id
            or _raw(reconciliation.lifecycle) != _raw(lifecycle_value)
        ):
            _fail(_REPLAY_MISMATCH)
        source_records = _exact_portable_sources(
            records=bundle.records,
            schedule=schedule,
            controlled_closure=controlled_closure,
            final_epoch=final_epoch,
            final_model=final_model,
            final_proof=final_proof,
            lineage=lineage,
            lifecycle_value=lifecycle_value,
            planning_input=planning_input,
        )
        source_binding = _build_source_binding(
            replayed=upstream,
            target_record=target,
            source_records=source_records,
            reconciliation=reconciliation,
        )
        graph = V075ConstructionClosedReconciliationTypedGraphV2(
            _TYPED_GRAPH_ISSUER,
            upstream.bundle_id,
            upstream.occurrence_id,
            upstream.public_context_closure_id,
            upstream,
            schedule,
            controlled_closure,
            final_epoch,
            final_model,
            final_proof,
            lineage,
            lifecycle_value,
            planning_input,
            reconciliation,
            target,
            source_records,
            source_binding,
        )
        nodes = _iterative_dependency_nodes(
            upstream_nodes=upstream.dependency_dag.nodes,
            source_binding=source_binding,
        )
        dag = V075ConstructionClosedReconciliationDependencyDAGV2(
            _DAG_ISSUER,
            upstream.bundle_id,
            graph.graph_id,
            upstream,
            source_binding,
            nodes,
        )
        closures = _build_role_closures(
            bundle_id=upstream.bundle_id,
            dependency_dag_id=dag.dag_id,
            nodes=nodes,
        )
        result = V075PortableConstructionClosedReconciliationReplayV2(
            _RESULT_ISSUER,
            upstream.bundle_id,
            upstream.occurrence_id,
            upstream.public_context_closure_id,
            graph,
            dag,
            closures,
        )
        if len(canonical_json_bytes(result.to_document())) > MAX_OUTPUT_BYTES:
            _fail("closed reconciliation public summary exceeds cap")
        return result
    except Exception:
        # Raw/private mismatch details are intentionally suppressed so secret
        # values cannot escape through nested exception text or repr output.
        raise (
            V075PortableConstructionClosedReconciliationV2InvariantViolation(
                _REPLAY_MISMATCH
            )
        ) from None


def assert_v075_portable_construction_closed_reconciliation_production_gate_v2(
    result: V075PortableConstructionClosedReconciliationReplayV2,
) -> NoReturn:
    if (
        type(result)
        is not V075PortableConstructionClosedReconciliationReplayV2
    ):
        _fail("closed reconciliation gate rejects duck-typed results")
    _ = result.result_id
    raise V075PortableConstructionClosedReconciliationProductionV2NotReady(
        "contract 1.80 is construction-only; MULTIROUND_RESULT, source/code "
        "provenance, accounting, and production gates remain open"
    )
