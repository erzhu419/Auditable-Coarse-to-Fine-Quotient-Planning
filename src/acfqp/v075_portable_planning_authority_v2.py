"""Public M2 numerical planning authority for the V0-075 portable graph.

This construction-only cut begins with the hardened contract-1.76 dynamic
child proposal replay.  It closes the numerical-model and numerical-proof
producer semantics from exact public live epochs:

* every model is tied to its occurrence, controlled-prefix verification, and
  complete live-row-source registry; and
* every proof is recomputed by the public exact numerical planner.

The construction planning input is registered but deliberately remains
unresolved.  Contract 1.73 exposes only its public lineage document, while the
producer compiler requires an issuer-owned typed construction lineage.  This
module never fabricates that type, never consumes the private closure
verification, and never calls the construction-input compiler.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import heapq
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_portable_dynamic_child_proposal_authority_v2 as m2_child
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.77.0"
PROFILE_KEY = "v075_portable_planning_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = False
CODE_PROVENANCE_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
PRIVATE_INPUT_CHANNELS_ALLOWED = False
PRIVATE_REPLAY_PERFORMED = False
B3_INPUT_ALLOWED = False
K7_INPUT_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
J0_ACCESS_ALLOWED = False
SIGNER_INPUT_ALLOWED = False
OBSERVER_ACCESS_ALLOWED = False
OBSERVER_INPUT_ALLOWED = False
WORKER_ACCESS_ALLOWED = False
WORKER_INPUT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_M2_NUMERICAL_PLANNING_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = (
    "M2_NUMERICAL_MODEL_AND_PROOF_REPLAYED_"
    "CONSTRUCTION_PLANNING_INPUT_AUTHORITY_UNRESOLVED"
)
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_DEPENDENCY_NODES = 4096

ROLE_ORDER = (
    "NUMERICAL_MODEL",
    "NUMERICAL_PLANNING_PROOF",
    "CONSTRUCTION_PLANNING_INPUT",
)
_ROLE_SET = frozenset(ROLE_ORDER)
_FULL_PUBLIC_ROLES = frozenset(ROLE_ORDER[:2])
_UNRESOLVED_ROLES = frozenset(ROLE_ORDER[2:])
PROPAGATED_ROLE_ORDER = (
    "LIVE_MODEL_EPOCH",
    "DYNAMIC_CHILD_CAUSAL_EDGE",
    "DYNAMIC_CHILD_STATE",
    "DYNAMIC_CHILD_CLOSURE",
    "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
)

_ROLE_SCHEMA = MappingProxyType(
    {
        "NUMERICAL_MODEL": (
            "acfqp.v075_batch_planning_numerical_model.v2"
        ),
        "NUMERICAL_PLANNING_PROOF": (
            "acfqp.v075_batch_planning_numerical_proof.v2"
        ),
        "CONSTRUCTION_PLANNING_INPUT": (
            "acfqp.v075_batch_planning_construction_input.v2"
        ),
    }
)
_ROLE_ID_FIELD = MappingProxyType(
    {
        "NUMERICAL_MODEL": "model_id",
        "NUMERICAL_PLANNING_PROOF": "proof_id",
        "CONSTRUCTION_PLANNING_INPUT": "input_id",
    }
)
_SOURCE_ROLE_SCHEMA = MappingProxyType(
    {
        "OCCURRENCE_IDENTITY": "acfqp.v075_batch_native_occurrence.v1",
        "OPEN_CONTROLLED_PREFIX_VERIFICATION": (
            "acfqp.v075_open_controlled_batch_prefix_verification.v2"
        ),
        "LIVE_ROW_SOURCE_BINDING": (
            "acfqp.v075_live_model_row_source_binding.v2"
        ),
    }
)
_SOURCE_ROLE_ID_FIELD = MappingProxyType(
    {
        "OCCURRENCE_IDENTITY": "occurrence_id",
        "OPEN_CONTROLLED_PREFIX_VERIFICATION": "verification_id",
        "LIVE_ROW_SOURCE_BINDING": "binding_id",
    }
)

DOMAIN_TAGS = MappingProxyType(
    {
        "source_binding": (
            "acfqp:v075-portable-planning-source-binding:v2"
        ),
        "typed_graph": "acfqp:v075-portable-planning-typed-graph:v2",
        "dependency_dag": (
            "acfqp:v075-portable-planning-dependency-dag:v2"
        ),
        "record_attestation": (
            "acfqp:v075-portable-planning-record-attestation:v2"
        ),
        "role_closure": (
            "acfqp:v075-portable-planning-role-closure:v2"
        ),
        "propagated_role_closure": (
            "acfqp:v075-portable-planning-propagated-role-closure:v2"
        ),
        "aggregate": "acfqp:v075-portable-planning-authority:v2",
    }
)


class V075PortablePlanningV2InvariantViolation(ValueError):
    """A planning artifact, source witness, or dependency proof was invalid."""


class V075PortablePlanningProductionV2NotReady(RuntimeError):
    """This construction-only authority cannot authorize production."""


class V075PortablePlanningRoleStatusV2(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED = (
        "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
    )
    NOT_PRESENT_IN_OCCURRENCE = "NOT_PRESENT_IN_OCCURRENCE"


class V075PortablePlanningResolverKindV2(str, Enum):
    UPSTREAM_M2_DYNAMIC_CHILD = "UPSTREAM_M2_DYNAMIC_CHILD"
    M2_NUMERICAL_MODEL_PUBLIC_ROW_REPLAY = (
        "M2_NUMERICAL_MODEL_PUBLIC_ROW_REPLAY"
    )
    M2_NUMERICAL_PROOF_EXACT_PLANNER_REPLAY = (
        "M2_NUMERICAL_PROOF_EXACT_PLANNER_REPLAY"
    )
    NO_REGISTERED_SEMANTIC_AUTHORITY = (
        "NO_REGISTERED_SEMANTIC_AUTHORITY"
    )


def _fail(message: str) -> NoReturn:
    raise V075PortablePlanningV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortablePlanningV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PortablePlanningV2InvariantViolation(str(error)) from error


def _strict_document(raw: bytes, *, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075PortablePlanningV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return value


def _raw(value: Any) -> bytes:
    return canonical_json_bytes(value.to_document())


def _epochs(
    upstream: m2_child.V075PortableDynamicChildProposalReplayV2,
    *,
    _upstream_already_current: bool = False,
) -> tuple[live_model.V075LiveIncrementalModelEpochV2, ...]:
    if (
        type(upstream)
        is not m2_child.V075PortableDynamicChildProposalReplayV2
    ):
        _fail("planning authority requires exact hardened 1.76 replay")
    if not _upstream_already_current:
        upstream._assert_current()  # noqa: SLF001
    values = upstream.typed_graph.m2_live_epoch_result.typed_graph.epochs
    if (
        type(values) is not tuple
        or not values
        or any(
            type(item)
            is not live_model.V075LiveIncrementalModelEpochV2
            for item in values
        )
    ):
        _fail("hardened 1.76 contains no exact live epochs")
    return values


_RECORD_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _PortableRecordBindingV2:
    _issuer: InitVar[object]
    record_id: str
    record_index: int
    role: str
    artifact_schema: str
    semantic_artifact_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes: bytes = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RECORD_BINDING_ISSUER:
            _fail("planning record binding is caller-minted")
        self._assert_current()

    def _assert_current(self) -> None:
        _cid(self.record_id, "planning portable record")
        _cid(self.semantic_artifact_id, "planning semantic artifact")
        schemas = {**_ROLE_SCHEMA, **_SOURCE_ROLE_SCHEMA}
        id_fields = {**_ROLE_ID_FIELD, **_SOURCE_ROLE_ID_FIELD}
        if (
            type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in schemas
            or self.artifact_schema != schemas[self.role]
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
        ):
            _fail("planning portable record binding is malformed")
        for value in self.dependency_record_ids:
            _cid(value, "planning portable dependency")
        document = _strict_document(
            self.canonical_artifact_bytes,
            label=f"planning {self.role}",
        )
        if (
            document.get("schema") != self.artifact_schema
            or document.get(id_fields[self.role])
            != self.semantic_artifact_id
        ):
            _fail("planning record bytes are role/schema-transplanted")
        domain = portable._record_domain(self.role)  # noqa: SLF001
        payload = {
            "schema": "acfqp.v075_portable_evidence_artifact_record.v2",
            "schema_version": portable.SCHEMA_VERSION,
            "profile_key": portable.PROFILE_KEY,
            "index": self.record_index,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "artifact_domain_tag": domain,
            "semantic_artifact_id": self.semantic_artifact_id,
            "dependency_record_ids": list(self.dependency_record_ids),
            "canonical_artifact_bytes_hex": (
                self.canonical_artifact_bytes.hex()
            ),
            "raw_bytes_complete": True,
            "private_material_serialized": False,
            "official_execution_allowed": False,
        }
        if portable._hash(domain, payload) != self.record_id:  # noqa: SLF001
            _fail("planning portable record ID is stale or rehashed")

    def commitment_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "semantic_artifact_id": self.semantic_artifact_id,
            "dependency_record_ids": list(self.dependency_record_ids),
            "canonical_artifact_sha256": hashlib.sha256(
                self.canonical_artifact_bytes
            ).hexdigest(),
            "canonical_artifact_byte_count": len(
                self.canonical_artifact_bytes
            ),
        }


def _binding_from_record(record: Any) -> _PortableRecordBindingV2:
    return _PortableRecordBindingV2(
        _RECORD_BINDING_ISSUER,
        record.record_id,
        record.index,
        record.role,
        record.artifact_schema,
        record.semantic_artifact_id,
        tuple(record.dependency_record_ids),
        record.canonical_artifact_bytes,
    )


def _replay_numerical_registry(
    upstream: m2_child.V075PortableDynamicChildProposalReplayV2,
    *,
    _upstream_already_current: bool = False,
) -> tuple[
    tuple[planning.V075NumericalModelV2, ...],
    tuple[planning.V075NumericalPlanningProofV2, ...],
]:
    """Recompute every epoch proof through the public exact planner."""

    models: dict[str, planning.V075NumericalModelV2] = {}
    proofs: dict[str, planning.V075NumericalPlanningProofV2] = {}
    for epoch in _epochs(
        upstream,
        _upstream_already_current=_upstream_already_current,
    ):
        try:
            replayed_proof = (
                planning.plan_v075_construction_numerical_model_v2(
                    model=epoch.model,
                    route=epoch.route,
                )
            )
        except Exception as error:
            raise V075PortablePlanningV2InvariantViolation(
                "numerical model/proof exact producer replay failed"
            ) from error
        if (
            _raw(replayed_proof.model) != _raw(epoch.model)
            or _raw(replayed_proof) != _raw(epoch.proof)
        ):
            _fail("epoch numerical model or proof differs from exact replay")
        prior_model = models.get(epoch.model.model_id)
        prior_proof = proofs.get(epoch.proof.proof_id)
        if (
            prior_model is not None
            and _raw(prior_model) != _raw(epoch.model)
        ) or (
            prior_proof is not None
            and _raw(prior_proof) != _raw(epoch.proof)
        ):
            _fail("one numerical semantic ID maps to conflicting bytes")
        models[epoch.model.model_id] = epoch.model
        proofs[epoch.proof.proof_id] = epoch.proof
    return (
        tuple(models[key] for key in sorted(models)),
        tuple(proofs[key] for key in sorted(proofs)),
    )


def _expected_target_bytes(
    models: tuple[planning.V075NumericalModelV2, ...],
    proofs: tuple[planning.V075NumericalPlanningProofV2, ...],
) -> Mapping[str, Mapping[str, bytes]]:
    return MappingProxyType(
        {
            "NUMERICAL_MODEL": MappingProxyType(
                {item.model_id: _raw(item) for item in models}
            ),
            "NUMERICAL_PLANNING_PROOF": MappingProxyType(
                {item.proof_id: _raw(item) for item in proofs}
            ),
        }
    )


def _validate_target_registry(
    *,
    target_bindings: tuple[_PortableRecordBindingV2, ...],
    models: tuple[planning.V075NumericalModelV2, ...],
    proofs: tuple[planning.V075NumericalPlanningProofV2, ...],
    epochs: tuple[live_model.V075LiveIncrementalModelEpochV2, ...],
) -> None:
    if (
        type(target_bindings) is not tuple
        or any(
            type(item) is not _PortableRecordBindingV2
            or item.role not in _ROLE_SET
            for item in target_bindings
        )
        or tuple(item.record_index for item in target_bindings)
        != tuple(sorted(item.record_index for item in target_bindings))
        or len({item.record_id for item in target_bindings})
        != len(target_bindings)
    ):
        _fail("planning target registry is malformed or duplicated")
    for item in target_bindings:
        item._assert_current()
    expected = _expected_target_bytes(models, proofs)
    for role in _FULL_PUBLIC_ROLES:
        members = tuple(
            item for item in target_bindings if item.role == role
        )
        if len({item.semantic_artifact_id for item in members}) != len(
            members
        ):
            _fail(f"{role} registry duplicates one semantic artifact")
        actual = {
            item.semantic_artifact_id: item.canonical_artifact_bytes
            for item in members
        }
        if actual != dict(expected[role]):
            _fail(f"{role} registry differs from exact all-epoch replay")
    inputs = tuple(
        item
        for item in target_bindings
        if item.role == "CONSTRUCTION_PLANNING_INPUT"
    )
    if len(inputs) != 1:
        _fail("construction planning input registry must be exact singleton")
    input_document = _strict_document(
        inputs[0].canonical_artifact_bytes,
        label="construction planning input",
    )
    final_epoch = max(epochs, key=lambda item: item.epoch_index)
    if input_document.get("numerical_model_id") != final_epoch.model.model_id:
        _fail("planning input public model identity differs from final epoch")


def _unique_record(
    records: tuple[_PortableRecordBindingV2, ...],
    *,
    role: str,
    semantic_id: str,
) -> _PortableRecordBindingV2:
    matches = tuple(
        item
        for item in records
        if item.role == role
        and item.semantic_artifact_id == semantic_id
    )
    if len(matches) != 1:
        _fail(f"planning source {role} is absent or duplicated")
    matches[0]._assert_current()
    return matches[0]


_SOURCE_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePlanningSourceBindingV2:
    """Content-addressed public producer inputs for one model or proof."""

    _issuer: InitVar[object]
    target_record_id: str
    target_role: str
    target_semantic_artifact_id: str
    occurrence_id: str
    context_id: str
    source_epoch_ids: tuple[str, ...]
    route_values: tuple[str, ...]
    source_dependency_record_ids: tuple[str, ...]
    source_commitments: tuple[tuple[str, str], ...]
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_BINDING_ISSUER:
            _fail("planning source binding is caller-minted")
        for value, label in (
            (self.target_record_id, "planning binding target record"),
            (
                self.target_semantic_artifact_id,
                "planning binding target semantic artifact",
            ),
            (self.occurrence_id, "planning binding occurrence"),
            (self.context_id, "planning binding context"),
        ):
            _cid(value, label)
        if (
            self.target_role not in _FULL_PUBLIC_ROLES
            or type(self.source_epoch_ids) is not tuple
            or not self.source_epoch_ids
            or tuple(sorted(set(self.source_epoch_ids)))
            != self.source_epoch_ids
            or type(self.route_values) is not tuple
            or not self.route_values
            or tuple(sorted(set(self.route_values))) != self.route_values
            or type(self.source_dependency_record_ids) is not tuple
            or not self.source_dependency_record_ids
            or tuple(sorted(set(self.source_dependency_record_ids)))
            != self.source_dependency_record_ids
            or type(self.source_commitments) is not tuple
            or not self.source_commitments
            or tuple(sorted(set(self.source_commitments)))
            != self.source_commitments
            or len({name for name, _value in self.source_commitments})
            != len(self.source_commitments)
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or not item[0]
                or type(item[1]) is not str
                or not item[1]
                for item in self.source_commitments
            )
        ):
            _fail("planning source binding is malformed")
        for value in (
            *self.source_epoch_ids,
            *self.source_dependency_record_ids,
        ):
            _cid(value, "planning source dependency")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("source_binding", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_planning_source_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "target_record_id": self.target_record_id,
            "target_role": self.target_role,
            "target_semantic_artifact_id": (
                self.target_semantic_artifact_id
            ),
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "source_epoch_ids": list(self.source_epoch_ids),
            "route_values": list(self.route_values),
            "source_dependency_record_ids": list(
                self.source_dependency_record_ids
            ),
            "source_commitments": [
                {"name": name, "value": value}
                for name, value in self.source_commitments
            ],
            "live_epoch_record_dependency_present": False,
            "reconciliation_record_dependency_present": False,
            "result_record_dependency_present": False,
            "private_lineage_consumed": False,
        }

    @property
    def binding_id(self) -> str:
        if self._binding_id != _hash("source_binding", self._payload()):
            _fail("planning source binding identity is stale")
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


def _build_source_bindings(
    *,
    epochs: tuple[live_model.V075LiveIncrementalModelEpochV2, ...],
    target_bindings: tuple[_PortableRecordBindingV2, ...],
    source_records: tuple[_PortableRecordBindingV2, ...],
) -> tuple[V075PortablePlanningSourceBindingV2, ...]:
    target_by_key = {
        (item.role, item.semantic_artifact_id): item
        for item in target_bindings
    }
    result: list[V075PortablePlanningSourceBindingV2] = []
    models = sorted({item.model.model_id for item in epochs})
    proofs = sorted({item.proof.proof_id for item in epochs})
    for role, semantic_ids in (
        ("NUMERICAL_MODEL", models),
        ("NUMERICAL_PLANNING_PROOF", proofs),
    ):
        for semantic_id in semantic_ids:
            target = target_by_key.get((role, semantic_id))
            if target is None:
                _fail(f"{role} target record is absent")
            matched = tuple(
                item
                for item in epochs
                if (
                    item.model.model_id
                    if role == "NUMERICAL_MODEL"
                    else item.proof.proof_id
                )
                == semantic_id
            )
            occurrence_ids = {
                item.occurrence_identity.occurrence_id for item in matched
            }
            context_ids = {item.context_id for item in matched}
            if len(occurrence_ids) != 1 or len(context_ids) != 1:
                _fail("one planning artifact crossed occurrence/context")
            occurrence_id = next(iter(occurrence_ids))
            context_id = next(iter(context_ids))
            occurrence_record = _unique_record(
                source_records,
                role="OCCURRENCE_IDENTITY",
                semantic_id=occurrence_id,
            )
            dependencies: set[str] = {occurrence_record.record_id}
            commitments: set[tuple[str, str]] = {
                ("occurrence_record_id", occurrence_record.record_id),
                ("occurrence_id", occurrence_id),
                ("context_id", context_id),
            }
            if role == "NUMERICAL_MODEL":
                for epoch in matched:
                    prefix = _unique_record(
                        source_records,
                        role="OPEN_CONTROLLED_PREFIX_VERIFICATION",
                        semantic_id=(
                            epoch.open_prefix_verification.verification_id
                        ),
                    )
                    dependencies.add(prefix.record_id)
                    commitments.add(
                        (
                            f"epoch:{epoch.model_epoch_id}:prefix_record_id",
                            prefix.record_id,
                        )
                    )
                    if tuple(
                        item.row_id for item in epoch.model.rows
                    ) != tuple(
                        item.numerical_row_id for item in epoch.row_sources
                    ):
                        _fail("model rows and live row sources are reordered")
                    for row, source in zip(
                        epoch.model.rows,
                        epoch.row_sources,
                        strict=True,
                    ):
                        source_record = _unique_record(
                            source_records,
                            role="LIVE_ROW_SOURCE_BINDING",
                            semantic_id=source.binding_id,
                        )
                        if (
                            source_record.canonical_artifact_bytes
                            != _raw(source)
                            or source.numerical_row_id != row.row_id
                            or source.row_binding_id != row.row_binding_id
                            or source.support_freeze_id
                            not in {
                                item.freeze_id
                                for item in epoch.support_freezes
                            }
                        ):
                            _fail(
                                "model row/source/freeze witness differs "
                                "from exact live epoch"
                            )
                        dependencies.add(source_record.record_id)
                        commitments.update(
                            {
                                (
                                    f"epoch:{epoch.model_epoch_id}:"
                                    f"row:{row.row_id}:source_record_id",
                                    source_record.record_id,
                                ),
                                (
                                    f"epoch:{epoch.model_epoch_id}:"
                                    f"row:{row.row_id}:row_binding_id",
                                    source.row_binding_id,
                                ),
                                (
                                    f"epoch:{epoch.model_epoch_id}:"
                                    f"row:{row.row_id}:support_freeze_id",
                                    source.support_freeze_id,
                                ),
                                (
                                    f"epoch:{epoch.model_epoch_id}:"
                                    f"row:{row.row_id}:source_digest",
                                    source.source_digest,
                                ),
                            }
                        )
            else:
                model_ids = {item.model.model_id for item in matched}
                if len(model_ids) != 1:
                    _fail("one numerical proof crossed numerical models")
                model_record = target_by_key.get(
                    ("NUMERICAL_MODEL", next(iter(model_ids)))
                )
                if model_record is None:
                    _fail("numerical proof source model record is absent")
                dependencies.add(model_record.record_id)
                commitments.add(
                    ("numerical_model_record_id", model_record.record_id)
                )
            for epoch in matched:
                commitments.add(
                    (
                        f"epoch:{epoch.model_epoch_id}:route",
                        epoch.route.value,
                    )
                )
            result.append(
                V075PortablePlanningSourceBindingV2(
                    _SOURCE_BINDING_ISSUER,
                    target.record_id,
                    role,
                    semantic_id,
                    occurrence_id,
                    context_id,
                    tuple(sorted(item.model_epoch_id for item in matched)),
                    tuple(sorted({item.route.value for item in matched})),
                    tuple(sorted(dependencies)),
                    tuple(sorted(commitments)),
                )
            )
    values = tuple(sorted(result, key=lambda item: item.target_record_id))
    if len(values) != len(models) + len(proofs):
        _fail("planning source binding coverage is not all-or-none")
    return values


def _expected_source_bytes(
    epochs: tuple[live_model.V075LiveIncrementalModelEpochV2, ...],
) -> Mapping[tuple[str, str], bytes]:
    expected: dict[tuple[str, str], bytes] = {}
    for epoch in epochs:
        members = (
            (
                "OCCURRENCE_IDENTITY",
                epoch.occurrence_identity.occurrence_id,
                _raw(epoch.occurrence_identity),
            ),
            (
                "OPEN_CONTROLLED_PREFIX_VERIFICATION",
                epoch.open_prefix_verification.verification_id,
                _raw(epoch.open_prefix_verification),
            ),
            *(
                (
                    "LIVE_ROW_SOURCE_BINDING",
                    source.binding_id,
                    _raw(source),
                )
                for source in epoch.row_sources
            ),
        )
        for role, semantic_id, raw in members:
            prior = expected.get((role, semantic_id))
            if prior is not None and prior != raw:
                _fail("one planning source semantic ID has conflicting bytes")
            expected[(role, semantic_id)] = raw
    if not expected:
        _fail("planning source registry is empty")
    return MappingProxyType(dict(sorted(expected.items())))


def _required_source_records(
    *,
    all_records: tuple[Any, ...],
    epochs: tuple[live_model.V075LiveIncrementalModelEpochV2, ...],
) -> tuple[_PortableRecordBindingV2, ...]:
    expected = _expected_source_bytes(epochs)
    selected: list[_PortableRecordBindingV2] = []
    for (role, semantic_id), expected_bytes in expected.items():
        matches = tuple(
            item
            for item in all_records
            if item.role == role
            and item.semantic_artifact_id == semantic_id
        )
        if len(matches) != 1:
            _fail(f"required planning source {role} is absent or duplicated")
        binding = _binding_from_record(matches[0])
        if binding.canonical_artifact_bytes != expected_bytes:
            _fail(f"required planning source {role} bytes changed")
        selected.append(binding)
    return tuple(sorted(selected, key=lambda item: item.record_index))


def _validate_exact_source_record_registry(
    *,
    source_records: tuple[_PortableRecordBindingV2, ...],
    epochs: tuple[live_model.V075LiveIncrementalModelEpochV2, ...],
) -> None:
    expected_sources = dict(_expected_source_bytes(epochs))
    actual_sources: dict[tuple[str, str], bytes] = {}
    if (
        type(source_records) is not tuple
        or tuple(item.record_index for item in source_records)
        != tuple(sorted(item.record_index for item in source_records))
        or len({item.record_id for item in source_records})
        != len(source_records)
    ):
        _fail("planning source record order or identity is duplicated")
    for item in source_records:
        if (
            type(item) is not _PortableRecordBindingV2
            or item.role not in _SOURCE_ROLE_SCHEMA
        ):
            _fail("planning source record registry is malformed")
        item._assert_current()
        key = (item.role, item.semantic_artifact_id)
        if key in actual_sources:
            _fail("planning source record registry is duplicated")
        actual_sources[key] = item.canonical_artifact_bytes
    if actual_sources != expected_sources:
        _fail("planning source record registry is incomplete or overbroad")


_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePlanningTypedGraphV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    m2_dynamic_child_result: (
        m2_child.V075PortableDynamicChildProposalReplayV2
    ) = field(repr=False)
    models: tuple[planning.V075NumericalModelV2, ...] = field(repr=False)
    proofs: tuple[planning.V075NumericalPlanningProofV2, ...] = field(
        repr=False
    )
    target_record_bindings: tuple[_PortableRecordBindingV2, ...] = field(
        repr=False
    )
    source_record_bindings: tuple[_PortableRecordBindingV2, ...] = field(
        repr=False
    )
    source_bindings: tuple[V075PortablePlanningSourceBindingV2, ...]
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TYPED_GRAPH_ISSUER:
            _fail("planning typed graph is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "planning graph bundle"),
            (self.occurrence_id, "planning graph occurrence"),
            (
                self.public_context_closure_id,
                "planning graph public context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.m2_dynamic_child_result)
            is not m2_child.V075PortableDynamicChildProposalReplayV2
            or type(self.models) is not tuple
            or not self.models
            or any(
                type(item) is not planning.V075NumericalModelV2
                for item in self.models
            )
            or type(self.proofs) is not tuple
            or not self.proofs
            or any(
                type(item) is not planning.V075NumericalPlanningProofV2
                for item in self.proofs
            )
            or type(self.target_record_bindings) is not tuple
            or type(self.source_record_bindings) is not tuple
            or type(self.source_bindings) is not tuple
            or any(
                type(item) is not V075PortablePlanningSourceBindingV2
                for item in self.source_bindings
            )
        ):
            _fail("planning typed graph is malformed")
        for item in self.source_bindings:
            _ = item.binding_id
        self.m2_dynamic_child_result._assert_current()  # noqa: SLF001
        if (
            self.m2_dynamic_child_result.bundle_id != self.bundle_id
            or self.m2_dynamic_child_result.occurrence_id
            != self.occurrence_id
            or self.m2_dynamic_child_result.public_context_closure_id
            != self.public_context_closure_id
        ):
            _fail("planning typed graph crossed hardened identities")
        epochs = _epochs(
            self.m2_dynamic_child_result,
            _upstream_already_current=True,
        )
        models, proofs = _replay_numerical_registry(
            self.m2_dynamic_child_result,
            _upstream_already_current=True,
        )
        if (
            tuple(_raw(item) for item in self.models)
            != tuple(_raw(item) for item in models)
            or tuple(_raw(item) for item in self.proofs)
            != tuple(_raw(item) for item in proofs)
        ):
            _fail("planning typed artifacts differ from exact replay")
        _validate_target_registry(
            target_bindings=self.target_record_bindings,
            models=self.models,
            proofs=self.proofs,
            epochs=epochs,
        )
        _validate_exact_source_record_registry(
            source_records=self.source_record_bindings,
            epochs=epochs,
        )
        expected_bindings = _build_source_bindings(
            epochs=epochs,
            target_bindings=self.target_record_bindings,
            source_records=self.source_record_bindings,
        )
        if tuple(item.to_document() for item in self.source_bindings) != tuple(
            item.to_document() for item in expected_bindings
        ):
            _fail("planning source bindings are stale or transplanted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_planning_typed_graph.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "hardened_m2_dynamic_child_result_id": (
                self.m2_dynamic_child_result._result_id  # noqa: SLF001
            ),
            "hardened_m2_dynamic_child_dependency_dag_id": (
                self.m2_dynamic_child_result.dependency_dag._dag_id
            ),
            "numerical_model_ids": [item.model_id for item in self.models],
            "numerical_proof_ids": [item.proof_id for item in self.proofs],
            "target_record_commitments": [
                item.commitment_document()
                for item in self.target_record_bindings
            ],
            "source_record_commitments": [
                item.commitment_document()
                for item in self.source_record_bindings
            ],
            "source_binding_ids": [
                item.binding_id for item in self.source_bindings
            ],
            "all_epoch_models_replayed": True,
            "all_epoch_proofs_replayed_by_public_exact_planner": True,
            "construction_planning_input_compiler_called": False,
            "typed_construction_lineage_fabricated": False,
            "private_replay_performed": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._graph_id != _hash("typed_graph", self._payload()):
            _fail("planning typed graph identity is stale")

    @property
    def graph_id(self) -> str:
        self._assert_current()
        return self._graph_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "typed_graph_id": self._graph_id}


@dataclass(frozen=True, slots=True)
class V075PortablePlanningDependencyNodeV2:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    source_binding_id: str | None
    resolver_kind: V075PortablePlanningResolverKindV2
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    dependency_depth: int

    def __post_init__(self) -> None:
        _cid(self.record_id, "planning dependency node")
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
            != (
                set(self.portable_declared_dependency_record_ids)
                | set(
                    self.authority_local_semantic_dependency_record_ids
                )
            )
            or type(self.resolver_kind)
            is not V075PortablePlanningResolverKindV2
            or type(self.local_semantic_authority_resolved) is not bool
            or type(self.semantically_resolved) is not bool
            or type(self.dependency_depth) is not int
            or self.dependency_depth <= 0
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
            _fail("planning dependency node is malformed")
        if self.source_binding_id is not None:
            _cid(self.source_binding_id, "planning node source binding")
        for value in (
            *self.effective_dependency_record_ids,
            *self.unresolved_frontier_record_ids,
        ):
            _cid(value, "planning dependency edge")

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
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
            "dependency_depth": self.dependency_depth,
        }


def _iterative_planning_dependency_nodes(
    *,
    upstream_nodes: tuple[Any, ...],
    source_bindings: tuple[V075PortablePlanningSourceBindingV2, ...],
) -> tuple[V075PortablePlanningDependencyNodeV2, ...]:
    """Recompute the complete three-lane DAG with forward-edge-safe Kahn."""

    if (
        type(upstream_nodes) is not tuple
        or not upstream_nodes
        or len(upstream_nodes) > MAX_DEPENDENCY_NODES
        or type(source_bindings) is not tuple
        or any(
            type(item) is not V075PortablePlanningSourceBindingV2
            for item in source_bindings
        )
    ):
        _fail("planning dependency replay requires a bounded nonempty DAG")
    for item in source_bindings:
        _ = item.binding_id
    upstream_by_id: dict[str, Any] = {}
    for expected_index, item in enumerate(upstream_nodes):
        try:
            record_id = item.record_id
            portable_deps = tuple(
                item.portable_declared_dependency_record_ids
            )
            local_deps = tuple(
                item.authority_local_semantic_dependency_record_ids
            )
            effective_deps = tuple(item.effective_dependency_record_ids)
        except (AttributeError, TypeError) as error:
            raise V075PortablePlanningV2InvariantViolation(
                "planning upstream dependency node is malformed"
            ) from error
        if (
            item.record_index != expected_index
            or record_id in upstream_by_id
            or tuple(sorted(set(portable_deps))) != portable_deps
            or tuple(sorted(set(local_deps))) != local_deps
            or tuple(sorted(set(effective_deps))) != effective_deps
            or set(effective_deps) != set(portable_deps) | set(local_deps)
        ):
            _fail("planning upstream DAG or dependency lanes are invalid")
        upstream_by_id[record_id] = item
    binding_by_target = {
        item.target_record_id: item for item in source_bindings
    }
    if len(binding_by_target) != len(source_bindings):
        _fail("planning source binding target is duplicated")
    all_ids = set(upstream_by_id)
    role_by_id = {
        record_id: item.role
        for record_id, item in upstream_by_id.items()
    }
    portable_by_id: dict[str, tuple[str, ...]] = {}
    local_by_id: dict[str, tuple[str, ...]] = {}
    effective_by_id: dict[str, tuple[str, ...]] = {}
    resolver_by_id: dict[
        str, V075PortablePlanningResolverKindV2
    ] = {}
    local_resolved_by_id: dict[str, bool] = {}
    source_binding_id_by_id: dict[str, str | None] = {}
    for record_id, upstream in upstream_by_id.items():
        portable_deps = tuple(
            upstream.portable_declared_dependency_record_ids
        )
        inherited_local = tuple(
            upstream.authority_local_semantic_dependency_record_ids
        )
        binding = binding_by_target.get(record_id)
        if (
            binding is not None
            and binding.target_role != role_by_id[record_id]
        ):
            _fail("planning source binding role is transplanted")
        added = () if binding is None else binding.source_dependency_record_ids
        local_deps = tuple(sorted(set(inherited_local) | set(added)))
        effective = tuple(sorted(set(portable_deps) | set(local_deps)))
        if any(value not in all_ids for value in effective):
            _fail("planning dependency graph cites a foreign record")
        if record_id in effective:
            _fail("planning dependency graph contains a self-edge")
        if role_by_id[record_id] == "NUMERICAL_MODEL" and any(
            role_by_id[value]
            in {
                "LIVE_MODEL_EPOCH",
                "SIGNED_CONTROL_RECONCILIATION",
                "CLOSED_RECONCILIATION",
                "MULTIROUND_RESULT",
            }
            for value in effective
        ):
            _fail("numerical model has a forbidden reverse source edge")
        if binding is not None:
            if binding.target_role == "NUMERICAL_MODEL":
                resolver = (
                    V075PortablePlanningResolverKindV2
                    .M2_NUMERICAL_MODEL_PUBLIC_ROW_REPLAY
                )
            else:
                resolver = (
                    V075PortablePlanningResolverKindV2
                    .M2_NUMERICAL_PROOF_EXACT_PLANNER_REPLAY
                )
            local_resolved = True
            source_binding_id = binding.binding_id
        elif role_by_id[record_id] == "CONSTRUCTION_PLANNING_INPUT":
            resolver = (
                V075PortablePlanningResolverKindV2
                .NO_REGISTERED_SEMANTIC_AUTHORITY
            )
            local_resolved = False
            source_binding_id = None
        else:
            resolver = (
                V075PortablePlanningResolverKindV2
                .UPSTREAM_M2_DYNAMIC_CHILD
            )
            local_resolved = bool(
                upstream.local_semantic_authority_resolved
            )
            source_binding_id = None
        portable_by_id[record_id] = portable_deps
        local_by_id[record_id] = local_deps
        effective_by_id[record_id] = effective
        resolver_by_id[record_id] = resolver
        local_resolved_by_id[record_id] = local_resolved
        source_binding_id_by_id[record_id] = source_binding_id
    if set(binding_by_target) != {
        record_id
        for record_id, role in role_by_id.items()
        if role in _FULL_PUBLIC_ROLES
    }:
        _fail("planning source bindings do not cover the exact target union")

    indegree = {
        record_id: len(dependencies)
        for record_id, dependencies in effective_by_id.items()
    }
    successors = {record_id: [] for record_id in all_ids}
    for record_id, dependencies in effective_by_id.items():
        for dependency_id in dependencies:
            successors[dependency_id].append(record_id)
    ready = [
        (upstream_by_id[record_id].record_index, record_id)
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
                    (upstream_by_id[successor].record_index, successor),
                )
    if len(order) != len(all_ids):
        _fail("planning effective dependency graph contains a cycle")

    resolved_by_id: dict[str, bool] = {}
    frontier_by_id: dict[str, tuple[str, ...]] = {}
    depth_by_id: dict[str, int] = {}
    node_by_id: dict[str, V075PortablePlanningDependencyNodeV2] = {}
    for record_id in order:
        dependencies = effective_by_id[record_id]
        semantically_resolved = (
            local_resolved_by_id[record_id]
            and all(resolved_by_id[value] for value in dependencies)
        )
        if semantically_resolved:
            frontier: tuple[str, ...] = ()
        elif not local_resolved_by_id[record_id]:
            frontier = (record_id,)
        else:
            unresolved: set[str] = set()
            for dependency_id in dependencies:
                unresolved.update(frontier_by_id[dependency_id])
            frontier = tuple(sorted(unresolved))
            if not frontier:
                _fail("unresolved planning node lacks an exact frontier")
        depth = 1 + max(
            (depth_by_id[value] for value in dependencies),
            default=0,
        )
        node = V075PortablePlanningDependencyNodeV2(
            record_id,
            upstream_by_id[record_id].record_index,
            role_by_id[record_id],
            portable_by_id[record_id],
            local_by_id[record_id],
            effective_by_id[record_id],
            source_binding_id_by_id[record_id],
            resolver_by_id[record_id],
            local_resolved_by_id[record_id],
            semantically_resolved,
            frontier,
            tuple(sorted({role_by_id[value] for value in frontier})),
            depth,
        )
        node_by_id[record_id] = node
        resolved_by_id[record_id] = semantically_resolved
        frontier_by_id[record_id] = frontier
        depth_by_id[record_id] = depth
    return tuple(
        node_by_id[item.record_id]
        for item in sorted(
            upstream_nodes,
            key=lambda value: value.record_index,
        )
    )


_DAG_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePlanningDependencyDAGV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    m2_dynamic_child_result: (
        m2_child.V075PortableDynamicChildProposalReplayV2
    ) = field(repr=False)
    source_bindings: tuple[V075PortablePlanningSourceBindingV2, ...]
    nodes: tuple[V075PortablePlanningDependencyNodeV2, ...]
    _dag_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DAG_ISSUER:
            _fail("planning dependency DAG is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_dag_id",
            _hash("dependency_dag", self._payload()),
        )

    def _validate(self) -> None:
        _cid(self.bundle_id, "planning DAG bundle")
        _cid(self.typed_graph_id, "planning DAG typed graph")
        if (
            type(self.m2_dynamic_child_result)
            is not m2_child.V075PortableDynamicChildProposalReplayV2
            or type(self.source_bindings) is not tuple
            or any(
                type(item) is not V075PortablePlanningSourceBindingV2
                for item in self.source_bindings
            )
            or type(self.nodes) is not tuple
            or not self.nodes
            or any(
                type(item) is not V075PortablePlanningDependencyNodeV2
                for item in self.nodes
            )
        ):
            _fail("planning dependency DAG is malformed")
        for item in self.source_bindings:
            _ = item.binding_id
        self.m2_dynamic_child_result._assert_current()  # noqa: SLF001
        if self.m2_dynamic_child_result.bundle_id != self.bundle_id:
            _fail("planning dependency DAG crossed the portable bundle")
        expected = _iterative_planning_dependency_nodes(
            upstream_nodes=self.m2_dynamic_child_result.dependency_dag.nodes,
            source_bindings=self.source_bindings,
        )
        if tuple(item.to_document() for item in self.nodes) != tuple(
            item.to_document() for item in expected
        ):
            _fail("planning dependency DAG is stale or transplanted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_planning_dependency_dag.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "typed_graph_id": self.typed_graph_id,
            "hardened_m2_dynamic_child_dependency_dag_id": (
                self.m2_dynamic_child_result.dependency_dag._dag_id
            ),
            "source_binding_ids": [
                item.binding_id for item in self.source_bindings
            ],
            "nodes": [item.to_document() for item in self.nodes],
            "upstream_three_dependency_lanes_preserved": True,
            "iterative_kahn_walk_used": True,
            "recursive_dependency_walk_used": False,
            "maximum_dependency_nodes": MAX_DEPENDENCY_NODES,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._dag_id != _hash("dependency_dag", self._payload()):
            _fail("planning dependency DAG identity is stale")


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePlanningRecordAttestationV2:
    _issuer: InitVar[object]
    bundle_id: str
    typed_graph_id: str
    dependency_dag_id: str
    record_id: str
    role: str
    semantic_artifact_id: str
    source_binding_id: str | None
    status: V075PortablePlanningRoleStatusV2
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("planning attestation is caller-minted")
        for value, label in (
            (self.bundle_id, "planning attestation bundle"),
            (self.typed_graph_id, "planning attestation graph"),
            (self.dependency_dag_id, "planning attestation DAG"),
            (self.record_id, "planning attestation record"),
            (
                self.semantic_artifact_id,
                "planning attestation semantic artifact",
            ),
        ):
            _cid(value, label)
        if (
            self.role not in _ROLE_SET
            or type(self.status) is not V075PortablePlanningRoleStatusV2
            or tuple(sorted(set(self.unresolved_frontier_record_ids)))
            != self.unresolved_frontier_record_ids
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
            or (
                self.status is V075PortablePlanningRoleStatusV2.FULL_PUBLIC
                and (
                    self.unresolved_frontier_record_ids
                    or self.unresolved_frontier_roles
                )
            )
        ):
            _fail("planning attestation is malformed")
        if self.source_binding_id is not None:
            _cid(self.source_binding_id, "planning attestation source")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_planning_record_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "typed_graph_id": self.typed_graph_id,
            "dependency_dag_id": self.dependency_dag_id,
            "record_id": self.record_id,
            "role": self.role,
            "semantic_artifact_id": self.semantic_artifact_id,
            "source_binding_id": self.source_binding_id,
            "status": self.status.value,
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self._attestation_id}


def _build_attestations(
    *,
    bundle_id: str,
    typed_graph_id: str,
    dependency_dag_id: str,
    target_bindings: tuple[_PortableRecordBindingV2, ...],
    nodes: tuple[V075PortablePlanningDependencyNodeV2, ...],
) -> tuple[V075PortablePlanningRecordAttestationV2, ...]:
    by_id = {item.record_id: item for item in nodes}
    result = []
    for binding in target_bindings:
        node = by_id.get(binding.record_id)
        if node is None:
            _fail("planning target lacks a dependency node")
        status = (
            V075PortablePlanningRoleStatusV2.FULL_PUBLIC
            if node.semantically_resolved
            else V075PortablePlanningRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        result.append(
            V075PortablePlanningRecordAttestationV2(
                _ATTESTATION_ISSUER,
                bundle_id,
                typed_graph_id,
                dependency_dag_id,
                binding.record_id,
                binding.role,
                binding.semantic_artifact_id,
                node.source_binding_id,
                status,
                node.unresolved_frontier_record_ids,
                node.unresolved_frontier_roles,
            )
        )
    return tuple(
        sorted(result, key=lambda item: by_id[item.record_id].record_index)
    )


_ROLE_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePlanningRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    dependency_dag_id: str
    role: str
    status: V075PortablePlanningRoleStatusV2
    record_ids: tuple[str, ...]
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_CLOSURE_ISSUER:
            _fail("planning role closure is caller-minted")
        _cid(self.bundle_id, "planning closure bundle")
        _cid(self.dependency_dag_id, "planning closure DAG")
        if (
            self.role not in _ROLE_SET
            or type(self.status) is not V075PortablePlanningRoleStatusV2
            or type(self.record_ids) is not tuple
            or not self.record_ids
            or tuple(sorted(set(self.record_ids))) != self.record_ids
            or tuple(sorted(set(self.unresolved_frontier_record_ids)))
            != self.unresolved_frontier_record_ids
            or tuple(sorted(set(self.unresolved_frontier_roles)))
            != self.unresolved_frontier_roles
        ):
            _fail("planning role closure is malformed")
        object.__setattr__(
            self,
            "_closure_id",
            _hash("role_closure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_planning_role_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "dependency_dag_id": self.dependency_dag_id,
            "role": self.role,
            "status": self.status.value,
            "record_ids": list(self.record_ids),
            "unresolved_frontier_record_ids": list(
                self.unresolved_frontier_record_ids
            ),
            "unresolved_frontier_roles": list(
                self.unresolved_frontier_roles
            ),
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self._closure_id}


def _build_role_closures(
    *,
    bundle_id: str,
    dependency_dag_id: str,
    attestations: tuple[V075PortablePlanningRecordAttestationV2, ...],
) -> tuple[V075PortablePlanningRoleClosureV2, ...]:
    result = []
    for role in ROLE_ORDER:
        members = tuple(item for item in attestations if item.role == role)
        if not members:
            _fail(f"planning role {role} is unexpectedly absent")
        unresolved = tuple(
            item
            for item in members
            if item.status
            is not V075PortablePlanningRoleStatusV2.FULL_PUBLIC
        )
        status = (
            V075PortablePlanningRoleStatusV2.FULL_PUBLIC
            if not unresolved
            else V075PortablePlanningRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        )
        result.append(
            V075PortablePlanningRoleClosureV2(
                _ROLE_CLOSURE_ISSUER,
                bundle_id,
                dependency_dag_id,
                role,
                status,
                tuple(sorted(item.record_id for item in members)),
                tuple(
                    sorted(
                        {
                            value
                            for item in unresolved
                            for value in item.unresolved_frontier_record_ids
                        }
                    )
                ),
                tuple(
                    sorted(
                        {
                            value
                            for item in unresolved
                            for value in item.unresolved_frontier_roles
                        }
                    )
                ),
            )
        )
    return tuple(result)


_PROPAGATED_CLOSURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePlanningPropagatedRoleClosureV2:
    _issuer: InitVar[object]
    bundle_id: str
    dependency_dag_id: str
    role: str
    record_ids: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROPAGATED_CLOSURE_ISSUER:
            _fail("planning propagated closure is caller-minted")
        _cid(self.bundle_id, "propagated closure bundle")
        _cid(self.dependency_dag_id, "propagated closure DAG")
        if (
            self.role not in PROPAGATED_ROLE_ORDER
            or type(self.record_ids) is not tuple
            or not self.record_ids
            or tuple(sorted(set(self.record_ids))) != self.record_ids
        ):
            _fail("planning propagated role closure is malformed")
        object.__setattr__(
            self,
            "_closure_id",
            _hash("propagated_role_closure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_planning_propagated_role_closure.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "dependency_dag_id": self.dependency_dag_id,
            "role": self.role,
            "status": V075PortablePlanningRoleStatusV2.FULL_PUBLIC.value,
            "record_ids": list(self.record_ids),
            "unresolved_frontier_record_ids": [],
            "unresolved_frontier_roles": [],
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self._closure_id}


def _build_propagated_role_closures(
    *,
    bundle_id: str,
    dependency_dag_id: str,
    nodes: tuple[V075PortablePlanningDependencyNodeV2, ...],
) -> tuple[V075PortablePlanningPropagatedRoleClosureV2, ...]:
    result = []
    for role in PROPAGATED_ROLE_ORDER:
        members = tuple(item for item in nodes if item.role == role)
        if not members or any(not item.semantically_resolved for item in members):
            _fail(f"planning authority did not close propagated role {role}")
        result.append(
            V075PortablePlanningPropagatedRoleClosureV2(
                _PROPAGATED_CLOSURE_ISSUER,
                bundle_id,
                dependency_dag_id,
                role,
                tuple(sorted(item.record_id for item in members)),
            )
        )
    return tuple(result)


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePlanningReplayV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    typed_graph: V075PortablePlanningTypedGraphV2 = field(repr=False)
    dependency_dag: V075PortablePlanningDependencyDAGV2 = field(repr=False)
    attestations: tuple[V075PortablePlanningRecordAttestationV2, ...]
    role_closures: tuple[V075PortablePlanningRoleClosureV2, ...]
    propagated_role_closures: tuple[
        V075PortablePlanningPropagatedRoleClosureV2,
        ...,
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("planning result is caller-minted")
        self._validate()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _validate(self) -> None:
        for value, label in (
            (self.bundle_id, "planning result bundle"),
            (self.occurrence_id, "planning result occurrence"),
            (
                self.public_context_closure_id,
                "planning result public context",
            ),
        ):
            _cid(value, label)
        if (
            type(self.typed_graph) is not V075PortablePlanningTypedGraphV2
            or type(self.dependency_dag)
            is not V075PortablePlanningDependencyDAGV2
            or type(self.attestations) is not tuple
            or any(
                type(item) is not V075PortablePlanningRecordAttestationV2
                for item in self.attestations
            )
            or type(self.role_closures) is not tuple
            or any(
                type(item) is not V075PortablePlanningRoleClosureV2
                for item in self.role_closures
            )
            or tuple(item.role for item in self.role_closures) != ROLE_ORDER
            or type(self.propagated_role_closures) is not tuple
            or any(
                type(item)
                is not V075PortablePlanningPropagatedRoleClosureV2
                for item in self.propagated_role_closures
            )
            or tuple(
                item.role for item in self.propagated_role_closures
            )
            != PROPAGATED_ROLE_ORDER
        ):
            _fail("planning result is malformed")
        self.typed_graph._assert_current()
        self.dependency_dag._assert_current()
        if (
            self.typed_graph.bundle_id != self.bundle_id
            or self.typed_graph.occurrence_id != self.occurrence_id
            or self.typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self.dependency_dag.bundle_id != self.bundle_id
            or self.dependency_dag.typed_graph_id
            != self.typed_graph._graph_id
            or self.dependency_dag.m2_dynamic_child_result
            is not self.typed_graph.m2_dynamic_child_result
            or self.dependency_dag.source_bindings
            != self.typed_graph.source_bindings
        ):
            _fail("planning result crossed authority identities")
        expected_attestations = _build_attestations(
            bundle_id=self.bundle_id,
            typed_graph_id=self.typed_graph._graph_id,
            dependency_dag_id=self.dependency_dag._dag_id,
            target_bindings=self.typed_graph.target_record_bindings,
            nodes=self.dependency_dag.nodes,
        )
        if tuple(item.to_document() for item in self.attestations) != tuple(
            item.to_document() for item in expected_attestations
        ):
            _fail("planning attestations are stale or transplanted")
        expected_closures = _build_role_closures(
            bundle_id=self.bundle_id,
            dependency_dag_id=self.dependency_dag._dag_id,
            attestations=self.attestations,
        )
        if tuple(item.to_document() for item in self.role_closures) != tuple(
            item.to_document() for item in expected_closures
        ):
            _fail("planning role closures are stale or overclaim")
        status_by_role = {
            item.role: item.status for item in self.role_closures
        }
        if (
            any(
                status_by_role[role]
                is not V075PortablePlanningRoleStatusV2.FULL_PUBLIC
                for role in _FULL_PUBLIC_ROLES
            )
            or status_by_role["CONSTRUCTION_PLANNING_INPUT"]
            is not V075PortablePlanningRoleStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        ):
            _fail("planning normative three-role closure is invalid")
        input_closure = self.role_closures[2]
        if input_closure.unresolved_frontier_roles != (
            "CONSTRUCTION_PLANNING_INPUT",
        ):
            _fail("planning input frontier was falsely pushed into private law")
        expected_propagated = _build_propagated_role_closures(
            bundle_id=self.bundle_id,
            dependency_dag_id=self.dependency_dag._dag_id,
            nodes=self.dependency_dag.nodes,
        )
        if tuple(
            item.to_document() for item in self.propagated_role_closures
        ) != tuple(item.to_document() for item in expected_propagated):
            _fail("planning propagated role closures are stale")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_planning_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "typed_graph_id": self.typed_graph._graph_id,
            "dependency_dag_id": self.dependency_dag._dag_id,
            "role_order": list(ROLE_ORDER),
            "role_statuses": {
                item.role: item.status.value for item in self.role_closures
            },
            "propagated_full_public_roles": [
                item.role for item in self.propagated_role_closures
            ],
            "attestation_ids": [
                item._attestation_id for item in self.attestations
            ],
            "role_closure_ids": [
                item._closure_id for item in self.role_closures
            ],
            "propagated_role_closure_ids": [
                item._closure_id for item in self.propagated_role_closures
            ],
            "construction_planning_input_semantic_authority_claimed": False,
            "private_closure_verification_consumed": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "portable_semantic_registry_complete": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    def _assert_current(self) -> None:
        self._validate()
        if self._result_id != _hash("aggregate", self._payload()):
            _fail("planning result identity is stale")

    @property
    def result_id(self) -> str:
        self._assert_current()
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_OUTPUT_BYTES:
            _fail("planning result exceeds the registered output cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "result_id": self._result_id}

    def __reduce__(self) -> NoReturn:
        raise TypeError("M2 portable planning result is in-memory-only")


def replay_v075_portable_planning_authority_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortablePlanningReplayV2:
    """Replay numerical model/proof semantics from raw public authorities."""

    if (
        type(portable_bundle_bytes) is not bytes
        or type(public_context_closure_bytes) is not bytes
    ):
        _fail("M2 planning authority accepts canonical raw bytes only")
    try:
        upstream = (
            m2_child.replay_v075_portable_dynamic_child_proposal_v2(
                repository_root=repository_root,
                portable_bundle_bytes=portable_bundle_bytes,
                public_context_closure_bytes=public_context_closure_bytes,
            )
        )
    except Exception as error:
        raise V075PortablePlanningV2InvariantViolation(
            "M2 planning hardened 1.76 replay failed"
        ) from error
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
    except Exception as error:
        raise V075PortablePlanningV2InvariantViolation(
            "M2 planning portable bundle replay failed after 1.76"
        ) from error
    if (
        bundle.bundle_id != upstream.bundle_id
        or bundle.occurrence_id != upstream.occurrence_id
    ):
        _fail("M2 planning raw authorities were transplanted")

    target_bindings = tuple(
        _binding_from_record(item)
        for item in bundle.records
        if item.role in _ROLE_SET
    )
    epochs = _epochs(upstream, _upstream_already_current=True)
    models, proofs = _replay_numerical_registry(
        upstream,
        _upstream_already_current=True,
    )
    _validate_target_registry(
        target_bindings=target_bindings,
        models=models,
        proofs=proofs,
        epochs=epochs,
    )
    source_records = _required_source_records(
        all_records=tuple(bundle.records),
        epochs=epochs,
    )
    source_bindings = _build_source_bindings(
        epochs=epochs,
        target_bindings=target_bindings,
        source_records=source_records,
    )
    typed_graph = V075PortablePlanningTypedGraphV2(
        _TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        upstream.public_context_closure_id,
        upstream,
        models,
        proofs,
        target_bindings,
        source_records,
        source_bindings,
    )
    nodes = _iterative_planning_dependency_nodes(
        upstream_nodes=upstream.dependency_dag.nodes,
        source_bindings=source_bindings,
    )
    dag = V075PortablePlanningDependencyDAGV2(
        _DAG_ISSUER,
        bundle.bundle_id,
        typed_graph._graph_id,
        upstream,
        source_bindings,
        nodes,
    )
    attestations = _build_attestations(
        bundle_id=bundle.bundle_id,
        typed_graph_id=typed_graph._graph_id,
        dependency_dag_id=dag._dag_id,
        target_bindings=target_bindings,
        nodes=nodes,
    )
    role_closures = _build_role_closures(
        bundle_id=bundle.bundle_id,
        dependency_dag_id=dag._dag_id,
        attestations=attestations,
    )
    propagated = _build_propagated_role_closures(
        bundle_id=bundle.bundle_id,
        dependency_dag_id=dag._dag_id,
        nodes=nodes,
    )
    result = V075PortablePlanningReplayV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        upstream.public_context_closure_id,
        typed_graph,
        dag,
        attestations,
        role_closures,
        propagated,
    )
    if len(result.canonical_bytes) > MAX_OUTPUT_BYTES:
        _fail("planning authority output exceeds the registered cap")
    return result


def assert_v075_portable_planning_production_gate_v2(
    result: V075PortablePlanningReplayV2,
) -> NoReturn:
    if type(result) is not V075PortablePlanningReplayV2:
        _fail("planning production gate rejects duck-typed results")
    result._assert_current()
    raise V075PortablePlanningProductionV2NotReady(
        "contract 1.77 is construction-only; planning input/private lineage, "
        "source authority, code provenance, and production gates remain open"
    )


__all__ = [
    "B3_INPUT_ALLOWED",
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "J0_ACCESS_ALLOWED",
    "K7_INPUT_ALLOWED",
    "KERNEL_ACCESS_ALLOWED",
    "MAX_DEPENDENCY_NODES",
    "MAX_OUTPUT_BYTES",
    "OBSERVER_ACCESS_ALLOWED",
    "OBSERVER_INPUT_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_INPUT_CHANNELS_ALLOWED",
    "PRIVATE_REPLAY_PERFORMED",
    "PROFILE_KEY",
    "PRODUCTION_AUTHORIZING",
    "PROPAGATED_ROLE_ORDER",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "SOURCE_AUTHORITY_COMPLETE",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SIGNER_INPUT_ALLOWED",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "V075PortablePlanningDependencyDAGV2",
    "V075PortablePlanningDependencyNodeV2",
    "V075PortablePlanningProductionV2NotReady",
    "V075PortablePlanningPropagatedRoleClosureV2",
    "V075PortablePlanningRecordAttestationV2",
    "V075PortablePlanningReplayV2",
    "V075PortablePlanningResolverKindV2",
    "V075PortablePlanningRoleClosureV2",
    "V075PortablePlanningRoleStatusV2",
    "V075PortablePlanningSourceBindingV2",
    "V075PortablePlanningTypedGraphV2",
    "V075PortablePlanningV2InvariantViolation",
    "WORKER_ACCESS_ALLOWED",
    "WORKER_INPUT_ALLOWED",
    "assert_v075_portable_planning_production_gate_v2",
    "replay_v075_portable_planning_authority_v2",
]
