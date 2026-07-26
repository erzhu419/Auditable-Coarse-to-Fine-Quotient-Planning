"""Durable model-only transport for the registered H2 action switch.

This module is intentionally independent from the matching-buffer ground
domain and from the owner-bound action-local runner.  It gives the pure
``h2_action_indexed_proof_dag_v1`` control a strict filesystem/process
boundary:

* C1 stores the registered first model/query and exactly 18 lower nodes before
  any ground row is supplied; audit/proposal/root artifacts remain ID-only and
  are rebuilt after load;
* P1 loads C1 in a fresh process and emits the deterministic failed-N audit;
* an externally produced, content-addressed overlay projection supplies the
  exact registered M-row semantics plus opaque evidence identities;
* P2 loads C1 and that projection in a fresh process, independently executes
  the first 18/0 graph, derives and authorizes the invalidation cone, executes
  the final 10/8 graph, and emits the strict N-to-M continuation; and
* C2 stores exactly 28 lower-node documents/identities together with the 18
  active final bindings; final audit/proposal/root artifacts are again rebuilt
  by another fresh process.

The opaque overlay evidence identities are provenance coordinates.  This
model-only module validates their content-ID syntax and exact M-row projection,
but it cannot mint or replace the live ground authority that produced them.
The parent composition layer must retain that owner-bound authority.

The profile is a narrow registered construction control.  It is not a generic
checkpoint format, crash-recovery protocol, sample-efficiency result, workload
economics result, or official execution path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import acfqp.h2_action_indexed_proof_dag_v1 as dag
from acfqp.h2_durable_action_local_recovery_pins_v1 import (
    EXPECTED_ACTION_INDEXED_SOURCE_SHA256,
)
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


_CANONICAL_DAG_PARSE_NODE = (
    dag.parse_action_indexed_proof_node_document_v1
)
_CANONICAL_DAG_RESTORE_FIRST = (
    dag.restore_verified_action_indexed_first_lower_graph_v1
)
_CANONICAL_DAG_RESTORE_FINAL = (
    dag.restore_verified_action_indexed_final_lower_graph_v1
)
_CANONICAL_DAG_REBUILD_ROOTS = (
    dag.rebuild_action_indexed_roots_from_restored_runtime_v1
)
_CANONICAL_DAG_EXECUTE = dag.execute_action_indexed_epoch_v1
_CANONICAL_DAG_AUTHORIZE_FINAL = (
    dag.authorize_action_indexed_final_epoch_v1
)
_CANONICAL_DAG_DERIVE_PRE = (
    dag.derive_action_indexed_preexecution_invalidation_v1
)
_CANONICAL_DAG_DERIVE_POST = (
    dag.derive_action_indexed_delta_and_invalidation_v1
)
_CANONICAL_DAG_REGISTERED_FIRST = (
    dag.registered_first_action_indexed_h2_model_v1
)
_CANONICAL_DAG_REGISTERED_FINAL = (
    dag.registered_final_action_indexed_h2_model_v1
)
_CANONICAL_DAG_REGISTERED_QUERY = (
    dag.registered_action_indexed_h2_query_v1
)
_DAG_LIVE_AUTHORITIES = (
    (
        "parse_action_indexed_proof_node_document_v1",
        _CANONICAL_DAG_PARSE_NODE,
    ),
    (
        "restore_verified_action_indexed_first_lower_graph_v1",
        _CANONICAL_DAG_RESTORE_FIRST,
    ),
    (
        "restore_verified_action_indexed_final_lower_graph_v1",
        _CANONICAL_DAG_RESTORE_FINAL,
    ),
    (
        "rebuild_action_indexed_roots_from_restored_runtime_v1",
        _CANONICAL_DAG_REBUILD_ROOTS,
    ),
    ("execute_action_indexed_epoch_v1", _CANONICAL_DAG_EXECUTE),
    (
        "authorize_action_indexed_final_epoch_v1",
        _CANONICAL_DAG_AUTHORIZE_FINAL,
    ),
    (
        "derive_action_indexed_preexecution_invalidation_v1",
        _CANONICAL_DAG_DERIVE_PRE,
    ),
    (
        "derive_action_indexed_delta_and_invalidation_v1",
        _CANONICAL_DAG_DERIVE_POST,
    ),
    (
        "registered_first_action_indexed_h2_model_v1",
        _CANONICAL_DAG_REGISTERED_FIRST,
    ),
    (
        "registered_final_action_indexed_h2_model_v1",
        _CANONICAL_DAG_REGISTERED_FINAL,
    ),
    (
        "registered_action_indexed_h2_query_v1",
        _CANONICAL_DAG_REGISTERED_QUERY,
    ),
    ("ADDRESS_ORDER", dag.ADDRESS_ORDER),
    ("ActionIndexedEpochExecutionV1", dag.ActionIndexedEpochExecutionV1),
    (
        "ActionIndexedFirstRuntimeRestoreV1",
        dag.ActionIndexedFirstRuntimeRestoreV1,
    ),
    ("ActionIndexedH2ModelV1", dag.ActionIndexedH2ModelV1),
    ("ActionIndexedH2QueryV1", dag.ActionIndexedH2QueryV1),
    (
        "ActionIndexedInvalidationManifestV1",
        dag.ActionIndexedInvalidationManifestV1,
    ),
    ("ActionIndexedModelDeltaV1", dag.ActionIndexedModelDeltaV1),
    (
        "ActionIndexedPreExecutionInvalidationV1",
        dag.ActionIndexedPreExecutionInvalidationV1,
    ),
    ("ActionIndexedProofNodeV1", dag.ActionIndexedProofNodeV1),
    ("ActionIndexedProofRuntimeV1", dag.ActionIndexedProofRuntimeV1),
    ("GroundRowName", dag.GroundRowName),
    ("PROFILE_KEY", dag.PROFILE_KEY),
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.19.0"
PROFILE_KEY = "lmb_h2_durable_action_switch_transport_v0"

DOMAIN_TAGS = {
    "protocol": "acfqp:h2-durable-action-switch-protocol:v1",
    "c1_payload": "acfqp:h2-durable-action-switch-c1-payload:v1",
    "c1_manifest": "acfqp:h2-durable-action-switch-c1-manifest:v1",
    "commit": "acfqp:h2-durable-action-switch-commit:v1",
    "warm_replay": "acfqp:h2-durable-action-switch-warm-replay:v1",
    "p1_attestation": "acfqp:h2-durable-action-switch-p1-attestation:v1",
    "overlay": "acfqp:h2-durable-action-switch-overlay-projection:v1",
    "p2_continuation": "acfqp:h2-durable-action-switch-p2-continuation:v1",
    "c2_payload": "acfqp:h2-durable-action-switch-c2-payload:v1",
    "c2_manifest": "acfqp:h2-durable-action-switch-c2-manifest:v1",
    "c2_attestation": "acfqp:h2-durable-action-switch-c2-attestation:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("durable action-switch content domains must be unique")


class DurableActionSwitchInvariantViolation(ValueError):
    """A durable artifact, store, continuation, or process result is invalid."""


class CheckpointKind(str, Enum):
    C1_FIRST = "C1_FIRST"
    C2_FINAL = "C2_FINAL"


class WorkerKind(str, Enum):
    P1 = "P1"
    P2 = "P2"
    C2 = "C2"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise DurableActionSwitchInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise DurableActionSwitchInvariantViolation(
            f"{name} must be a full lowercase SHA-256 content ID"
        ) from error


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DurableActionSwitchInvariantViolation(
            f"{name} must be an integer >= {minimum}"
        )
    return value


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise DurableActionSwitchInvariantViolation(f"{name} must be a boolean")
    return value


def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise DurableActionSwitchInvariantViolation(
            f"{name} must be nonempty text"
        )
    return value


def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise DurableActionSwitchInvariantViolation(f"{name} must be exact")
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        numerator = value["numerator"]
        denominator = value["denominator"]
        if (
            type(numerator) is not int
            or type(denominator) is not int
            or denominator <= 0
        ):
            raise DurableActionSwitchInvariantViolation(
                f"{name} rational is invalid"
            )
        result = Fraction(numerator, denominator)
        if (
            result.numerator != numerator
            or result.denominator != denominator
        ):
            raise DurableActionSwitchInvariantViolation(
                f"{name} rational is not reduced"
            )
        return result
    raise DurableActionSwitchInvariantViolation(f"{name} must be exact")


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _normalize_document(value: Any) -> Any:
    if isinstance(value, Fraction):
        return _fdoc(value)
    if type(value) is dict:
        return {
            key: _normalize_document(item)
            for key, item in value.items()
        }
    if type(value) is list:
        return [_normalize_document(item) for item in value]
    if type(value) is tuple:
        return [_normalize_document(item) for item in value]
    return value


def _exact_mapping(
    value: Any,
    fields: set[str],
    where: str,
) -> dict[str, Any]:
    normalized = _normalize_document(value)
    if type(normalized) is not dict:
        raise DurableActionSwitchInvariantViolation(
            f"{where} must be an exact JSON object"
        )
    actual = set(normalized)
    if actual != fields:
        raise DurableActionSwitchInvariantViolation(
            f"{where} field set changed; "
            f"missing={sorted(fields - actual)!r}, "
            f"unknown={sorted(actual - fields)!r}"
        )
    return normalized


def _same_document(left: Any, right: Any) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _source_sha256(module: Any) -> str:
    path = Path(module.__file__).resolve()
    if path.suffix != ".py" or not path.is_file():
        raise DurableActionSwitchInvariantViolation(
            "action-indexed source is not a real Python file"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_model_only_import_boundary(*, fresh_worker: bool = False) -> None:
    """Check the stronger import boundary only inside an isolated worker.

    A host composition process may already retain the owner-bound action-local
    source (and therefore its ground module).  This module still never imports
    that source.  Only isolated workers claim that the ground module is absent
    from their process.
    """

    local_callables = (
        _CANONICAL_DAG_PARSE_NODE,
        _CANONICAL_DAG_RESTORE_FIRST,
        _CANONICAL_DAG_RESTORE_FINAL,
        _CANONICAL_DAG_REBUILD_ROOTS,
        _CANONICAL_DAG_EXECUTE,
        _CANONICAL_DAG_AUTHORIZE_FINAL,
        _CANONICAL_DAG_DERIVE_PRE,
        _CANONICAL_DAG_DERIVE_POST,
        _CANONICAL_DAG_REGISTERED_FIRST,
        _CANONICAL_DAG_REGISTERED_FINAL,
        _CANONICAL_DAG_REGISTERED_QUERY,
    )
    frozen_callables = tuple(
        item[1] for item in _DAG_LIVE_AUTHORITIES[:11]
    )
    internal_authorities = globals().get(
        "_TRANSPORT_INTERNAL_AUTHORITIES",
        (),
    )
    if (
        _source_sha256(dag) != EXPECTED_ACTION_INDEXED_SOURCE_SHA256
        or any(
            getattr(dag, name, None) is not authority
            for name, authority in _DAG_LIVE_AUTHORITIES
        )
        or local_callables != frozen_callables
        or not internal_authorities
        or any(
            globals().get(name) is not authority
            for name, authority in internal_authorities
        )
    ):
        raise DurableActionSwitchInvariantViolation(
            "action-indexed model-only source/live authority changed"
        )
    if fresh_worker and "acfqp.domains.matching_buffer" in sys.modules:
        raise DurableActionSwitchInvariantViolation(
            "model-only durable worker imported the matching-buffer ground module"
        )


_CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT = _assert_model_only_import_boundary


def _ordered_unique_node_ids(
    first: dag.ActionIndexedEpochExecutionV1,
    final: dag.ActionIndexedEpochExecutionV1 | None = None,
) -> tuple[str, ...]:
    values: dict[str, None] = {}
    for execution in (first,) if final is None else (first, final):
        for node in execution.nodes:
            values.setdefault(node.node_id, None)
    return tuple(sorted(values))


def _ordered_unique_nodes(
    first: dag.ActionIndexedEpochExecutionV1,
    final: dag.ActionIndexedEpochExecutionV1,
) -> tuple[dag.ActionIndexedProofNodeV1, ...]:
    by_id = {
        node.node_id: node
        for execution in (first, final)
        for node in execution.nodes
    }
    if len(by_id) != 28:
        raise DurableActionSwitchInvariantViolation(
            "cross-epoch lower cache no longer contains exactly 28 identities"
        )
    return tuple(by_id[node_id] for node_id in sorted(by_id))


def _active_bindings(
    execution: dag.ActionIndexedEpochExecutionV1,
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (node.address.value, node.node_key_id, node.node_id)
        for node in execution.nodes
    )


def _derive_first_state() -> tuple[
    dag.ActionIndexedH2ModelV1,
    dag.ActionIndexedH2QueryV1,
    dag.ActionIndexedProofRuntimeV1,
    dag.ActionIndexedEpochExecutionV1,
]:
    _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT()
    model = _CANONICAL_DAG_REGISTERED_FIRST()
    query = _CANONICAL_DAG_REGISTERED_QUERY()
    runtime = dag.ActionIndexedProofRuntimeV1()
    execution = _CANONICAL_DAG_EXECUTE(model, query, runtime)
    if (
        execution.work.lower_computed != 18
        or execution.work.lower_reused != 0
        or execution.work.fresh_root_computed != 3
        or runtime.cache_size != 18
    ):
        raise DurableActionSwitchInvariantViolation(
            "registered first action-indexed work changed"
        )
    return model, query, runtime, execution


@dataclass(frozen=True, slots=True)
class DurableActionSwitchProtocolV1:
    first_model_id: str
    query_id: str
    action_indexed_profile_key: str
    action_indexed_source_sha256: str
    c1_lower_entry_count: int = 18
    c1_fresh_root_count: int = 3
    c2_full_cache_entry_count: int = 28
    c2_active_entry_count: int = 18
    canonical_json_only: bool = True
    external_expected_commit_required: bool = True
    mutable_head_allowed: bool = False
    ground_module_allowed: bool = False

    def __post_init__(self) -> None:
        _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT()
        for value in (
            self.first_model_id,
            self.query_id,
            self.action_indexed_source_sha256,
        ):
            _cid(value, "durable protocol identity")
        first = _CANONICAL_DAG_REGISTERED_FIRST()
        query = _CANONICAL_DAG_REGISTERED_QUERY()
        if (
            self.first_model_id != first.model_id
            or self.query_id != query.query_id
            or self.action_indexed_profile_key != dag.PROFILE_KEY
            or self.action_indexed_source_sha256
            != EXPECTED_ACTION_INDEXED_SOURCE_SHA256
            or self.c1_lower_entry_count != 18
            or self.c1_fresh_root_count != 3
            or self.c2_full_cache_entry_count != 28
            or self.c2_active_entry_count != 18
            or self.canonical_json_only is not True
            or self.external_expected_commit_required is not True
            or self.mutable_head_allowed is not False
            or self.ground_module_allowed is not False
        ):
            raise DurableActionSwitchInvariantViolation(
                "durable action-switch protocol changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "first_model_id": self.first_model_id,
            "query_id": self.query_id,
            "action_indexed_profile_key": self.action_indexed_profile_key,
            "action_indexed_source_sha256": (
                self.action_indexed_source_sha256
            ),
            "c1_lower_entry_count": self.c1_lower_entry_count,
            "c1_fresh_root_count": self.c1_fresh_root_count,
            "c2_full_cache_entry_count": self.c2_full_cache_entry_count,
            "c2_active_entry_count": self.c2_active_entry_count,
            "canonical_json_only": self.canonical_json_only,
            "external_expected_commit_required": (
                self.external_expected_commit_required
            ),
            "mutable_head_allowed": self.mutable_head_allowed,
            "ground_module_allowed": self.ground_module_allowed,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("protocol", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


def registered_durable_action_switch_protocol_v1(
) -> DurableActionSwitchProtocolV1:
    _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT()
    first = _CANONICAL_DAG_REGISTERED_FIRST()
    query = _CANONICAL_DAG_REGISTERED_QUERY()
    return DurableActionSwitchProtocolV1(
        first.model_id,
        query.query_id,
        dag.PROFILE_KEY,
        EXPECTED_ACTION_INDEXED_SOURCE_SHA256,
    )


def _parse_protocol(document: Any) -> DurableActionSwitchProtocolV1:
    row = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "contract_version",
            "profile_key",
            "first_model_id",
            "query_id",
            "action_indexed_profile_key",
            "action_indexed_source_sha256",
            "c1_lower_entry_count",
            "c1_fresh_root_count",
            "c2_full_cache_entry_count",
            "c2_active_entry_count",
            "canonical_json_only",
            "external_expected_commit_required",
            "mutable_head_allowed",
            "ground_module_allowed",
            "protocol_id",
        },
        "durable action-switch protocol",
    )
    if (
        row["schema"] != "acfqp.h2_durable_action_switch_protocol.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["contract_version"] != CONTRACT_VERSION
        or row["profile_key"] != PROFILE_KEY
    ):
        raise DurableActionSwitchInvariantViolation("protocol schema changed")
    result = DurableActionSwitchProtocolV1(
        row["first_model_id"],
        row["query_id"],
        row["action_indexed_profile_key"],
        row["action_indexed_source_sha256"],
        row["c1_lower_entry_count"],
        row["c1_fresh_root_count"],
        row["c2_full_cache_entry_count"],
        row["c2_active_entry_count"],
        row["canonical_json_only"],
        row["external_expected_commit_required"],
        row["mutable_head_allowed"],
        row["ground_module_allowed"],
    )
    if not _same_document(result.to_document(), row):
        raise DurableActionSwitchInvariantViolation("protocol is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class DurableActionSwitchC1PayloadV1:
    protocol: DurableActionSwitchProtocolV1
    first_model_document: Mapping[str, Any]
    query_document: Mapping[str, Any]
    lower_node_documents: tuple[Mapping[str, Any], ...]
    cached_lower_node_ids: tuple[str, ...]
    active_lower_node_ids: tuple[str, ...]
    committed_runtime_snapshot_id: str
    lower_entry_count: int = 18
    persisted_root_artifact_count: int = 0
    cached_root_entry_count: int = 0

    def __post_init__(self) -> None:
        if type(self.protocol) is not DurableActionSwitchProtocolV1:
            raise DurableActionSwitchInvariantViolation(
                "C1 payload rejects substituted protocol"
            )
        for value in (
            *self.cached_lower_node_ids,
            *self.active_lower_node_ids,
            self.committed_runtime_snapshot_id,
        ):
            _cid(value, "C1 payload identity")
        model, query, runtime, execution = _derive_first_state()
        expected_nodes = tuple(node.node_id for node in execution.nodes)
        if (
            not _same_document(self.first_model_document, model.to_document())
            or not _same_document(self.query_document, query.to_document())
            or type(self.lower_node_documents) is not tuple
            or len(self.lower_node_documents) != 18
            or tuple(
                canonical_json_bytes(item)
                for item in self.lower_node_documents
            )
            != tuple(
                canonical_json_bytes(item.to_document())
                for item in execution.nodes
            )
            or self.protocol.first_model_id != model.model_id
            or self.protocol.query_id != query.query_id
            or self.cached_lower_node_ids != expected_nodes
            or self.active_lower_node_ids != expected_nodes
            or self.committed_runtime_snapshot_id != runtime.snapshot_id
            or self.lower_entry_count != 18
            or self.persisted_root_artifact_count != 0
            or self.cached_root_entry_count != 0
        ):
            raise DurableActionSwitchInvariantViolation(
                "C1 payload differs from the exact registered first execution"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_c1_payload.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol": self.protocol.to_document(),
            "first_model_document": dict(self.first_model_document),
            "query_document": dict(self.query_document),
            "lower_node_documents": [
                dict(item) for item in self.lower_node_documents
            ],
            "cached_lower_node_ids": list(self.cached_lower_node_ids),
            "active_lower_node_ids": list(self.active_lower_node_ids),
            "committed_runtime_snapshot_id": (
                self.committed_runtime_snapshot_id
            ),
            "lower_entry_count": self.lower_entry_count,
            "persisted_root_artifact_count": (
                self.persisted_root_artifact_count
            ),
            "cached_root_entry_count": self.cached_root_entry_count,
        }

    @property
    def payload_id(self) -> str:
        return _content_id("c1_payload", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "payload_id": self.payload_id}


def _materialize_c1_payload() -> DurableActionSwitchC1PayloadV1:
    protocol = registered_durable_action_switch_protocol_v1()
    model, query, runtime, execution = _derive_first_state()
    node_ids = tuple(node.node_id for node in execution.nodes)
    return DurableActionSwitchC1PayloadV1(
        protocol,
        model.to_document(),
        query.to_document(),
        tuple(node.to_document() for node in execution.nodes),
        node_ids,
        node_ids,
        runtime.snapshot_id,
    )


def _parse_c1_payload(document: Any) -> DurableActionSwitchC1PayloadV1:
    row = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "protocol",
            "first_model_document",
            "query_document",
            "lower_node_documents",
            "cached_lower_node_ids",
            "active_lower_node_ids",
            "committed_runtime_snapshot_id",
            "lower_entry_count",
            "persisted_root_artifact_count",
            "cached_root_entry_count",
            "payload_id",
        },
        "C1 payload",
    )
    if (
        row["schema"]
        != "acfqp.h2_durable_action_switch_c1_payload.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["lower_node_documents"]) is not list
        or type(row["cached_lower_node_ids"]) is not list
        or type(row["active_lower_node_ids"]) is not list
    ):
        raise DurableActionSwitchInvariantViolation("C1 payload schema changed")
    result = DurableActionSwitchC1PayloadV1(
        _parse_protocol(row["protocol"]),
        row["first_model_document"],
        row["query_document"],
        tuple(row["lower_node_documents"]),
        tuple(row["cached_lower_node_ids"]),
        tuple(row["active_lower_node_ids"]),
        row["committed_runtime_snapshot_id"],
        row["lower_entry_count"],
        row["persisted_root_artifact_count"],
        row["cached_root_entry_count"],
    )
    if not _same_document(result.to_document(), row):
        raise DurableActionSwitchInvariantViolation("C1 payload is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class DurableActionSwitchC1ManifestV1:
    protocol: DurableActionSwitchProtocolV1
    payload_id: str
    payload_sha256: str
    payload_size_bytes: int
    first_model_id: str
    query_id: str
    first_execution_id: str
    candidate_audit_ids: tuple[str, str]
    candidate_root_ids: tuple[str, str]
    proposal_id: str
    selected_root_id: str
    created_before_overlay_projection: bool = True
    created_before_ground_evidence: bool = True

    def __post_init__(self) -> None:
        if type(self.protocol) is not DurableActionSwitchProtocolV1:
            raise DurableActionSwitchInvariantViolation(
                "C1 manifest rejects substituted protocol"
            )
        for value in (
            self.payload_id,
            self.payload_sha256,
            self.first_model_id,
            self.query_id,
            self.first_execution_id,
            *self.candidate_audit_ids,
            *self.candidate_root_ids,
            self.proposal_id,
            self.selected_root_id,
        ):
            _cid(value, "C1 manifest identity")
        _integer(self.payload_size_bytes, "C1 payload size", 1)
        _, _, _, execution = _derive_first_state()
        if (
            self.first_model_id != self.protocol.first_model_id
            or self.query_id != self.protocol.query_id
            or self.first_execution_id != execution.execution_id
            or self.candidate_audit_ids
            != tuple(item.audit_id for item in execution.candidate_audits)
            or self.candidate_root_ids
            != tuple(item.root_id for item in execution.candidate_roots)
            or self.proposal_id != execution.proposal.proposal_id
            or self.selected_root_id != execution.selected_root.root_id
            or self.created_before_overlay_projection is not True
            or self.created_before_ground_evidence is not True
        ):
            raise DurableActionSwitchInvariantViolation(
                "C1 manifest temporal/semantic binding changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_c1_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol": self.protocol.to_document(),
            "payload_id": self.payload_id,
            "payload_sha256": self.payload_sha256,
            "payload_size_bytes": self.payload_size_bytes,
            "first_model_id": self.first_model_id,
            "query_id": self.query_id,
            "first_execution_id": self.first_execution_id,
            "candidate_audit_ids": list(self.candidate_audit_ids),
            "candidate_root_ids": list(self.candidate_root_ids),
            "proposal_id": self.proposal_id,
            "selected_root_id": self.selected_root_id,
            "created_before_overlay_projection": (
                self.created_before_overlay_projection
            ),
            "created_before_ground_evidence": (
                self.created_before_ground_evidence
            ),
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("c1_manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


def _parse_c1_manifest(document: Any) -> DurableActionSwitchC1ManifestV1:
    row = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "protocol",
            "payload_id",
            "payload_sha256",
            "payload_size_bytes",
            "first_model_id",
            "query_id",
            "first_execution_id",
            "candidate_audit_ids",
            "candidate_root_ids",
            "proposal_id",
            "selected_root_id",
            "created_before_overlay_projection",
            "created_before_ground_evidence",
            "manifest_id",
        },
        "C1 manifest",
    )
    if (
        row["schema"]
        != "acfqp.h2_durable_action_switch_c1_manifest.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["candidate_audit_ids"]) is not list
        or type(row["candidate_root_ids"]) is not list
        or len(row["candidate_audit_ids"]) != 2
        or len(row["candidate_root_ids"]) != 2
    ):
        raise DurableActionSwitchInvariantViolation("C1 manifest schema changed")
    result = DurableActionSwitchC1ManifestV1(
        _parse_protocol(row["protocol"]),
        row["payload_id"],
        row["payload_sha256"],
        row["payload_size_bytes"],
        row["first_model_id"],
        row["query_id"],
        row["first_execution_id"],
        tuple(row["candidate_audit_ids"]),  # type: ignore[arg-type]
        tuple(row["candidate_root_ids"]),  # type: ignore[arg-type]
        row["proposal_id"],
        row["selected_root_id"],
        row["created_before_overlay_projection"],
        row["created_before_ground_evidence"],
    )
    if not _same_document(result.to_document(), row):
        raise DurableActionSwitchInvariantViolation("C1 manifest is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class DurableActionSwitchCommitV1:
    checkpoint_kind: CheckpointKind
    protocol_id: str
    payload_id: str
    payload_sha256: str
    payload_size_bytes: int
    manifest_id: str
    manifest_sha256: str
    manifest_size_bytes: int
    generation: int
    previous_commit_id: str | None
    commit_complete: bool = True

    def __post_init__(self) -> None:
        if type(self.checkpoint_kind) is not CheckpointKind:
            raise DurableActionSwitchInvariantViolation(
                "commit checkpoint kind changed"
            )
        for value in (
            self.protocol_id,
            self.payload_id,
            self.payload_sha256,
            self.manifest_id,
            self.manifest_sha256,
        ):
            _cid(value, "durable commit identity")
        _integer(self.payload_size_bytes, "commit payload size", 1)
        _integer(self.manifest_size_bytes, "commit manifest size", 1)
        if self.previous_commit_id is not None:
            _cid(self.previous_commit_id, "previous commit")
        expected = (
            (1, None)
            if self.checkpoint_kind is CheckpointKind.C1_FIRST
            else (2, self.previous_commit_id)
        )
        if (
            (self.generation, self.previous_commit_id) != expected
            or (
                self.checkpoint_kind is CheckpointKind.C2_FINAL
                and self.previous_commit_id is None
            )
            or self.commit_complete is not True
        ):
            raise DurableActionSwitchInvariantViolation(
                "durable commit chain changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_commit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "checkpoint_kind": self.checkpoint_kind.value,
            "protocol_id": self.protocol_id,
            "payload_id": self.payload_id,
            "payload_sha256": self.payload_sha256,
            "payload_size_bytes": self.payload_size_bytes,
            "manifest_id": self.manifest_id,
            "manifest_sha256": self.manifest_sha256,
            "manifest_size_bytes": self.manifest_size_bytes,
            "generation": self.generation,
            "previous_commit_id": (
                self.previous_commit_id
                if self.previous_commit_id is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "INITIAL_C1_COMMIT",
                }
            ),
            "commit_complete": self.commit_complete,
        }

    @property
    def commit_id(self) -> str:
        return _content_id("commit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commit_id": self.commit_id}


def _parse_commit(document: Any) -> DurableActionSwitchCommitV1:
    row = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "checkpoint_kind",
            "protocol_id",
            "payload_id",
            "payload_sha256",
            "payload_size_bytes",
            "manifest_id",
            "manifest_sha256",
            "manifest_size_bytes",
            "generation",
            "previous_commit_id",
            "commit_complete",
            "commit_id",
        },
        "durable commit",
    )
    if (
        row["schema"] != "acfqp.h2_durable_action_switch_commit.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
    ):
        raise DurableActionSwitchInvariantViolation("commit schema changed")
    kind = CheckpointKind(row["checkpoint_kind"])
    previous = row["previous_commit_id"]
    if kind is CheckpointKind.C1_FIRST:
        if previous != {
            "kind": "NOT_APPLICABLE",
            "reason": "INITIAL_C1_COMMIT",
        }:
            raise DurableActionSwitchInvariantViolation(
                "C1 previous-commit typed null changed"
            )
        previous = None
    elif type(previous) is not str:
        raise DurableActionSwitchInvariantViolation(
            "C2 previous commit must be a content ID"
        )
    result = DurableActionSwitchCommitV1(
        kind,
        row["protocol_id"],
        row["payload_id"],
        row["payload_sha256"],
        row["payload_size_bytes"],
        row["manifest_id"],
        row["manifest_sha256"],
        row["manifest_size_bytes"],
        row["generation"],
        previous,
        row["commit_complete"],
    )
    if not _same_document(result.to_document(), row):
        raise DurableActionSwitchInvariantViolation("commit is not canonical")
    return result


def _atomic_write(path: Path, data: bytes) -> None:
    if not isinstance(path, Path) or type(data) is not bytes or not data:
        raise DurableActionSwitchInvariantViolation(
            "atomic write requires a Path and nonempty bytes"
        )
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise DurableActionSwitchInvariantViolation(
            "atomic write target is not fresh"
        )
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise DurableActionSwitchInvariantViolation(
            "atomic write temporary target already exists"
        )
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _read_stable_regular(path: Path) -> bytes:
    if not isinstance(path, Path):
        raise DurableActionSwitchInvariantViolation(
            "stable read target must be a Path"
        )
    before = path.lstat()
    if (
        path.is_symlink()
        or not path.is_file()
        or before.st_nlink != 1
        or before.st_size <= 0
    ):
        raise DurableActionSwitchInvariantViolation(
            "durable artifact is not a unique regular file"
        )
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = path.lstat()

    def signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mtime_ns,
            value.st_nlink,
        )

    if not (
        signature(before)
        == signature(opened)
        == signature(after_open)
        == signature(after_path)
    ):
        raise DurableActionSwitchInvariantViolation(
            "durable artifact changed during stable read"
        )
    return b"".join(chunks)


def _prepare_empty_checkpoint_store(store_root: Path) -> tuple[Path, Path]:
    if not isinstance(store_root, Path):
        raise DurableActionSwitchInvariantViolation(
            "checkpoint store root must be a pathlib Path"
        )
    if store_root.exists():
        if (
            store_root.is_symlink()
            or not store_root.is_dir()
            or any(store_root.iterdir())
        ):
            raise DurableActionSwitchInvariantViolation(
                "checkpoint writer requires an empty real directory"
            )
    else:
        store_root.mkdir(parents=True)
    blobs = store_root / "blobs"
    commits = store_root / "commits"
    blobs.mkdir()
    commits.mkdir()
    return blobs, commits


def _write_single_checkpoint(
    store_root: Path,
    payload_id: str,
    payload_document: Mapping[str, Any],
    manifest_id: str,
    manifest_document: Mapping[str, Any],
    commit: DurableActionSwitchCommitV1,
) -> None:
    blobs, commits = _prepare_empty_checkpoint_store(store_root)
    payload_bytes = canonical_json_bytes(dict(payload_document))
    manifest_bytes = canonical_json_bytes(dict(manifest_document))
    commit_bytes = canonical_json_bytes(commit.to_document())
    _atomic_write(blobs / f"{payload_id}.json", payload_bytes)
    _atomic_write(blobs / f"{manifest_id}.json", manifest_bytes)
    _atomic_write(commits / f"{commit.commit_id}.json", commit_bytes)
    if (store_root / "HEAD").exists():
        raise DurableActionSwitchInvariantViolation(
            "mutable HEAD is forbidden"
        )


def _read_single_checkpoint(
    store_root: Path,
    expected_commit_id: str,
) -> tuple[DurableActionSwitchCommitV1, bytes, bytes]:
    if not isinstance(store_root, Path):
        raise DurableActionSwitchInvariantViolation(
            "checkpoint loader root must be a pathlib Path"
        )
    expected = _cid(expected_commit_id, "externally expected commit")
    if (
        not store_root.exists()
        or store_root.is_symlink()
        or not store_root.is_dir()
        or {item.name for item in store_root.iterdir()}
        != {"blobs", "commits"}
    ):
        raise DurableActionSwitchInvariantViolation(
            "checkpoint store topology changed or contains HEAD"
        )
    blobs = store_root / "blobs"
    commits = store_root / "commits"
    if (
        blobs.is_symlink()
        or commits.is_symlink()
        or not blobs.is_dir()
        or not commits.is_dir()
        or {item.name for item in commits.iterdir()} != {f"{expected}.json"}
    ):
        raise DurableActionSwitchInvariantViolation(
            "checkpoint commit directory is not exact"
        )
    commit_bytes = _read_stable_regular(commits / f"{expected}.json")
    commit = _parse_commit(loads_canonical_json(commit_bytes))
    if commit.commit_id != expected:
        raise DurableActionSwitchInvariantViolation(
            "external expected commit does not match bytes"
        )
    expected_blobs = {
        f"{commit.payload_id}.json",
        f"{commit.manifest_id}.json",
    }
    if {item.name for item in blobs.iterdir()} != expected_blobs:
        raise DurableActionSwitchInvariantViolation(
            "checkpoint blob directory is not exact"
        )
    payload_bytes = _read_stable_regular(blobs / f"{commit.payload_id}.json")
    manifest_bytes = _read_stable_regular(
        blobs / f"{commit.manifest_id}.json"
    )
    if (
        len(payload_bytes) != commit.payload_size_bytes
        or hashlib.sha256(payload_bytes).hexdigest()
        != commit.payload_sha256
        or len(manifest_bytes) != commit.manifest_size_bytes
        or hashlib.sha256(manifest_bytes).hexdigest()
        != commit.manifest_sha256
    ):
        raise DurableActionSwitchInvariantViolation(
            "checkpoint blob size or SHA changed"
        )
    return commit, payload_bytes, manifest_bytes


@dataclass(frozen=True, slots=True)
class VerifiedDurableActionSwitchC1LeaseV1:
    expected_commit_id: str
    commit: DurableActionSwitchCommitV1
    manifest: DurableActionSwitchC1ManifestV1
    payload: DurableActionSwitchC1PayloadV1
    first_model: dag.ActionIndexedH2ModelV1
    query: dag.ActionIndexedH2QueryV1
    first_execution: dag.ActionIndexedEpochExecutionV1
    stored_lower_nodes: tuple[dag.ActionIndexedProofNodeV1, ...]
    semantic_replay_only: bool = True
    ground_transition_calls: int = 0

    def __post_init__(self) -> None:
        _cid(self.expected_commit_id, "verified C1 lease commit")
        if (
            type(self.commit) is not DurableActionSwitchCommitV1
            or type(self.manifest) is not DurableActionSwitchC1ManifestV1
            or type(self.payload) is not DurableActionSwitchC1PayloadV1
            or type(self.first_model) is not dag.ActionIndexedH2ModelV1
            or type(self.query) is not dag.ActionIndexedH2QueryV1
            or type(self.first_execution)
            is not dag.ActionIndexedEpochExecutionV1
            or type(self.stored_lower_nodes) is not tuple
            or any(
                type(item) is not dag.ActionIndexedProofNodeV1
                for item in self.stored_lower_nodes
            )
            or len(self.stored_lower_nodes) != 18
            or self.expected_commit_id != self.commit.commit_id
            or self.commit.checkpoint_kind is not CheckpointKind.C1_FIRST
            or self.commit.payload_id != self.payload.payload_id
            or self.commit.manifest_id != self.manifest.manifest_id
            or self.manifest.payload_id != self.payload.payload_id
            or self.manifest.protocol.protocol_id
            != self.payload.protocol.protocol_id
            or self.first_model.model_id != self.manifest.first_model_id
            or self.query.query_id != self.manifest.query_id
            or self.first_execution.execution_id
            != self.manifest.first_execution_id
            or tuple(
                item.to_document() for item in self.stored_lower_nodes
            )
            != tuple(self.payload.lower_node_documents)
            or tuple(item.node_id for item in self.stored_lower_nodes)
            != self.payload.cached_lower_node_ids
            or self.semantic_replay_only is not True
            or self.ground_transition_calls != 0
        ):
            raise DurableActionSwitchInvariantViolation(
                "verified C1 lease binding changed"
            )


def write_durable_action_switch_c1_v1(
    store_root: Path,
) -> DurableActionSwitchCommitV1:
    """Commit C1 before any overlay or ground evidence exists."""

    _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT()
    payload = _materialize_c1_payload()
    payload_bytes = canonical_json_bytes(payload.to_document())
    _, _, _, execution = _derive_first_state()
    manifest = DurableActionSwitchC1ManifestV1(
        payload.protocol,
        payload.payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        payload.protocol.first_model_id,
        payload.protocol.query_id,
        execution.execution_id,
        tuple(item.audit_id for item in execution.candidate_audits),
        tuple(item.root_id for item in execution.candidate_roots),
        execution.proposal.proposal_id,
        execution.selected_root.root_id,
    )
    manifest_bytes = canonical_json_bytes(manifest.to_document())
    commit = DurableActionSwitchCommitV1(
        CheckpointKind.C1_FIRST,
        payload.protocol.protocol_id,
        payload.payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        manifest.manifest_id,
        hashlib.sha256(manifest_bytes).hexdigest(),
        len(manifest_bytes),
        1,
        None,
    )
    _write_single_checkpoint(
        store_root,
        payload.payload_id,
        payload.to_document(),
        manifest.manifest_id,
        manifest.to_document(),
        commit,
    )
    loaded = load_verified_durable_action_switch_c1_v1(
        store_root, commit.commit_id
    )
    if loaded.commit.to_document() != commit.to_document():
        raise DurableActionSwitchInvariantViolation("C1 reread changed")
    return commit


def load_verified_durable_action_switch_c1_v1(
    store_root: Path,
    expected_commit_id: str,
) -> VerifiedDurableActionSwitchC1LeaseV1:
    """Load C1 from an externally selected immutable commit."""

    _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT()
    commit, payload_bytes, manifest_bytes = _read_single_checkpoint(
        store_root, expected_commit_id
    )
    if commit.checkpoint_kind is not CheckpointKind.C1_FIRST:
        raise DurableActionSwitchInvariantViolation(
            "C1 loader rejects a non-C1 commit"
        )
    payload = _parse_c1_payload(loads_canonical_json(payload_bytes))
    manifest = _parse_c1_manifest(loads_canonical_json(manifest_bytes))
    if (
        payload.payload_id != commit.payload_id
        or manifest.manifest_id != commit.manifest_id
        or manifest.payload_id != payload.payload_id
        or manifest.protocol.protocol_id != commit.protocol_id
        or payload.protocol.protocol_id != commit.protocol_id
        or manifest.payload_sha256 != commit.payload_sha256
        or manifest.payload_size_bytes != commit.payload_size_bytes
    ):
        raise DurableActionSwitchInvariantViolation(
            "C1 content-addressed identity chain changed"
        )
    model, query, _, execution = _derive_first_state()
    stored_nodes = tuple(
        _CANONICAL_DAG_PARSE_NODE(item)
        for item in payload.lower_node_documents
    )
    if tuple(item.to_document() for item in stored_nodes) != tuple(
        item.to_document() for item in execution.nodes
    ):
        raise DurableActionSwitchInvariantViolation(
            "C1 durable lower objects differ from semantic validation"
        )
    return VerifiedDurableActionSwitchC1LeaseV1(
        commit.commit_id,
        commit,
        manifest,
        payload,
        model,
        query,
        execution,
        stored_nodes,
    )


@dataclass(frozen=True, slots=True)
class DurableActionSwitchWarmReplayV1:
    """Checkpoint-local lower hits plus freshly reconstructed roots.

    Semantic validation work is deliberately separate from operational durable
    reuse.  This wrapper never rewrites an ``ActionIndexedEpochExecutionV1``:
    the historical first execution remains 18/0 and the historical final
    execution remains 10/8.
    """

    checkpoint_kind: CheckpointKind
    commit_id: str
    payload_id: str
    model_id: str
    query_id: str
    source_execution_id: str
    restore_binding_id: str
    restored_root_replay_id: str
    active_lower_node_ids: tuple[str, ...]
    selected_action: str
    selected_schedule_code: str
    certified: bool
    semantic_validation_lower_obligations: int = 18
    operational_lower_computes: int = 0
    operational_lower_hits: int = 18
    roots_loaded: int = 0
    fresh_root_computes: int = 3

    def __post_init__(self) -> None:
        if type(self.checkpoint_kind) is not CheckpointKind:
            raise DurableActionSwitchInvariantViolation(
                "warm replay checkpoint kind changed"
            )
        for value in (
            self.commit_id,
            self.payload_id,
            self.model_id,
            self.query_id,
            self.source_execution_id,
            self.restore_binding_id,
            self.restored_root_replay_id,
            *self.active_lower_node_ids,
        ):
            _cid(value, "warm replay identity")
        if (
            len(self.active_lower_node_ids) != 18
            or len(set(self.active_lower_node_ids)) != 18
            or self.selected_action not in ("N", "M")
            or self.selected_schedule_code
            != ("A0A0" if self.selected_action == "N" else "A0A1")
            or type(self.certified) is not bool
            or self.semantic_validation_lower_obligations != 18
            or self.operational_lower_computes != 0
            or self.operational_lower_hits != 18
            or self.roots_loaded != 0
            or self.fresh_root_computes != 3
        ):
            raise DurableActionSwitchInvariantViolation(
                "warm replay work split changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_warm_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "checkpoint_kind": self.checkpoint_kind.value,
            "commit_id": self.commit_id,
            "payload_id": self.payload_id,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "source_execution_id": self.source_execution_id,
            "restore_binding_id": self.restore_binding_id,
            "restored_root_replay_id": self.restored_root_replay_id,
            "active_lower_node_ids": list(self.active_lower_node_ids),
            "selected_action": self.selected_action,
            "selected_schedule_code": self.selected_schedule_code,
            "certified": self.certified,
            "semantic_validation_lower_obligations": (
                self.semantic_validation_lower_obligations
            ),
            "operational_lower_computes": self.operational_lower_computes,
            "operational_lower_hits": self.operational_lower_hits,
            "roots_loaded": self.roots_loaded,
            "fresh_root_computes": self.fresh_root_computes,
        }

    @property
    def replay_id(self) -> str:
        return _content_id("warm_replay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


@dataclass(frozen=True, slots=True)
class DurableActionSwitchP1AttestationV1:
    warm_replay: DurableActionSwitchWarmReplayV1
    c1_commit_id: str
    c1_payload_id: str
    first_execution_id: str
    model_id: str
    query_id: str
    selected_action: str
    selected_schedule_code: str
    policy_reward_lower: Fraction
    policy_failure_upper: Fraction
    normalized_regret: Fraction
    coverage_passed: bool
    certified: bool
    lower_computed: int
    lower_reused: int
    fresh_roots: int
    matching_buffer_imported: bool = False
    ground_transition_calls: int = 0

    def __post_init__(self) -> None:
        if type(self.warm_replay) is not DurableActionSwitchWarmReplayV1:
            raise DurableActionSwitchInvariantViolation(
                "P1 requires an exact warm replay wrapper"
            )
        for value in (
            self.c1_commit_id,
            self.c1_payload_id,
            self.first_execution_id,
            self.model_id,
            self.query_id,
        ):
            _cid(value, "P1 attestation identity")
        for name in (
            "policy_reward_lower",
            "policy_failure_upper",
            "normalized_regret",
        ):
            object.__setattr__(
                self, name, _fraction(getattr(self, name), f"P1 {name}")
            )
        for name in ("lower_computed", "lower_reused", "fresh_roots"):
            _integer(getattr(self, name), f"P1 {name}")
        if (
            self.selected_action != "N"
            or self.selected_schedule_code != "A0A0"
            or self.policy_reward_lower != 0
            or self.policy_failure_upper != 0
            or self.normalized_regret != Fraction(3, 4)
            or self.coverage_passed is not True
            or self.certified is not False
            or (self.lower_computed, self.lower_reused, self.fresh_roots)
            != (0, 18, 3)
            or self.warm_replay.checkpoint_kind
            is not CheckpointKind.C1_FIRST
            or self.warm_replay.commit_id != self.c1_commit_id
            or self.warm_replay.payload_id != self.c1_payload_id
            or self.warm_replay.source_execution_id
            != self.first_execution_id
            or self.warm_replay.selected_action != self.selected_action
            or self.warm_replay.certified is not self.certified
            or self.matching_buffer_imported is not False
            or self.ground_transition_calls != 0
        ):
            raise DurableActionSwitchInvariantViolation(
                "P1 failed-N attestation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_p1_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "warm_replay": self.warm_replay.to_document(),
            "c1_commit_id": self.c1_commit_id,
            "c1_payload_id": self.c1_payload_id,
            "first_execution_id": self.first_execution_id,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "selected_action": self.selected_action,
            "selected_schedule_code": self.selected_schedule_code,
            "policy_reward_lower": _fdoc(self.policy_reward_lower),
            "policy_failure_upper": _fdoc(self.policy_failure_upper),
            "normalized_regret": _fdoc(self.normalized_regret),
            "coverage_passed": self.coverage_passed,
            "certified": self.certified,
            "lower_computed": self.lower_computed,
            "lower_reused": self.lower_reused,
            "fresh_roots": self.fresh_roots,
            "matching_buffer_imported": self.matching_buffer_imported,
            "ground_transition_calls": self.ground_transition_calls,
        }

    @property
    def attestation_id(self) -> str:
        return _content_id("p1_attestation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def _derive_p1(
    lease: VerifiedDurableActionSwitchC1LeaseV1,
) -> DurableActionSwitchP1AttestationV1:
    if type(lease) is not VerifiedDurableActionSwitchC1LeaseV1:
        raise DurableActionSwitchInvariantViolation(
            "P1 requires an exact verified C1 lease"
        )
    _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT()
    runtime, restore = (
        _CANONICAL_DAG_RESTORE_FIRST(
            lease.first_model,
            lease.query,
            lease.stored_lower_nodes,
            lease.first_execution.execution_id,
        )
    )
    roots = _CANONICAL_DAG_REBUILD_ROOTS(
        lease.first_model,
        lease.query,
        runtime,
        restore,
    )
    audit = roots.candidate_audits[0]
    warm = DurableActionSwitchWarmReplayV1(
        CheckpointKind.C1_FIRST,
        lease.commit.commit_id,
        lease.payload.payload_id,
        lease.first_model.model_id,
        lease.query.query_id,
        lease.first_execution.execution_id,
        restore.restore_id,
        roots.replay_id,
        roots.ordered_lower_node_ids,
        roots.proposal.selected_action.value,
        roots.proposal.selected_schedule_code,
        audit.certified,
    )
    return DurableActionSwitchP1AttestationV1(
        warm,
        lease.commit.commit_id,
        lease.payload.payload_id,
        lease.first_execution.execution_id,
        lease.first_model.model_id,
        lease.query.query_id,
        roots.proposal.selected_action.value,
        roots.proposal.selected_schedule_code,
        audit.policy_reward_lower,
        audit.policy_failure_upper,
        audit.normalized_regret,
        audit.coverage_passed,
        audit.certified,
        0,
        18,
        roots.fresh_root_computed,
    )


@dataclass(frozen=True, slots=True)
class DurableActionSwitchOverlayProjectionV1:
    source_result_id: str
    fixture_id: str
    evidence_bundle_id: str
    row_evidence_id: str
    overlay_build_id: str
    first_query_local_model_id: str
    final_query_local_model_id: str
    m_ground_row_id: str
    m_state_id: str
    m_action_id: str
    m_row_document: Mapping[str, Any]
    exact_projected_row_count: int = 1
    source_ground_transition_calls: int = 1
    immutable_append_only: bool = True
    live_ground_authority_transportable: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.source_result_id,
            self.fixture_id,
            self.evidence_bundle_id,
            self.row_evidence_id,
            self.overlay_build_id,
            self.first_query_local_model_id,
            self.final_query_local_model_id,
            self.m_ground_row_id,
            self.m_state_id,
            self.m_action_id,
        ):
            _cid(value, "overlay projection identity")
        final = _CANONICAL_DAG_REGISTERED_FINAL()
        expected_m = final.row(dag.GroundRowName.M)
        if (
            not _same_document(self.m_row_document, expected_m.to_document())
            or self.exact_projected_row_count != 1
            or self.source_ground_transition_calls != 1
            or self.immutable_append_only is not True
            or self.live_ground_authority_transportable is not False
        ):
            raise DurableActionSwitchInvariantViolation(
                "overlay projection is not the exact immutable M row"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_overlay_projection.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_result_id": self.source_result_id,
            "fixture_id": self.fixture_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "row_evidence_id": self.row_evidence_id,
            "overlay_build_id": self.overlay_build_id,
            "first_query_local_model_id": self.first_query_local_model_id,
            "final_query_local_model_id": self.final_query_local_model_id,
            "m_ground_row_id": self.m_ground_row_id,
            "m_state_id": self.m_state_id,
            "m_action_id": self.m_action_id,
            "m_row_document": dict(self.m_row_document),
            "exact_projected_row_count": self.exact_projected_row_count,
            "source_ground_transition_calls": (
                self.source_ground_transition_calls
            ),
            "immutable_append_only": self.immutable_append_only,
            "live_ground_authority_transportable": (
                self.live_ground_authority_transportable
            ),
        }

    @property
    def projection_id(self) -> str:
        return _content_id("overlay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "projection_id": self.projection_id}


def freeze_durable_action_switch_overlay_projection_v1(
    *,
    source_result_id: str,
    fixture_id: str,
    evidence_bundle_id: str,
    row_evidence_id: str,
    overlay_build_id: str,
    first_query_local_model_id: str,
    final_query_local_model_id: str,
    m_ground_row_id: str,
    m_state_id: str,
    m_action_id: str,
) -> DurableActionSwitchOverlayProjectionV1:
    """Freeze opaque live-source IDs and the exact registered final M row."""

    m_row = _CANONICAL_DAG_REGISTERED_FINAL().row(
        dag.GroundRowName.M
    )
    return DurableActionSwitchOverlayProjectionV1(
        source_result_id,
        fixture_id,
        evidence_bundle_id,
        row_evidence_id,
        overlay_build_id,
        first_query_local_model_id,
        final_query_local_model_id,
        m_ground_row_id,
        m_state_id,
        m_action_id,
        m_row.to_document(),
    )


def _parse_overlay(
    document: Any,
) -> DurableActionSwitchOverlayProjectionV1:
    row = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "source_result_id",
            "fixture_id",
            "evidence_bundle_id",
            "row_evidence_id",
            "overlay_build_id",
            "first_query_local_model_id",
            "final_query_local_model_id",
            "m_ground_row_id",
            "m_state_id",
            "m_action_id",
            "m_row_document",
            "exact_projected_row_count",
            "source_ground_transition_calls",
            "immutable_append_only",
            "live_ground_authority_transportable",
            "projection_id",
        },
        "overlay projection",
    )
    if (
        row["schema"]
        != "acfqp.h2_durable_action_switch_overlay_projection.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
    ):
        raise DurableActionSwitchInvariantViolation(
            "overlay projection schema changed"
        )
    result = DurableActionSwitchOverlayProjectionV1(
        row["source_result_id"],
        row["fixture_id"],
        row["evidence_bundle_id"],
        row["row_evidence_id"],
        row["overlay_build_id"],
        row["first_query_local_model_id"],
        row["final_query_local_model_id"],
        row["m_ground_row_id"],
        row["m_state_id"],
        row["m_action_id"],
        row["m_row_document"],
        row["exact_projected_row_count"],
        row["source_ground_transition_calls"],
        row["immutable_append_only"],
        row["live_ground_authority_transportable"],
    )
    if not _same_document(result.to_document(), row):
        raise DurableActionSwitchInvariantViolation(
            "overlay projection is not canonical"
        )
    return result


def write_durable_action_switch_overlay_projection_v1(
    projection: DurableActionSwitchOverlayProjectionV1,
    store_root: Path,
) -> str:
    if type(projection) is not DurableActionSwitchOverlayProjectionV1:
        raise DurableActionSwitchInvariantViolation(
            "overlay writer requires the exact typed projection"
        )
    projection.__post_init__()
    if not isinstance(store_root, Path):
        raise DurableActionSwitchInvariantViolation(
            "overlay store root must be a Path"
        )
    if store_root.exists():
        if (
            store_root.is_symlink()
            or not store_root.is_dir()
            or any(store_root.iterdir())
        ):
            raise DurableActionSwitchInvariantViolation(
                "overlay writer requires an empty real directory"
            )
    else:
        store_root.mkdir(parents=True)
    _atomic_write(
        store_root / f"{projection.projection_id}.json",
        canonical_json_bytes(projection.to_document()),
    )
    loaded = load_durable_action_switch_overlay_projection_v1(
        store_root, projection.projection_id
    )
    if loaded.to_document() != projection.to_document():
        raise DurableActionSwitchInvariantViolation("overlay reread changed")
    return projection.projection_id


def load_durable_action_switch_overlay_projection_v1(
    store_root: Path,
    expected_projection_id: str,
) -> DurableActionSwitchOverlayProjectionV1:
    expected = _cid(expected_projection_id, "externally expected overlay")
    if (
        not isinstance(store_root, Path)
        or not store_root.exists()
        or store_root.is_symlink()
        or not store_root.is_dir()
        or {item.name for item in store_root.iterdir()}
        != {f"{expected}.json"}
    ):
        raise DurableActionSwitchInvariantViolation(
            "overlay store topology changed"
        )
    projection = _parse_overlay(
        loads_canonical_json(
            _read_stable_regular(store_root / f"{expected}.json")
        )
    )
    if projection.projection_id != expected:
        raise DurableActionSwitchInvariantViolation(
            "external expected overlay does not match bytes"
        )
    return projection


def _derive_switch_state(
    lease: VerifiedDurableActionSwitchC1LeaseV1,
    projection: DurableActionSwitchOverlayProjectionV1,
) -> tuple[
    dag.ActionIndexedProofRuntimeV1,
    dag.ActionIndexedEpochExecutionV1,
    dag.ActionIndexedFirstRuntimeRestoreV1,
    dag.ActionIndexedH2ModelV1,
    dag.ActionIndexedModelDeltaV1,
    dag.ActionIndexedPreExecutionInvalidationV1,
    dag.ActionIndexedEpochExecutionV1,
    dag.ActionIndexedInvalidationManifestV1,
]:
    if (
        type(lease) is not VerifiedDurableActionSwitchC1LeaseV1
        or type(projection) is not DurableActionSwitchOverlayProjectionV1
    ):
        raise DurableActionSwitchInvariantViolation(
            "switch derivation requires exact C1 and overlay artifacts"
        )
    _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT()
    projection.__post_init__()
    first_model = _CANONICAL_DAG_REGISTERED_FIRST()
    final_model = _CANONICAL_DAG_REGISTERED_FINAL()
    query = _CANONICAL_DAG_REGISTERED_QUERY()
    if not _same_document(
        projection.m_row_document,
        final_model.row(dag.GroundRowName.M).to_document(),
    ):
        raise DurableActionSwitchInvariantViolation(
            "projection M row differs from final model"
        )
    first = lease.first_execution
    if (
        first.to_document() != lease.first_execution.to_document()
        or (first.work.lower_computed, first.work.lower_reused) != (18, 0)
    ):
        raise DurableActionSwitchInvariantViolation(
            "fresh continuation first execution differs from C1"
        )
    runtime, restore = (
        _CANONICAL_DAG_RESTORE_FIRST(
        first_model,
        query,
        lease.stored_lower_nodes,
        first.execution_id,
        )
    )
    if (
        restore.lower_entries_loaded != 18
        or restore.roots_loaded != 0
        or runtime.cache_size != 18
    ):
        raise DurableActionSwitchInvariantViolation(
            "durable first-runtime restore changed"
        )
    delta, pre = _CANONICAL_DAG_DERIVE_PRE(
        first_model, final_model, first
    )
    _CANONICAL_DAG_AUTHORIZE_FINAL(runtime, pre)
    final = _CANONICAL_DAG_EXECUTE(final_model, query, runtime)
    verified_delta, invalidation = (
        _CANONICAL_DAG_DERIVE_POST(
            first_model, final_model, first, final
        )
    )
    if (
        delta.to_document() != verified_delta.to_document()
        or (final.work.lower_computed, final.work.lower_reused) != (10, 8)
        or runtime.cache_size != 28
    ):
        raise DurableActionSwitchInvariantViolation(
            "fresh continuation final proof work changed"
        )
    return (
        runtime,
        first,
        restore,
        final_model,
        delta,
        pre,
        final,
        invalidation,
    )


@dataclass(frozen=True, slots=True)
class DurableActionSwitchP2ContinuationV1:
    c1_commit_id: str
    c1_payload_id: str
    overlay_projection_id: str
    overlay_source_result_id: str
    first_execution_id: str
    first_restore_document: Mapping[str, Any]
    final_model_id: str
    delta_document: Mapping[str, Any]
    preexecution_invalidation_document: Mapping[str, Any]
    final_execution_document: Mapping[str, Any]
    invalidation_document: Mapping[str, Any]
    first_action: str
    final_action: str
    first_schedule_code: str
    final_schedule_code: str
    first_certified: bool
    final_certified: bool
    source_first_execution_lower_computed: int
    source_first_execution_lower_reused: int
    semantic_validation_first_lower_obligations: int
    operational_first_lower_computes: int
    operational_first_lower_hits: int
    final_lower_computed: int
    final_lower_reused: int
    full_cache_node_ids: tuple[str, ...]
    active_final_bindings: tuple[tuple[str, str, str], ...]
    committed_final_runtime_snapshot_id: str
    matching_buffer_imported: bool = False
    worker_ground_transition_calls: int = 0

    def __post_init__(self) -> None:
        for value in (
            self.c1_commit_id,
            self.c1_payload_id,
            self.overlay_projection_id,
            self.overlay_source_result_id,
            self.first_execution_id,
            self.final_model_id,
            self.committed_final_runtime_snapshot_id,
            *self.full_cache_node_ids,
        ):
            _cid(value, "P2 continuation identity")
        restore_id = _cid(
            _exact_mapping(
                self.first_restore_document,
                set(self.first_restore_document),
                "P2 first restore",
            )["restore_id"],
            "P2 first restore",
        )
        if restore_id == self.first_execution_id:
            raise DurableActionSwitchInvariantViolation(
                "P2 restore receipt must be distinct from its source execution"
            )
        for address, key_id, node_id in self.active_final_bindings:
            _text(address, "P2 active address")
            _cid(key_id, "P2 active node key")
            _cid(node_id, "P2 active node")
        for name in (
            "source_first_execution_lower_computed",
            "source_first_execution_lower_reused",
            "semantic_validation_first_lower_obligations",
            "operational_first_lower_computes",
            "operational_first_lower_hits",
            "final_lower_computed",
            "final_lower_reused",
        ):
            _integer(getattr(self, name), f"P2 {name}")
        if (
            self.first_action != "N"
            or self.final_action != "M"
            or self.first_schedule_code != "A0A0"
            or self.final_schedule_code != "A0A1"
            or self.first_certified is not False
            or self.final_certified is not True
            or (
                self.source_first_execution_lower_computed,
                self.source_first_execution_lower_reused,
                self.semantic_validation_first_lower_obligations,
                self.operational_first_lower_computes,
                self.operational_first_lower_hits,
                self.final_lower_computed,
                self.final_lower_reused,
            )
            != (18, 0, 18, 0, 18, 10, 8)
            or len(self.full_cache_node_ids) != 28
            or len(set(self.full_cache_node_ids)) != 28
            or self.full_cache_node_ids != tuple(sorted(self.full_cache_node_ids))
            or len(self.active_final_bindings) != 18
            or tuple(item[0] for item in self.active_final_bindings)
            != tuple(address.value for address in dag.ADDRESS_ORDER)
            or len({item[1] for item in self.active_final_bindings}) != 18
            or len({item[2] for item in self.active_final_bindings}) != 18
            or self.matching_buffer_imported is not False
            or self.worker_ground_transition_calls != 0
        ):
            raise DurableActionSwitchInvariantViolation(
                "P2 strict continuation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_p2_continuation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "c1_commit_id": self.c1_commit_id,
            "c1_payload_id": self.c1_payload_id,
            "overlay_projection_id": self.overlay_projection_id,
            "overlay_source_result_id": self.overlay_source_result_id,
            "first_execution_id": self.first_execution_id,
            "first_restore_document": dict(self.first_restore_document),
            "final_model_id": self.final_model_id,
            "delta_document": dict(self.delta_document),
            "preexecution_invalidation_document": dict(
                self.preexecution_invalidation_document
            ),
            "final_execution_document": dict(self.final_execution_document),
            "invalidation_document": dict(self.invalidation_document),
            "first_action": self.first_action,
            "final_action": self.final_action,
            "first_schedule_code": self.first_schedule_code,
            "final_schedule_code": self.final_schedule_code,
            "first_certified": self.first_certified,
            "final_certified": self.final_certified,
            "source_first_execution_lower_computed": (
                self.source_first_execution_lower_computed
            ),
            "source_first_execution_lower_reused": (
                self.source_first_execution_lower_reused
            ),
            "semantic_validation_first_lower_obligations": (
                self.semantic_validation_first_lower_obligations
            ),
            "operational_first_lower_computes": (
                self.operational_first_lower_computes
            ),
            "operational_first_lower_hits": (
                self.operational_first_lower_hits
            ),
            "final_lower_computed": self.final_lower_computed,
            "final_lower_reused": self.final_lower_reused,
            "full_cache_node_ids": list(self.full_cache_node_ids),
            "active_final_bindings": [
                {
                    "address": address,
                    "node_key_id": key_id,
                    "node_id": node_id,
                }
                for address, key_id, node_id in self.active_final_bindings
            ],
            "committed_final_runtime_snapshot_id": (
                self.committed_final_runtime_snapshot_id
            ),
            "matching_buffer_imported": self.matching_buffer_imported,
            "worker_ground_transition_calls": (
                self.worker_ground_transition_calls
            ),
        }

    @property
    def continuation_id(self) -> str:
        return _content_id("p2_continuation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "continuation_id": self.continuation_id}


def _derive_p2(
    lease: VerifiedDurableActionSwitchC1LeaseV1,
    projection: DurableActionSwitchOverlayProjectionV1,
) -> DurableActionSwitchP2ContinuationV1:
    (
        runtime,
        first,
        restore,
        final_model,
        delta,
        pre,
        final,
        invalidation,
    ) = _derive_switch_state(lease, projection)
    first_audit = first.candidate_audits[0]
    final_audit = final.candidate_audits[1]
    return DurableActionSwitchP2ContinuationV1(
        lease.commit.commit_id,
        lease.payload.payload_id,
        projection.projection_id,
        projection.source_result_id,
        first.execution_id,
        restore.to_document(),
        final_model.model_id,
        delta.to_document(),
        pre.to_document(),
        final.to_document(),
        invalidation.to_document(),
        first.proposal.selected_action.value,
        final.proposal.selected_action.value,
        first.proposal.selected_schedule_code,
        final.proposal.selected_schedule_code,
        first_audit.certified,
        final_audit.certified,
        first.work.lower_computed,
        first.work.lower_reused,
        18,
        0,
        restore.lower_entries_loaded,
        final.work.lower_computed,
        final.work.lower_reused,
        _ordered_unique_node_ids(first, final),
        _active_bindings(final),
        runtime.snapshot_id,
    )


def _parse_active_bindings(
    value: Any,
    where: str,
) -> tuple[tuple[str, str, str], ...]:
    if type(value) is not list:
        raise DurableActionSwitchInvariantViolation(
            f"{where} must be a JSON array"
        )
    result: list[tuple[str, str, str]] = []
    for item in value:
        row = _exact_mapping(
            item,
            {"address", "node_key_id", "node_id"},
            f"{where} item",
        )
        result.append(
            (row["address"], row["node_key_id"], row["node_id"])
        )
    return tuple(result)


def _parse_p2(
    document: Any,
) -> DurableActionSwitchP2ContinuationV1:
    row = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "c1_commit_id",
            "c1_payload_id",
            "overlay_projection_id",
            "overlay_source_result_id",
            "first_execution_id",
            "first_restore_document",
            "final_model_id",
            "delta_document",
            "preexecution_invalidation_document",
            "final_execution_document",
            "invalidation_document",
            "first_action",
            "final_action",
            "first_schedule_code",
            "final_schedule_code",
            "first_certified",
            "final_certified",
            "source_first_execution_lower_computed",
            "source_first_execution_lower_reused",
            "semantic_validation_first_lower_obligations",
            "operational_first_lower_computes",
            "operational_first_lower_hits",
            "final_lower_computed",
            "final_lower_reused",
            "full_cache_node_ids",
            "active_final_bindings",
            "committed_final_runtime_snapshot_id",
            "matching_buffer_imported",
            "worker_ground_transition_calls",
            "continuation_id",
        },
        "P2 continuation",
    )
    if (
        row["schema"]
        != "acfqp.h2_durable_action_switch_p2_continuation.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["full_cache_node_ids"]) is not list
    ):
        raise DurableActionSwitchInvariantViolation("P2 schema changed")
    result = DurableActionSwitchP2ContinuationV1(
        row["c1_commit_id"],
        row["c1_payload_id"],
        row["overlay_projection_id"],
        row["overlay_source_result_id"],
        row["first_execution_id"],
        row["first_restore_document"],
        row["final_model_id"],
        row["delta_document"],
        row["preexecution_invalidation_document"],
        row["final_execution_document"],
        row["invalidation_document"],
        row["first_action"],
        row["final_action"],
        row["first_schedule_code"],
        row["final_schedule_code"],
        row["first_certified"],
        row["final_certified"],
        row["source_first_execution_lower_computed"],
        row["source_first_execution_lower_reused"],
        row["semantic_validation_first_lower_obligations"],
        row["operational_first_lower_computes"],
        row["operational_first_lower_hits"],
        row["final_lower_computed"],
        row["final_lower_reused"],
        tuple(row["full_cache_node_ids"]),
        _parse_active_bindings(
            row["active_final_bindings"], "P2 active bindings"
        ),
        row["committed_final_runtime_snapshot_id"],
        row["matching_buffer_imported"],
        row["worker_ground_transition_calls"],
    )
    if not _same_document(result.to_document(), row):
        raise DurableActionSwitchInvariantViolation("P2 is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class DurableActionSwitchC2PayloadV1:
    protocol: DurableActionSwitchProtocolV1
    c1_commit_id: str
    overlay_projection_id: str
    p2_continuation_id: str
    final_model_id: str
    final_execution_id: str
    delta_id: str
    preexecution_invalidation_id: str
    invalidation_id: str
    lower_node_documents: tuple[Mapping[str, Any], ...]
    full_cache_node_ids: tuple[str, ...]
    active_final_bindings: tuple[tuple[str, str, str], ...]
    committed_final_runtime_snapshot_id: str
    full_cache_entry_count: int = 28
    active_final_entry_count: int = 18
    cached_root_entry_count: int = 0

    def __post_init__(self) -> None:
        if type(self.protocol) is not DurableActionSwitchProtocolV1:
            raise DurableActionSwitchInvariantViolation(
                "C2 payload rejects substituted protocol"
            )
        _cid(self.c1_commit_id, "C2 parent commit")
        for value in (
            self.overlay_projection_id,
            self.p2_continuation_id,
            self.final_model_id,
            self.final_execution_id,
            self.delta_id,
            self.preexecution_invalidation_id,
            self.invalidation_id,
        ):
            _cid(value, "C2 semantic identity")
        _cid(
            self.committed_final_runtime_snapshot_id,
            "C2 final runtime snapshot",
        )
        for value in self.full_cache_node_ids:
            _cid(value, "C2 cache node")
        if (
            type(self.lower_node_documents) is not tuple
            or len(self.lower_node_documents) != 28
        ):
            raise DurableActionSwitchInvariantViolation(
                "C2 lower node documents changed"
            )
        document_ids = tuple(
            _cid(
                _exact_mapping(
                    document,
                    set(document),
                    "C2 lower node document",
                )["node_id"],
                "C2 lower node document",
            )
            for document in self.lower_node_documents
        )
        if (
            document_ids != self.full_cache_node_ids
            or len(set(document_ids)) != 28
            or not {
                item[2] for item in self.active_final_bindings
            }.issubset(set(document_ids))
            or self.full_cache_entry_count != 28
            or self.active_final_entry_count != 18
            or self.cached_root_entry_count != 0
        ):
            raise DurableActionSwitchInvariantViolation(
                "C2 payload cache/continuation binding changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_c2_payload.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol": self.protocol.to_document(),
            "c1_commit_id": self.c1_commit_id,
            "overlay_projection_id": self.overlay_projection_id,
            "p2_continuation_id": self.p2_continuation_id,
            "final_model_id": self.final_model_id,
            "final_execution_id": self.final_execution_id,
            "delta_id": self.delta_id,
            "preexecution_invalidation_id": (
                self.preexecution_invalidation_id
            ),
            "invalidation_id": self.invalidation_id,
            "lower_node_documents": [
                dict(item) for item in self.lower_node_documents
            ],
            "full_cache_node_ids": list(self.full_cache_node_ids),
            "active_final_bindings": [
                {
                    "address": address,
                    "node_key_id": key_id,
                    "node_id": node_id,
                }
                for address, key_id, node_id in self.active_final_bindings
            ],
            "committed_final_runtime_snapshot_id": (
                self.committed_final_runtime_snapshot_id
            ),
            "full_cache_entry_count": self.full_cache_entry_count,
            "active_final_entry_count": self.active_final_entry_count,
            "cached_root_entry_count": self.cached_root_entry_count,
        }

    @property
    def payload_id(self) -> str:
        return _content_id("c2_payload", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "payload_id": self.payload_id}


def _parse_c2_payload(document: Any) -> DurableActionSwitchC2PayloadV1:
    row = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "protocol",
            "c1_commit_id",
            "overlay_projection_id",
            "p2_continuation_id",
            "final_model_id",
            "final_execution_id",
            "delta_id",
            "preexecution_invalidation_id",
            "invalidation_id",
            "lower_node_documents",
            "full_cache_node_ids",
            "active_final_bindings",
            "committed_final_runtime_snapshot_id",
            "full_cache_entry_count",
            "active_final_entry_count",
            "cached_root_entry_count",
            "payload_id",
        },
        "C2 payload",
    )
    if (
        row["schema"]
        != "acfqp.h2_durable_action_switch_c2_payload.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["lower_node_documents"]) is not list
        or type(row["full_cache_node_ids"]) is not list
    ):
        raise DurableActionSwitchInvariantViolation("C2 payload schema changed")
    result = DurableActionSwitchC2PayloadV1(
        _parse_protocol(row["protocol"]),
        row["c1_commit_id"],
        row["overlay_projection_id"],
        row["p2_continuation_id"],
        row["final_model_id"],
        row["final_execution_id"],
        row["delta_id"],
        row["preexecution_invalidation_id"],
        row["invalidation_id"],
        tuple(row["lower_node_documents"]),
        tuple(row["full_cache_node_ids"]),
        _parse_active_bindings(
            row["active_final_bindings"], "C2 active bindings"
        ),
        row["committed_final_runtime_snapshot_id"],
        row["full_cache_entry_count"],
        row["active_final_entry_count"],
        row["cached_root_entry_count"],
    )
    if not _same_document(result.to_document(), row):
        raise DurableActionSwitchInvariantViolation("C2 payload is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class DurableActionSwitchC2ManifestV1:
    protocol: DurableActionSwitchProtocolV1
    payload_id: str
    payload_sha256: str
    payload_size_bytes: int
    previous_c1_commit_id: str
    overlay_projection_id: str
    p2_continuation_id: str
    final_execution_id: str
    full_cache_entry_count: int = 28
    active_final_entry_count: int = 18

    def __post_init__(self) -> None:
        if type(self.protocol) is not DurableActionSwitchProtocolV1:
            raise DurableActionSwitchInvariantViolation(
                "C2 manifest rejects substituted protocol"
            )
        for value in (
            self.payload_id,
            self.payload_sha256,
            self.previous_c1_commit_id,
            self.overlay_projection_id,
            self.p2_continuation_id,
            self.final_execution_id,
        ):
            _cid(value, "C2 manifest identity")
        _integer(self.payload_size_bytes, "C2 payload size", 1)
        if (
            self.full_cache_entry_count != 28
            or self.active_final_entry_count != 18
        ):
            raise DurableActionSwitchInvariantViolation(
                "C2 manifest cardinality changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_c2_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol": self.protocol.to_document(),
            "payload_id": self.payload_id,
            "payload_sha256": self.payload_sha256,
            "payload_size_bytes": self.payload_size_bytes,
            "previous_c1_commit_id": self.previous_c1_commit_id,
            "overlay_projection_id": self.overlay_projection_id,
            "p2_continuation_id": self.p2_continuation_id,
            "final_execution_id": self.final_execution_id,
            "full_cache_entry_count": self.full_cache_entry_count,
            "active_final_entry_count": self.active_final_entry_count,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("c2_manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


def _parse_c2_manifest(document: Any) -> DurableActionSwitchC2ManifestV1:
    row = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "protocol",
            "payload_id",
            "payload_sha256",
            "payload_size_bytes",
            "previous_c1_commit_id",
            "overlay_projection_id",
            "p2_continuation_id",
            "final_execution_id",
            "full_cache_entry_count",
            "active_final_entry_count",
            "manifest_id",
        },
        "C2 manifest",
    )
    if (
        row["schema"]
        != "acfqp.h2_durable_action_switch_c2_manifest.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
    ):
        raise DurableActionSwitchInvariantViolation("C2 manifest schema changed")
    result = DurableActionSwitchC2ManifestV1(
        _parse_protocol(row["protocol"]),
        row["payload_id"],
        row["payload_sha256"],
        row["payload_size_bytes"],
        row["previous_c1_commit_id"],
        row["overlay_projection_id"],
        row["p2_continuation_id"],
        row["final_execution_id"],
        row["full_cache_entry_count"],
        row["active_final_entry_count"],
    )
    if not _same_document(result.to_document(), row):
        raise DurableActionSwitchInvariantViolation(
            "C2 manifest is not canonical"
        )
    return result


@dataclass(frozen=True, slots=True)
class VerifiedDurableActionSwitchC2LeaseV1:
    expected_commit_id: str
    commit: DurableActionSwitchCommitV1
    manifest: DurableActionSwitchC2ManifestV1
    payload: DurableActionSwitchC2PayloadV1
    projection: DurableActionSwitchOverlayProjectionV1
    continuation: DurableActionSwitchP2ContinuationV1
    stored_lower_nodes: tuple[dag.ActionIndexedProofNodeV1, ...]
    ground_transition_calls: int = 0

    def __post_init__(self) -> None:
        _cid(self.expected_commit_id, "verified C2 lease commit")
        if (
            type(self.commit) is not DurableActionSwitchCommitV1
            or type(self.manifest) is not DurableActionSwitchC2ManifestV1
            or type(self.payload) is not DurableActionSwitchC2PayloadV1
            or type(self.projection)
            is not DurableActionSwitchOverlayProjectionV1
            or type(self.continuation)
            is not DurableActionSwitchP2ContinuationV1
            or type(self.stored_lower_nodes) is not tuple
            or any(
                type(item) is not dag.ActionIndexedProofNodeV1
                for item in self.stored_lower_nodes
            )
            or len(self.stored_lower_nodes) != 28
            or self.expected_commit_id != self.commit.commit_id
            or self.commit.checkpoint_kind is not CheckpointKind.C2_FINAL
            or self.commit.payload_id != self.payload.payload_id
            or self.commit.manifest_id != self.manifest.manifest_id
            or self.commit.previous_commit_id
            != self.manifest.previous_c1_commit_id
            or self.projection.projection_id
            != self.manifest.overlay_projection_id
            or self.continuation.continuation_id
            != self.manifest.p2_continuation_id
            or tuple(
                item.to_document() for item in self.stored_lower_nodes
            )
            != tuple(self.payload.lower_node_documents)
            or tuple(item.node_id for item in self.stored_lower_nodes)
            != self.payload.full_cache_node_ids
            or self.ground_transition_calls != 0
        ):
            raise DurableActionSwitchInvariantViolation(
                "verified C2 lease binding changed"
            )


def write_durable_action_switch_c2_v1(
    c1_lease: VerifiedDurableActionSwitchC1LeaseV1,
    projection: DurableActionSwitchOverlayProjectionV1,
    continuation: DurableActionSwitchP2ContinuationV1,
    store_root: Path,
) -> DurableActionSwitchCommitV1:
    """Commit the complete 28-cache/18-active final durable state."""

    if (
        type(c1_lease) is not VerifiedDurableActionSwitchC1LeaseV1
        or type(projection) is not DurableActionSwitchOverlayProjectionV1
        or type(continuation) is not DurableActionSwitchP2ContinuationV1
    ):
        raise DurableActionSwitchInvariantViolation(
            "C2 writer requires exact typed inputs"
        )
    expected = _derive_p2(c1_lease, projection)
    if continuation.to_document() != expected.to_document():
        raise DurableActionSwitchInvariantViolation(
            "C2 continuation differs from exact model-only replay"
        )
    (
        _runtime,
        first,
        _restore,
        final_model,
        delta,
        pre,
        final,
        invalidation,
    ) = _derive_switch_state(c1_lease, projection)
    full_nodes = _ordered_unique_nodes(first, final)
    payload = DurableActionSwitchC2PayloadV1(
        c1_lease.payload.protocol,
        c1_lease.commit.commit_id,
        projection.projection_id,
        continuation.continuation_id,
        final_model.model_id,
        final.execution_id,
        delta.delta_id,
        pre.plan_id,
        invalidation.manifest_id,
        tuple(item.to_document() for item in full_nodes),
        tuple(item.node_id for item in full_nodes),
        continuation.active_final_bindings,
        continuation.committed_final_runtime_snapshot_id,
    )
    payload_bytes = canonical_json_bytes(payload.to_document())
    manifest = DurableActionSwitchC2ManifestV1(
        payload.protocol,
        payload.payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        c1_lease.commit.commit_id,
        projection.projection_id,
        continuation.continuation_id,
        final.execution_id,
    )
    manifest_bytes = canonical_json_bytes(manifest.to_document())
    commit = DurableActionSwitchCommitV1(
        CheckpointKind.C2_FINAL,
        payload.protocol.protocol_id,
        payload.payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        manifest.manifest_id,
        hashlib.sha256(manifest_bytes).hexdigest(),
        len(manifest_bytes),
        2,
        c1_lease.commit.commit_id,
    )
    _write_single_checkpoint(
        store_root,
        payload.payload_id,
        payload.to_document(),
        manifest.manifest_id,
        manifest.to_document(),
        commit,
    )
    loaded = load_verified_durable_action_switch_c2_v1(
        store_root,
        commit.commit_id,
        c1_lease,
        projection,
    )
    if loaded.commit.to_document() != commit.to_document():
        raise DurableActionSwitchInvariantViolation("C2 reread changed")
    return commit


def load_verified_durable_action_switch_c2_v1(
    store_root: Path,
    expected_commit_id: str,
    c1_lease: VerifiedDurableActionSwitchC1LeaseV1,
    projection: DurableActionSwitchOverlayProjectionV1,
) -> VerifiedDurableActionSwitchC2LeaseV1:
    _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT()
    if (
        type(c1_lease) is not VerifiedDurableActionSwitchC1LeaseV1
        or type(projection) is not DurableActionSwitchOverlayProjectionV1
    ):
        raise DurableActionSwitchInvariantViolation(
            "C2 loader requires exact parent inputs"
        )
    commit, payload_bytes, manifest_bytes = _read_single_checkpoint(
        store_root, expected_commit_id
    )
    if commit.checkpoint_kind is not CheckpointKind.C2_FINAL:
        raise DurableActionSwitchInvariantViolation(
            "C2 loader rejects a non-C2 commit"
        )
    payload = _parse_c2_payload(loads_canonical_json(payload_bytes))
    manifest = _parse_c2_manifest(loads_canonical_json(manifest_bytes))
    expected = _derive_p2(c1_lease, projection)
    (
        _runtime,
        first,
        _restore,
        final_model,
        delta,
        pre,
        final,
        invalidation,
    ) = _derive_switch_state(c1_lease, projection)
    full_nodes = _ordered_unique_nodes(first, final)
    if (
        commit.previous_commit_id != c1_lease.commit.commit_id
        or payload.overlay_projection_id != projection.projection_id
        or payload.p2_continuation_id != expected.continuation_id
        or payload.final_model_id != final_model.model_id
        or payload.final_execution_id != final.execution_id
        or payload.delta_id != delta.delta_id
        or payload.preexecution_invalidation_id != pre.plan_id
        or payload.invalidation_id != invalidation.manifest_id
        or tuple(
            canonical_json_bytes(item)
            for item in payload.lower_node_documents
        )
        != tuple(
            canonical_json_bytes(item.to_document())
            for item in full_nodes
        )
        or payload.full_cache_node_ids
        != tuple(item.node_id for item in full_nodes)
        or payload.active_final_bindings
        != expected.active_final_bindings
        or payload.committed_final_runtime_snapshot_id
        != expected.committed_final_runtime_snapshot_id
        or payload.payload_id != commit.payload_id
        or manifest.manifest_id != commit.manifest_id
        or manifest.payload_id != payload.payload_id
        or manifest.protocol.protocol_id != commit.protocol_id
        or payload.protocol.protocol_id != commit.protocol_id
        or manifest.payload_sha256 != commit.payload_sha256
        or manifest.payload_size_bytes != commit.payload_size_bytes
        or manifest.previous_c1_commit_id != c1_lease.commit.commit_id
        or manifest.overlay_projection_id != projection.projection_id
        or manifest.p2_continuation_id != expected.continuation_id
    ):
        raise DurableActionSwitchInvariantViolation(
            "C2 content-addressed identity chain changed"
        )
    stored_nodes = tuple(
        _CANONICAL_DAG_PARSE_NODE(item)
        for item in payload.lower_node_documents
    )
    if tuple(item.to_document() for item in stored_nodes) != tuple(
        item.to_document() for item in full_nodes
    ):
        raise DurableActionSwitchInvariantViolation(
            "C2 durable lower objects differ from semantic validation"
        )
    return VerifiedDurableActionSwitchC2LeaseV1(
        commit.commit_id,
        commit,
        manifest,
        payload,
        projection,
        expected,
        stored_nodes,
    )


@dataclass(frozen=True, slots=True)
class DurableActionSwitchC2AttestationV1:
    warm_replay: DurableActionSwitchWarmReplayV1
    c2_commit_id: str
    c1_commit_id: str
    overlay_projection_id: str
    continuation_id: str
    full_cache_entry_count: int
    active_final_entry_count: int
    selected_action: str
    selected_schedule_code: str
    final_certified: bool
    matching_buffer_imported: bool = False
    ground_transition_calls: int = 0

    def __post_init__(self) -> None:
        if type(self.warm_replay) is not DurableActionSwitchWarmReplayV1:
            raise DurableActionSwitchInvariantViolation(
                "C2 attestation requires an exact warm replay wrapper"
            )
        for value in (
            self.c2_commit_id,
            self.c1_commit_id,
            self.overlay_projection_id,
            self.continuation_id,
        ):
            _cid(value, "C2 attestation identity")
        if (
            self.full_cache_entry_count != 28
            or self.active_final_entry_count != 18
            or self.selected_action != "M"
            or self.selected_schedule_code != "A0A1"
            or self.final_certified is not True
            or self.warm_replay.checkpoint_kind
            is not CheckpointKind.C2_FINAL
            or self.warm_replay.commit_id != self.c2_commit_id
            or self.warm_replay.selected_action != self.selected_action
            or self.warm_replay.certified is not self.final_certified
            or self.matching_buffer_imported is not False
            or self.ground_transition_calls != 0
        ):
            raise DurableActionSwitchInvariantViolation(
                "C2 attestation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_action_switch_c2_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "warm_replay": self.warm_replay.to_document(),
            "c2_commit_id": self.c2_commit_id,
            "c1_commit_id": self.c1_commit_id,
            "overlay_projection_id": self.overlay_projection_id,
            "continuation_id": self.continuation_id,
            "full_cache_entry_count": self.full_cache_entry_count,
            "active_final_entry_count": self.active_final_entry_count,
            "selected_action": self.selected_action,
            "selected_schedule_code": self.selected_schedule_code,
            "final_certified": self.final_certified,
            "matching_buffer_imported": self.matching_buffer_imported,
            "ground_transition_calls": self.ground_transition_calls,
        }

    @property
    def attestation_id(self) -> str:
        return _content_id("c2_attestation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def _derive_c2_attestation(
    lease: VerifiedDurableActionSwitchC2LeaseV1,
) -> DurableActionSwitchC2AttestationV1:
    if type(lease) is not VerifiedDurableActionSwitchC2LeaseV1:
        raise DurableActionSwitchInvariantViolation(
            "C2 attestation requires an exact verified lease"
        )
    final_model = _CANONICAL_DAG_REGISTERED_FINAL()
    query = _CANONICAL_DAG_REGISTERED_QUERY()
    final_execution_id = _cid(
        _exact_mapping(
            lease.continuation.final_execution_document,
            set(lease.continuation.final_execution_document),
            "C2 final execution",
        )["execution_id"],
        "C2 final execution",
    )
    runtime, restore = (
        _CANONICAL_DAG_RESTORE_FINAL(
            final_model,
            query,
            lease.stored_lower_nodes,
            lease.continuation.active_final_bindings,
            final_execution_id,
        )
    )
    roots = _CANONICAL_DAG_REBUILD_ROOTS(
        final_model,
        query,
        runtime,
        restore,
    )
    active_ids = roots.ordered_lower_node_ids
    if active_ids != tuple(
        item[2] for item in lease.continuation.active_final_bindings
    ):
        raise DurableActionSwitchInvariantViolation(
            "C2 active bindings differ from final semantic replay"
        )
    warm = DurableActionSwitchWarmReplayV1(
        CheckpointKind.C2_FINAL,
        lease.commit.commit_id,
        lease.payload.payload_id,
        final_model.model_id,
        query.query_id,
        final_execution_id,
        restore.restore_id,
        roots.replay_id,
        active_ids,
        roots.proposal.selected_action.value,
        roots.proposal.selected_schedule_code,
        roots.selected_root.certified,
    )
    return DurableActionSwitchC2AttestationV1(
        warm,
        lease.commit.commit_id,
        lease.manifest.previous_c1_commit_id,
        lease.projection.projection_id,
        lease.continuation.continuation_id,
        lease.payload.full_cache_entry_count,
        lease.payload.active_final_entry_count,
        lease.continuation.final_action,
        lease.continuation.final_schedule_code,
        lease.continuation.final_certified,
    )


def _worker_environment() -> dict[str, str]:
    environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
    }
    for name in ("LANG", "LC_ALL", "TZ"):
        value = os.environ.get(name)
        if value is not None:
            environment[name] = value
    return environment


def _worker_command(
    *,
    kind: WorkerKind,
    c1_store_root: Path,
    c1_commit_id: str,
    output: Path,
    parent_process_id: int,
    overlay_store_root: Path | None = None,
    overlay_projection_id: str | None = None,
    c2_store_root: Path | None = None,
    c2_commit_id: str | None = None,
) -> tuple[str, ...]:
    source_root = Path(__file__).resolve().parents[1]
    bootstrap = (
        "import runpy,sys;"
        f"sys.path.insert(0,{str(source_root)!r});"
        "runpy.run_module("
        "'acfqp.h2_durable_action_switch_transport_v1',"
        "run_name='__main__')"
    )
    command = [
        sys.executable,
        "-I",
        "-s",
        "-B",
        "-c",
        bootstrap,
        "--worker-kind",
        kind.value,
        "--c1-store-root",
        str(c1_store_root.resolve()),
        "--c1-commit-id",
        c1_commit_id,
        "--output",
        str(output),
        "--parent-process-id",
        str(parent_process_id),
    ]
    if overlay_store_root is not None:
        command.extend(
            [
                "--overlay-store-root",
                str(overlay_store_root.resolve()),
                "--overlay-projection-id",
                str(overlay_projection_id),
            ]
        )
    if c2_store_root is not None:
        command.extend(
            [
                "--c2-store-root",
                str(c2_store_root.resolve()),
                "--c2-commit-id",
                str(c2_commit_id),
            ]
        )
    return tuple(command)


def _launch_worker(
    *,
    kind: WorkerKind,
    c1_store_root: Path,
    c1_commit_id: str,
    overlay_store_root: Path | None = None,
    overlay_projection_id: str | None = None,
    c2_store_root: Path | None = None,
    c2_commit_id: str | None = None,
) -> Mapping[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix=f"acfqp-durable-action-switch-{kind.value.lower()}-"
    ) as directory:
        output = Path(directory) / "worker-output.json"
        command = _worker_command(
            kind=kind,
            c1_store_root=c1_store_root,
            c1_commit_id=c1_commit_id,
            overlay_store_root=overlay_store_root,
            overlay_projection_id=overlay_projection_id,
            c2_store_root=c2_store_root,
            c2_commit_id=c2_commit_id,
            output=output,
            parent_process_id=os.getpid(),
        )
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[2],
            env=_worker_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = process.communicate(timeout=1200)
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.communicate()
            raise DurableActionSwitchInvariantViolation(
                f"fresh {kind.value} worker timed out"
            ) from error
        if process.returncode != 0:
            diagnostic = stderr.decode("utf-8", errors="replace")[-2000:]
            raise DurableActionSwitchInvariantViolation(
                f"fresh {kind.value} worker failed with code "
                f"{process.returncode}: {diagnostic}"
            )
        if stdout:
            raise DurableActionSwitchInvariantViolation(
                f"fresh {kind.value} worker emitted unexpected stdout"
            )
        envelope = _exact_mapping(
            loads_canonical_json(_read_stable_regular(output)),
            {
                "schema",
                "schema_version",
                "profile_key",
                "worker_kind",
                "child_process_id",
                "parent_process_id",
                "artifact",
            },
            f"{kind.value} worker envelope",
        )
        if (
            envelope["schema"]
            != "acfqp.h2_durable_action_switch_worker_envelope.v1"
            or envelope["schema_version"] != SCHEMA_VERSION
            or envelope["profile_key"] != PROFILE_KEY
            or envelope["worker_kind"] != kind.value
            or envelope["child_process_id"] != process.pid
            or envelope["parent_process_id"] != os.getpid()
            or process.pid == os.getpid()
        ):
            raise DurableActionSwitchInvariantViolation(
                f"fresh {kind.value} OS process attestation changed"
            )
        return envelope["artifact"]


def run_durable_action_switch_p1_fresh_worker_v1(
    c1_store_root: Path,
    c1_commit_id: str,
) -> DurableActionSwitchP1AttestationV1:
    artifact = _launch_worker(
        kind=WorkerKind.P1,
        c1_store_root=c1_store_root,
        c1_commit_id=c1_commit_id,
    )
    lease = load_verified_durable_action_switch_c1_v1(
        c1_store_root, c1_commit_id
    )
    expected = _derive_p1(lease)
    if not _same_document(artifact, expected.to_document()):
        raise DurableActionSwitchInvariantViolation(
            "fresh P1 output differs from trusted C1 replay"
        )
    return expected


def run_durable_action_switch_p2_fresh_worker_v1(
    c1_store_root: Path,
    c1_commit_id: str,
    overlay_store_root: Path,
    overlay_projection_id: str,
) -> DurableActionSwitchP2ContinuationV1:
    artifact = _launch_worker(
        kind=WorkerKind.P2,
        c1_store_root=c1_store_root,
        c1_commit_id=c1_commit_id,
        overlay_store_root=overlay_store_root,
        overlay_projection_id=overlay_projection_id,
    )
    lease = load_verified_durable_action_switch_c1_v1(
        c1_store_root, c1_commit_id
    )
    projection = load_durable_action_switch_overlay_projection_v1(
        overlay_store_root, overlay_projection_id
    )
    expected = _derive_p2(lease, projection)
    if not _same_document(artifact, expected.to_document()):
        raise DurableActionSwitchInvariantViolation(
            "fresh P2 output differs from trusted model-only replay"
        )
    return expected


def run_durable_action_switch_c2_fresh_worker_v1(
    c1_store_root: Path,
    c1_commit_id: str,
    overlay_store_root: Path,
    overlay_projection_id: str,
    c2_store_root: Path,
    c2_commit_id: str,
) -> DurableActionSwitchC2AttestationV1:
    artifact = _launch_worker(
        kind=WorkerKind.C2,
        c1_store_root=c1_store_root,
        c1_commit_id=c1_commit_id,
        overlay_store_root=overlay_store_root,
        overlay_projection_id=overlay_projection_id,
        c2_store_root=c2_store_root,
        c2_commit_id=c2_commit_id,
    )
    c1 = load_verified_durable_action_switch_c1_v1(
        c1_store_root, c1_commit_id
    )
    projection = load_durable_action_switch_overlay_projection_v1(
        overlay_store_root, overlay_projection_id
    )
    c2 = load_verified_durable_action_switch_c2_v1(
        c2_store_root, c2_commit_id, c1, projection
    )
    expected = _derive_c2_attestation(c2)
    if not _same_document(artifact, expected.to_document()):
        raise DurableActionSwitchInvariantViolation(
            "fresh C2 output differs from trusted checkpoint replay"
        )
    return expected


def _worker_cli(arguments: argparse.Namespace) -> int:
    try:
        kind = WorkerKind(arguments.worker_kind)
        if os.getpid() == arguments.parent_process_id:
            raise DurableActionSwitchInvariantViolation(
                "worker did not cross a process boundary"
            )
        _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT(fresh_worker=True)
        c1_store = Path(arguments.c1_store_root)
        c1 = load_verified_durable_action_switch_c1_v1(
            c1_store, arguments.c1_commit_id
        )
        if kind is WorkerKind.P1:
            artifact: Any = _derive_p1(c1)
        else:
            if (
                type(arguments.overlay_store_root) is not str
                or type(arguments.overlay_projection_id) is not str
            ):
                raise DurableActionSwitchInvariantViolation(
                    f"{kind.value} requires overlay inputs"
                )
            projection = load_durable_action_switch_overlay_projection_v1(
                Path(arguments.overlay_store_root),
                arguments.overlay_projection_id,
            )
            if kind is WorkerKind.P2:
                artifact = _derive_p2(c1, projection)
            else:
                if (
                    type(arguments.c2_store_root) is not str
                    or type(arguments.c2_commit_id) is not str
                ):
                    raise DurableActionSwitchInvariantViolation(
                        "C2 worker requires C2 checkpoint inputs"
                    )
                c2 = load_verified_durable_action_switch_c2_v1(
                    Path(arguments.c2_store_root),
                    arguments.c2_commit_id,
                    c1,
                    projection,
                )
                artifact = _derive_c2_attestation(c2)
        _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT(fresh_worker=True)
        output = Path(arguments.output)
        if output.exists() or not output.parent.is_dir():
            raise DurableActionSwitchInvariantViolation(
                "worker output target is not fresh"
            )
        envelope = {
            "schema": "acfqp.h2_durable_action_switch_worker_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "worker_kind": kind.value,
            "child_process_id": os.getpid(),
            "parent_process_id": arguments.parent_process_id,
            "artifact": artifact.to_document(),
        }
        _atomic_write(output, canonical_json_bytes(envelope))
        return 0
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


def _main(argv: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="acfqp-h2-durable-action-switch-transport-v1"
    )
    parser.add_argument("--worker-kind", choices=tuple(item.value for item in WorkerKind))
    parser.add_argument("--c1-store-root")
    parser.add_argument("--c1-commit-id")
    parser.add_argument("--overlay-store-root")
    parser.add_argument("--overlay-projection-id")
    parser.add_argument("--c2-store-root")
    parser.add_argument("--c2-commit-id")
    parser.add_argument("--output")
    parser.add_argument("--parent-process-id", type=int)
    arguments = parser.parse_args(argv)
    if (
        type(arguments.worker_kind) is not str
        or type(arguments.c1_store_root) is not str
        or type(arguments.c1_commit_id) is not str
        or type(arguments.output) is not str
        or type(arguments.parent_process_id) is not int
        or arguments.parent_process_id <= 0
    ):
        parser.error("the module is an internal fresh-process worker")
    return _worker_cli(arguments)


_TRANSPORT_INTERNAL_AUTHORITIES = (
    (
        "_assert_model_only_import_boundary",
        _assert_model_only_import_boundary,
    ),
    (
        "_CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT",
        _CANONICAL_MODEL_ONLY_BOUNDARY_ASSERT,
    ),
    ("_read_stable_regular", _read_stable_regular),
    ("_atomic_write", _atomic_write),
    ("_write_single_checkpoint", _write_single_checkpoint),
    ("_read_single_checkpoint", _read_single_checkpoint),
    ("_parse_commit", _parse_commit),
    ("_parse_c1_payload", _parse_c1_payload),
    ("_parse_c1_manifest", _parse_c1_manifest),
    ("_parse_overlay", _parse_overlay),
    ("_parse_p2", _parse_p2),
    ("_parse_c2_payload", _parse_c2_payload),
    ("_parse_c2_manifest", _parse_c2_manifest),
    ("_derive_first_state", _derive_first_state),
    ("_materialize_c1_payload", _materialize_c1_payload),
    ("_derive_p1", _derive_p1),
    ("_derive_switch_state", _derive_switch_state),
    ("_derive_p2", _derive_p2),
    ("_derive_c2_attestation", _derive_c2_attestation),
    ("_worker_environment", _worker_environment),
    ("_worker_command", _worker_command),
    ("_launch_worker", _launch_worker),
    ("_worker_cli", _worker_cli),
)


__all__ = [
    "CONTRACT_VERSION",
    "CheckpointKind",
    "DurableActionSwitchC1ManifestV1",
    "DurableActionSwitchC1PayloadV1",
    "DurableActionSwitchC2AttestationV1",
    "DurableActionSwitchC2ManifestV1",
    "DurableActionSwitchC2PayloadV1",
    "DurableActionSwitchCommitV1",
    "DurableActionSwitchInvariantViolation",
    "DurableActionSwitchOverlayProjectionV1",
    "DurableActionSwitchP1AttestationV1",
    "DurableActionSwitchP2ContinuationV1",
    "DurableActionSwitchProtocolV1",
    "DurableActionSwitchWarmReplayV1",
    "EXPECTED_ACTION_INDEXED_SOURCE_SHA256",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "VerifiedDurableActionSwitchC1LeaseV1",
    "VerifiedDurableActionSwitchC2LeaseV1",
    "WorkerKind",
    "freeze_durable_action_switch_overlay_projection_v1",
    "load_durable_action_switch_overlay_projection_v1",
    "load_verified_durable_action_switch_c1_v1",
    "load_verified_durable_action_switch_c2_v1",
    "registered_durable_action_switch_protocol_v1",
    "run_durable_action_switch_c2_fresh_worker_v1",
    "run_durable_action_switch_p1_fresh_worker_v1",
    "run_durable_action_switch_p2_fresh_worker_v1",
    "write_durable_action_switch_c1_v1",
    "write_durable_action_switch_c2_v1",
    "write_durable_action_switch_overlay_projection_v1",
]


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(_main())
