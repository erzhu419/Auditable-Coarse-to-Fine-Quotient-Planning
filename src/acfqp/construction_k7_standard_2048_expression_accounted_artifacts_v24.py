"""Fixed-point CounterRecord/WorkVector artifacts for the V24 campaign."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_standard_2048_expression_accounted_preregistration_v24 as pre
from acfqp import construction_k7_standard_2048_expression_accounted_runtime_v24 as runtime
from acfqp.accounting_v1 import RouteKindEnum, WorkVectorV1
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
MAXIMUM_FIXED_POINT_ITERATIONS = 16


class ConstructionK7Standard2048ExpressionAccountedArtifactsV24Error(RuntimeError):
    """A native receipt, output fixed point, or durable write changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionAccountedArtifactsV24Error(message)


def _exact_document(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} is not one mapping")
    raw = canonical_json_bytes(dict(value))
    replay = loads_canonical_json(raw)
    if type(replay) is not dict:
        raise AssertionError("canonical mapping replay changed")
    return replay


def _measurement(
    *,
    subject_id: str,
    window_role: str,
    values: Mapping[str, int],
    lane: str,
) -> dict[str, Any]:
    parse_content_id(subject_id)
    if lane not in {"OPERATIONAL", "EVALUATION"}:
        _fail("measurement lane changed")
    paths = (
        pre.SHARED_RESOURCE_PATHS
        if lane == "OPERATIONAL"
        else (
            "evaluation.hash_invocations",
            "evaluation.io_mounted_bytes_peak",
            "evaluation.io_output_bytes",
            "evaluation.io_read_bytes",
            "evaluation.io_staged_bytes",
            "evaluation.memory_working_bytes_peak",
            "evaluation.process_launches",
            "evaluation.semantic_integrity_checks",
            "evaluation.semantic_protocol_checks",
        )
    )
    if any(path not in values or type(values[path]) is not int or values[path] < 0 for path in paths):
        _fail("measurement path coverage changed")
    payload = {
        "schema": "acfqp.standard_2048_expression_accounting_measurement.v24",
        "schema_version": SCHEMA_VERSION,
        "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
        "subject_id": subject_id,
        "window_role": window_role,
        "lane": lane,
        "measured_values": [
            {"path": path, "value": values[path]} for path in paths
        ],
        "native_measurement_not_legacy_summary_translation": True,
    }
    return {
        **payload,
        "expression_accounting_measurement_id": content_id(
            pre.FUTURE_DOMAINS["measurement"], payload
        ),
    }


def _write_exact(path: Path, raw: bytes) -> None:
    if path.exists() or not path.parent.is_dir():
        _fail("accounting output path is not fresh")
    with path.open("xb") as stream:
        written = stream.write(raw)
        if written != len(raw):
            _fail("accounting output short write")
        stream.flush()
        os.fsync(stream.fileno())
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    if path.stat().st_size != len(raw):
        _fail("accounting output reread changed")


@dataclass(frozen=True, slots=True)
class MaterializedOperationalBundleV24:
    canonical_bytes: bytes
    bundle_id: str
    output_path: Path
    chain: runtime.OperationalAccountingChainV24

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("operational bundle is not an object")
        return document


@dataclass(frozen=True, slots=True)
class MaterializedEvaluationBundleV24:
    canonical_bytes: bytes
    bundle_id: str
    output_path: Path
    work_vector: WorkVectorV1

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("evaluation bundle is not an object")
        return document


def materialize_operational_bundle_v24(
    *,
    subject_id: str,
    window_role: str,
    route_kind: RouteKindEnum,
    work_scope: ActualWorkScope,
    base_values: Mapping[str, int],
    evidence_document: Mapping[str, Any],
    output_path: Path,
    external_output_bytes: int = 0,
) -> MaterializedOperationalBundleV24:
    values = dict(base_values)
    output_guess = values.get("io.output_bytes", 0)
    if (
        output_guess != 0
        or type(external_output_bytes) is not int
        or external_output_bytes < 0
    ):
        _fail("operational fixed point must begin at native zero")
    evidence = _exact_document(evidence_document, "operational evidence")
    final = None
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values["io.output_bytes"] = output_guess
        measurement = _measurement(
            subject_id=subject_id,
            window_role=window_role,
            values=values,
            lane="OPERATIONAL",
        )
        recorder_id = measurement["expression_accounting_measurement_id"]
        chain = runtime.build_operational_accounting_chain_v24(
            subject_id=subject_id,
            route_kind=route_kind,
            work_scope=work_scope,
            values=values,
            recorder_id=recorder_id,
        )
        payload = {
            "schema": "acfqp.standard_2048_expression_operational_counter_bundle.v24",
            "schema_version": SCHEMA_VERSION,
            "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
            "subject_id": subject_id,
            "window_role": window_role,
            "measurement": measurement,
            "work_vector": chain.work_vector.to_dict(),
            "comparison_vector": chain.comparison_vector.to_dict(),
            "actual_projection_proof": chain.projection_proof.to_dict(),
            "native_zero_attestation": chain.native_zero_attestation.to_dict(),
            "evidence": evidence,
            "output_bytes_fixed_point": output_guess,
            "fixed_point_iteration": iteration,
            "evaluation_work_in_operational_vector": False,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "expression_accounted_counter_bundle_id": content_id(
                pre.FUTURE_DOMAINS["counter_bundle"], payload
            ),
        }
        raw = canonical_json_bytes(document)
        if external_output_bytes + len(raw) == output_guess:
            final = (raw, document, chain)
            break
        output_guess = external_output_bytes + len(raw)
    if final is None:
        _fail("operational output-byte fixed point did not converge")
    raw, document, chain = final
    _write_exact(output_path, raw)
    return MaterializedOperationalBundleV24(
        raw,
        document["expression_accounted_counter_bundle_id"],
        output_path,
        chain,
    )


def materialize_evaluation_bundle_v24(
    *,
    subject_id: str,
    window_role: str,
    base_values: Mapping[str, int],
    evidence_document: Mapping[str, Any],
    output_path: Path,
    external_output_bytes: int = 0,
) -> MaterializedEvaluationBundleV24:
    values = dict(base_values)
    output_guess = values.get("evaluation.io_output_bytes", 0)
    if (
        output_guess != 0
        or type(external_output_bytes) is not int
        or external_output_bytes < 0
    ):
        _fail("evaluation fixed point must begin at native zero")
    evidence = _exact_document(evidence_document, "evaluation evidence")
    final = None
    for iteration in range(MAXIMUM_FIXED_POINT_ITERATIONS):
        values["evaluation.io_output_bytes"] = output_guess
        measurement = _measurement(
            subject_id=subject_id,
            window_role=window_role,
            values=values,
            lane="EVALUATION",
        )
        recorder_id = measurement["expression_accounting_measurement_id"]
        vector, zero = runtime.build_evaluation_work_vector_v24(
            subject_id=subject_id,
            values=values,
            recorder_id=recorder_id,
        )
        payload = {
            "schema": "acfqp.standard_2048_expression_evaluation_counter_bundle.v24",
            "schema_version": SCHEMA_VERSION,
            "expression_accounted_preregistration_id": pre.PREREGISTRATION_ID,
            "subject_id": subject_id,
            "window_role": window_role,
            "measurement": measurement,
            "work_vector": vector.to_dict(),
            "comparison_vector": None,
            "actual_projection_proof": None,
            "native_zero_attestation": zero.to_dict(),
            "evidence": evidence,
            "output_bytes_fixed_point": output_guess,
            "fixed_point_iteration": iteration,
            "evaluation_lane_excluded_from_operational_comparison": True,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "expression_accounted_counter_bundle_id": content_id(
                pre.FUTURE_DOMAINS["counter_bundle"], payload
            ),
        }
        raw = canonical_json_bytes(document)
        if external_output_bytes + len(raw) == output_guess:
            final = (raw, document, vector)
            break
        output_guess = external_output_bytes + len(raw)
    if final is None:
        _fail("evaluation output-byte fixed point did not converge")
    raw, document, vector = final
    _write_exact(output_path, raw)
    return MaterializedEvaluationBundleV24(
        raw,
        document["expression_accounted_counter_bundle_id"],
        output_path,
        vector,
    )


__all__ = (
    "MaterializedEvaluationBundleV24",
    "MaterializedOperationalBundleV24",
    "materialize_evaluation_bundle_v24",
    "materialize_operational_bundle_v24",
)
