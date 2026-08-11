"""Bind one query-neutral V0-075 model to its actual BuildEpoch work.

This authority consumes the versioned model-export trace emitted by the same
sealed K7 construction occurrence.  It aggregates exactly the 100 mandatory
initial-acquisition, initial-build and closed-reconciliation paths from the
twelve native V6 stages and issues their formal ``CounterRecordV1`` values.

The remaining query-segment records, output-byte fixed point, plan
certificate, campaign closure and official Gates remain outside this slice.
In particular, no construction work is zeroed merely because the model may be
reused by later queries.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from functools import lru_cache
import hashlib
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import CounterRecordV1, ReducerEnum
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_owned_runtime_v2 as owned_v2
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_abstract_query_native_zero_authority_v1 as query_zero_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_k7_causal_promotion_accounted_executor_v1 as executor_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_REUSABLE_BUILD_EPOCH_ENVELOPE_V1_DOMAIN,
    CONSTRUCTION_K7_REUSABLE_BUILD_EPOCH_RESOLUTION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    V075_K7_REUSABLE_MODEL_OPERATIONAL_TRACE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.83"
PROFILE_KEY = "construction_k7_reusable_build_epoch_authority_v1"

EXPECTED_STAGE_COUNT = 12
EXPECTED_STAGE_LOCAL_RECORD_COUNT = 2_424
EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT = 100
EXPECTED_SOURCE_RECORD_COUNT = 1_200

RESOLUTION_DOMAIN = CONSTRUCTION_K7_REUSABLE_BUILD_EPOCH_RESOLUTION_V1_DOMAIN
ENVELOPE_DOMAIN = CONSTRUCTION_K7_REUSABLE_BUILD_EPOCH_ENVELOPE_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESOLUTION_DOMAIN, ENVELOPE_DOMAIN})
if len(LOCAL_DOMAINS) != 2 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("reusable BuildEpoch domains are not central")

_ENVELOPE_ISSUER = object()


class ConstructionK7ReusableBuildEpochAuthorityV1Error(ValueError):
    """The model trace, native records, or BuildEpoch identity changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReusableBuildEpochAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ReusableBuildEpochAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True, order=True)
class ReusableBuildEpochPathResolutionV1:
    source_operational_trace_id: str
    source_occurrence_id: str
    root_model_epoch_id: str
    path: str
    reducer: ReducerEnum
    value: int
    ordered_source_record_ids: tuple[str, ...]
    _resolution_id: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_operational_trace_id, "source trace"),
            (self.source_occurrence_id, "source occurrence"),
            (self.root_model_epoch_id, "root model epoch"),
        ):
            _cid(value, label)
        try:
            reducer = ReducerEnum(self.reducer)
        except (TypeError, ValueError) as error:
            raise ConstructionK7ReusableBuildEpochAuthorityV1Error(
                "BuildEpoch resolution reducer changed"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        ids = tuple(self.ordered_source_record_ids)
        object.__setattr__(self, "ordered_source_record_ids", ids)
        if (
            type(self.path) is not str
            or not self.path
            or type(self.value) is not int
            or self.value < 0
            or len(ids) != EXPECTED_STAGE_COUNT
            or len(set(ids)) != EXPECTED_STAGE_COUNT
        ):
            _fail("BuildEpoch path resolution shape changed")
        for value in ids:
            _cid(value, "source stage record")
        object.__setattr__(
            self,
            "_resolution_id",
            content_id(RESOLUTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_reusable_build_epoch_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_operational_trace_id": self.source_operational_trace_id,
            "source_occurrence_id": self.source_occurrence_id,
            "root_model_epoch_id": self.root_model_epoch_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "value": self.value,
            "ordered_source_record_ids": list(self.ordered_source_record_ids),
            "ordered_source_stage_indices": list(range(1, EXPECTED_STAGE_COUNT + 1)),
            "missing_record_inferred_zero": False,
            "construction_work_zeroed_for_reuse": False,
            "formal_counter_record_authorized": True,
        }

    @property
    def resolution_id(self) -> str:
        current = content_id(RESOLUTION_DOMAIN, self._payload())
        if current != self._resolution_id:
            _fail("BuildEpoch path resolution changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reusable_build_epoch_resolution_id": self.resolution_id,
        }


@dataclass(frozen=True, slots=True)
class ReusableBuildEpochEnvelopeV1:
    _issuer: InitVar[object]
    source_operational_trace_id: str
    source_occurrence_id: str
    source_accounted_occurrence_id: str
    source_owned_accounting_result_id: str
    root_model_epoch_id: str
    root_model_id: str
    root_model_bytes_sha256: str
    root_model_byte_count: int
    initial_model_build_completion_id: str
    resolutions: tuple[ReusableBuildEpochPathResolutionV1, ...]
    counter_records: tuple[CounterRecordV1, ...]
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ENVELOPE_ISSUER:
            _fail("reusable BuildEpoch envelope is caller-minted")
        for value, label in (
            (self.source_operational_trace_id, "source trace"),
            (self.source_occurrence_id, "source occurrence"),
            (self.source_accounted_occurrence_id, "source accounted occurrence"),
            (self.source_owned_accounting_result_id, "source accounting result"),
            (self.root_model_epoch_id, "root model epoch"),
            (self.root_model_id, "root model"),
            (self.initial_model_build_completion_id, "initial-build completion"),
        ):
            _cid(value, label)
        resolutions = tuple(self.resolutions)
        records = tuple(self.counter_records)
        object.__setattr__(self, "resolutions", resolutions)
        object.__setattr__(self, "counter_records", records)
        paths = query_zero_v1.required_build_epoch_paths_v1()
        if (
            type(self.root_model_bytes_sha256) is not str
            or len(self.root_model_bytes_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.root_model_bytes_sha256)
            or type(self.root_model_byte_count) is not int
            or self.root_model_byte_count <= 0
            or len(resolutions) != EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT
            or tuple(row.path for row in resolutions) != paths
            or len(records) != EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT
            or tuple(row.path for row in records) != paths
            or any(type(row) is not ReusableBuildEpochPathResolutionV1 for row in resolutions)
            or any(type(row) is not CounterRecordV1 for row in records)
        ):
            _fail("reusable BuildEpoch envelope inventory changed")
        registry = registry_v6.official_counter_registry_v6()
        for resolution, record in zip(resolutions, records):
            leaf = registry.by_path[resolution.path]
            record.verify_against(leaf)
            if (
                resolution.source_operational_trace_id
                != self.source_operational_trace_id
                or resolution.source_occurrence_id != self.source_occurrence_id
                or resolution.root_model_epoch_id != self.root_model_epoch_id
                or resolution.reducer is not leaf.reducer
                or record.counter_registry_id != registry.registry_id
                or record.value != resolution.value
                or record.recorder_id != resolution.resolution_id
            ):
                _fail("reusable BuildEpoch record crossed its native resolution")
        object.__setattr__(
            self,
            "_envelope_id",
            content_id(ENVELOPE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_reusable_build_epoch_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_operational_trace_id": self.source_operational_trace_id,
            "source_occurrence_id": self.source_occurrence_id,
            "source_accounted_occurrence_id": self.source_accounted_occurrence_id,
            "source_owned_accounting_result_id": self.source_owned_accounting_result_id,
            "root_model_epoch_id": self.root_model_epoch_id,
            "root_model_id": self.root_model_id,
            "root_model_bytes_sha256": self.root_model_bytes_sha256,
            "root_model_byte_count": self.root_model_byte_count,
            "initial_model_build_completion_id": self.initial_model_build_completion_id,
            "resolution_ids": [row.resolution_id for row in self.resolutions],
            "counter_record_ids": [row.record_id for row in self.counter_records],
            "required_build_epoch_path_count": len(self.counter_records),
            "source_stage_count": EXPECTED_STAGE_COUNT,
            "source_stage_local_counter_record_count": EXPECTED_STAGE_LOCAL_RECORD_COUNT,
            "selected_source_record_count": EXPECTED_SOURCE_RECORD_COUNT,
            "model_occurrence_or_arm_fields_present": False,
            "model_threshold_fields_present": False,
            "model_private_law_access": False,
            "same_run_model_and_native_work_bound": True,
            "construction_work_zeroed_for_reuse": False,
            "query_segment_work_included": False,
            "io_output_bytes_fixed_point_solved": False,
            "warm_query_executed": False,
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def envelope_id(self) -> str:
        current = content_id(ENVELOPE_DOMAIN, self._payload())
        if current != self._envelope_id:
            _fail("reusable BuildEpoch envelope changed after issuance")
        return current

    @property
    def values(self) -> Mapping[str, int]:
        return MappingProxyType({row.path: row.value for row in self.counter_records})

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "resolutions": [row.to_document() for row in self.resolutions],
            "counter_records": [row.to_dict() for row in self.counter_records],
            "reusable_build_epoch_envelope_id": self.envelope_id,
        }


def _record_rows(
    stages: tuple[live_v3.RecordedStageWorkV3, ...],
    path: str,
) -> tuple[live_v3.CounterRecordV3, ...]:
    rows = []
    for stage in stages:
        matches = tuple(row for row in stage.work_vector.records if row.path == path)
        if len(matches) != 1:
            _fail(f"source stage does not contain exactly one {path!r} record")
        rows.append(matches[0])
    return tuple(rows)


def _build_expected_envelope(
    *,
    trace_document: Mapping[str, Any],
    stages: tuple[live_v3.RecordedStageWorkV3, ...],
) -> ReusableBuildEpochEnvelopeV1:
    registry = registry_v6.official_counter_registry_v6()
    model_raw = canonical_json_bytes(trace_document["root_numerical_model"])
    try:
        model = planning_v2.replay_v075_numerical_model_bytes_v2(model_raw)
    except Exception as error:
        raise ConstructionK7ReusableBuildEpochAuthorityV1Error(
            "root model export failed exact typed replay"
        ) from error
    science = trace_document["science_summary"]
    initial_build = stages[2].stage_completion
    if (
        initial_build.stage_kind.value != "INITIAL_MODEL_BUILD"
        or model.model_id != trace_document["root_model_id"]
        or trace_document["root_model_epoch_id"] != science["root_model_epoch_id"]
        or model.model_id not in initial_build.output_artifact_ids
        or science["root_model_epoch_id"] not in initial_build.output_artifact_ids
    ):
        _fail("root model export differs from initial-build completion")
    resolutions = []
    records = []
    for path in query_zero_v1.required_build_epoch_paths_v1():
        source_rows = _record_rows(stages, path)
        leaf = registry.by_path[path]
        for row in source_rows:
            row.verify_against(leaf)
            if (
                row.counter_registry_id != registry.registry_id
                or row.subject_id != science["occurrence_id"]
            ):
                _fail("BuildEpoch source record identity crossed")
        if leaf.reducer is ReducerEnum.SUM:
            value = sum(row.value for row in source_rows)
        else:
            value = max(row.value for row in source_rows)
        resolution = ReusableBuildEpochPathResolutionV1(
            trace_document["operational_trace_id"],
            science["occurrence_id"],
            science["root_model_epoch_id"],
            path,
            leaf.reducer,
            value,
            tuple(row.record_id for row in source_rows),
        )
        resolutions.append(resolution)
        records.append(
            CounterRecordV1.observe(
                registry,
                path,
                value,
                recorder_id=resolution.resolution_id,
            )
        )
    return ReusableBuildEpochEnvelopeV1(
        _ENVELOPE_ISSUER,
        trace_document["operational_trace_id"],
        science["occurrence_id"],
        science["accounted_occurrence_id"],
        science["owned_accounting_result_id"],
        science["root_model_epoch_id"],
        model.model_id,
        hashlib.sha256(model_raw).hexdigest(),
        len(model_raw),
        initial_build.completion_attestation_id,
        tuple(resolutions),
        tuple(records),
    )


@lru_cache(maxsize=4)
def _replay_model_export_trace_stages(
    trace_raw: bytes,
) -> tuple[live_v3.RecordedStageWorkV3, ...]:
    if type(trace_raw) is not bytes or not trace_raw:
        _fail("model-export trace must be nonempty bytes")
    try:
        document = loads_canonical_json(trace_raw)
    except Exception as error:
        raise ConstructionK7ReusableBuildEpochAuthorityV1Error(
            "model-export trace is not canonical JSON"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != trace_raw
        or set(document) != executor_v1.MODEL_EXPORT_TRACE_KEYS
        or document["schema"] != executor_v1.MODEL_EXPORT_TRACE_SCHEMA
        or document["schema_version"]
        != executor_v1.MODEL_EXPORT_TRACE_SCHEMA_VERSION
        or document["artifact_role"] != "OPERATIONAL_TRACE"
        or document["profile_key"]
        != "v075_k7_causal_promotion_accounted_runtime_v1"
        or document["construction_only"] is not True
        or document["fresh_heldout_accessed"] is not False
        or document["formal_counter_record_issued_by_worker"] is not False
        or document["occurrence_vector_issued_by_worker"] is not False
        or document["official_execution_allowed"] is not False
        or document["accounting_provenance_hashes_excluded"] is not True
        or document["global_hashlib_sha256_constructor_hook_present"] is not True
        or document["reusable_model_export_only"] is not True
        or document["model_occurrence_or_arm_fields_present"] is not False
        or document["model_threshold_fields_present"] is not False
        or document["model_private_law_access"] is not False
    ):
        _fail("model-export trace contract changed")
    payload = dict(document)
    supplied = payload.pop("operational_trace_id")
    if supplied != content_id(
        V075_K7_REUSABLE_MODEL_OPERATIONAL_TRACE_V1_DOMAIN, payload
    ):
        _fail("model-export trace content ID changed")
    science = document["science_summary"]
    if type(science) is not dict or set(science) != executor_v1.SCIENCE_SUMMARY_KEYS:
        _fail("model-export science summary changed")
    for key in (
        "supervised_request_id",
        "runtime_preparation_id",
        "runtime_tree_id",
    ):
        _cid(document[key], f"model-export {key}")
    for key in (
        "occurrence_id",
        "accounted_occurrence_id",
        "owned_accounting_result_id",
        "root_model_epoch_id",
    ):
        _cid(science[key], f"model-export science {key}")
    if (
        science["terminal_class"] != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or science["terminal_code"] != "ATTEMPT_BUDGET_EXHAUSTED"
        or science["observer_closed_and_exactly_reconciled"] is not True
        or science["stage_instance_count"] != EXPECTED_STAGE_COUNT
        or science["stage_local_counter_record_count"]
        != EXPECTED_STAGE_LOCAL_RECORD_COUNT
        or document["child_integrity_obligations"]
        != list(executor_v1.EXPECTED_CHILD_INTEGRITY_OBLIGATIONS)
        or document["child_protocol_obligations"]
        != list(executor_v1.EXPECTED_CHILD_PROTOCOL_OBLIGATIONS)
    ):
        _fail("model-export terminal or obligation summary changed")
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    rows = document["recorded_stages"]
    if type(rows) is not list or len(rows) != EXPECTED_STAGE_COUNT:
        _fail("model-export stage inventory changed")
    try:
        stages = tuple(
            live_v3.RecordedStageWorkV3.from_document(
                row, registry, stage_profile, comparison, actual
            )
            for row in rows
        )
        for row in stages:
            live_v3.verify_recorded_stage_work_v3(
                row, registry, stage_profile, comparison, actual
            )
    except Exception as error:
        raise ConstructionK7ReusableBuildEpochAuthorityV1Error(
            "model-export native stages failed replay"
        ) from error
    if (
        tuple(
            registry_v6.ConstructionStageKindV6(row.stage_start.stage_kind.value)
            for row in stages
        )
        != owned_v2.CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2
        or sum(len(row.work_vector.records) for row in stages)
        != EXPECTED_STAGE_LOCAL_RECORD_COUNT
    ):
        _fail("model-export stage plan changed")
    return stages


def _replay_model_export_trace(
    trace_raw: bytes,
) -> tuple[dict[str, Any], tuple[live_v3.RecordedStageWorkV3, ...]]:
    stages = _replay_model_export_trace_stages(trace_raw)
    document = loads_canonical_json(trace_raw)
    if type(document) is not dict:
        _fail("model-export trace replay did not produce one object")
    return document, stages


def issue_reusable_build_epoch_authority_v1(
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
) -> ReusableBuildEpochEnvelopeV1:
    execution = executor_v1.require_supervised_causal_promotion_execution_v1(
        execution
    )
    if execution.root_model_bytes is None:
        _fail("historical causal-promotion trace has no reusable model export")
    trace_document, stages = _replay_model_export_trace(execution.trace_raw)
    expected = _build_expected_envelope(
        trace_document=trace_document,
        stages=stages,
    )
    if expected.root_model_bytes_sha256 != hashlib.sha256(
        execution.root_model_bytes
    ).hexdigest():
        _fail("live model bytes differ from the portable model-export trace")
    return expected


def require_reusable_build_epoch_envelope_v1(
    envelope: ReusableBuildEpochEnvelopeV1,
) -> ReusableBuildEpochEnvelopeV1:
    if type(envelope) is not ReusableBuildEpochEnvelopeV1:
        _fail("reusable BuildEpoch envelope has a foreign type")
    envelope.__post_init__(_ENVELOPE_ISSUER)
    return envelope


def replay_reusable_build_epoch_source_v1(
    source_trace_bytes: bytes,
) -> ReusableBuildEpochEnvelopeV1:
    """Rebuild the typed 100-path envelope from one exact model-export trace."""

    trace_document, stages = _replay_model_export_trace(source_trace_bytes)
    return _build_expected_envelope(
        trace_document=trace_document,
        stages=stages,
    )


def verify_reusable_build_epoch_authority_bytes_v1(
    *,
    source_trace_bytes: bytes,
    envelope_bytes: bytes,
) -> ReusableBuildEpochEnvelopeV1:
    trace_document, stages = _replay_model_export_trace(source_trace_bytes)
    expected = _build_expected_envelope(
        trace_document=trace_document,
        stages=stages,
    )
    if type(envelope_bytes) is not bytes or not envelope_bytes:
        _fail("reusable BuildEpoch envelope must be nonempty bytes")
    try:
        claimed = loads_canonical_json(envelope_bytes)
    except Exception as error:
        raise ConstructionK7ReusableBuildEpochAuthorityV1Error(
            "reusable BuildEpoch envelope is not canonical JSON"
        ) from error
    if (
        type(claimed) is not dict
        or canonical_json_bytes(claimed) != envelope_bytes
        or canonical_json_bytes(expected.to_document()) != envelope_bytes
    ):
        _fail("reusable BuildEpoch envelope differs from exact source replay")
    return expected


__all__ = [
    "ConstructionK7ReusableBuildEpochAuthorityV1Error",
    "EXPECTED_REQUIRED_BUILD_EPOCH_PATH_COUNT",
    "LOCAL_DOMAINS",
    "ReusableBuildEpochEnvelopeV1",
    "ReusableBuildEpochPathResolutionV1",
    "issue_reusable_build_epoch_authority_v1",
    "require_reusable_build_epoch_envelope_v1",
    "replay_reusable_build_epoch_source_v1",
    "verify_reusable_build_epoch_authority_bytes_v1",
]
