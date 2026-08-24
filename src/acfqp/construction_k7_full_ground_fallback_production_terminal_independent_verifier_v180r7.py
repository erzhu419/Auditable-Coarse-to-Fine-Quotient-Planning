"""Producer-free replay of the fresh V180r7 fallback V6-to-V9 lift."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_fallback_execution_authorization_v180r7 as authorization
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_domain_registry_extension_v180r7 as domains
from acfqp.accounting_v1 import (
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope, derive_actual_projection_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


EXPECTED_TERMINAL_BUNDLE_ID = "0" * 64
EXPECTED_TERMINAL_BYTE_COUNT = 0
EXPECTED_TERMINAL_SHA256 = "0" * 64
EXPECTED_VERIFICATION_ID = "0" * 64
EXPECTED_VERIFICATION_BYTE_COUNT = 0
EXPECTED_VERIFICATION_SHA256 = "0" * 64

_ROUTES = (
    RouteKindEnum.ABSTRACT_FAILED_PREFIX,
    RouteKindEnum.LOCAL_ATTEMPT,
    RouteKindEnum.DIRECT_FALLBACK,
)
_SOURCE_VECTOR_KEY_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_FAILED_PREFIX: "supervised_wrapper_work_vector",
    RouteKindEnum.LOCAL_ATTEMPT: "local_recovery_work_vector",
    RouteKindEnum.DIRECT_FALLBACK: "direct_fallback_work_vector",
}
_SCOPE_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_FAILED_PREFIX: ActualWorkScope.COMMON_PREFIX,
    RouteKindEnum.LOCAL_ATTEMPT: ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    RouteKindEnum.DIRECT_FALLBACK: ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
}
_OUTPUT_FILENAMES = {
    "ACTUAL_PROJECTION_PROOF.json",
    "BUSINESS_RESULT.json",
    "COMPARISON_VECTOR.json",
    "COUNTER_RECORD_SET.json",
    "OPERATIONAL_TRACE.json",
    "OUTPUT_MANIFEST.json",
    "TERMINAL_ARTIFACT.json",
    "WORK_VECTOR.json",
}
_TOP_LEVEL_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "development_fixture_only",
    "finalizer_output_bytes",
    "fixed_point_iteration",
    "formalization_contract_id",
    "fresh_v180r7_observed_occurrence_present",
    "historical_summary_translation_used",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "output_bytes_fixed_point",
    "partial_campaign_cannot_unlock_any_gate",
    "production_execution_protocol_id",
    "production_execution_slot",
    "production_occurrence_receipt",
    "production_terminal_bundle_id",
    "registered_counter_to_counter_v6_to_v9_lift_used",
    "schema",
    "source_occurrence_accounting_bundle",
    "source_output_bytes",
    "source_output_inventory",
    "terminal_code",
    "three_route_family_vectors_remain_separate",
    "v9_lifted_route_components",
    "v9_paths_absent_from_source_vector_have_explicit_native_zero_lineage",
}
_RECEIPT_FIELDS = {
    "execution_nonce",
    "historical_summary_translation_used",
    "logical_occurrence_id",
    "native_v6_counter_records_used",
    "predecessor_occurrence_slot_id",
    "preexisting_occurrence_output_used",
    "production_execution_protocol_id",
    "production_execution_slot_id",
    "production_execution_started_by_this_call",
    "production_occurrence_receipt_id",
    "query_ordinal",
    "registered_v6_to_v9_counter_lift_required",
    "schema",
    "source_counter_registry_id",
    "source_occurrence_accounting_bundle_id",
    "source_output_bytes",
    "source_output_inventory",
    "source_shared_resource_receipt_ids",
    "source_work_vector_ids",
    "target_counter_registry_id",
    "terminal_code",
}
_COMPONENT_FIELDS = {
    "counter_lift_lineage",
    "source_work_vector",
    "v9_actual_projection_proof",
    "v9_comparison_vector",
    "v9_native_zero_attestation",
    "v9_work_vector",
}
_LINEAGE_FIELDS = {
    "finalizer_output_increment",
    "historical_summary_translation_used",
    "inherited_semantics_exact",
    "lineage_id",
    "path",
    "route_kind",
    "schema",
    "source_counter_record_id",
    "source_counter_registry_id",
    "source_value",
    "source_value_plus_finalizer_increment_equals_target_value",
    "source_work_vector_id",
    "target_counter_record_id",
    "target_counter_registry_id",
    "target_path_absent_from_source_vector_native_zero_observation",
    "value",
}
_FORMALIZATION_CONTRACT_ID = (
    "f392e9178e8c9c69150567ce210ad146ab96d61aa5925c34b133415fa86737fd"
)


class ConstructionK7FullGroundFallbackIndependentVerifierV180r7Error(
    RuntimeError
):
    """The fresh fallback output or V9 lift changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FullGroundFallbackIndependentVerifierV180r7Error(message)


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _source_authorization() -> tuple[dict[str, Any], dict[str, Any]]:
    frozen = authorization.freeze_fallback_execution_authorization_v180r7()
    document = frozen.to_document()
    source_root = Path(__file__).resolve().parent
    repository_root = source_root.parents[1]
    for fact in document["source_facts"]:
        raw = (source_root / fact["filename"]).read_bytes()
        if fact != {
            "filename": fact["filename"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }:
            _fail("V180r7 authorized source bytes changed")
    for fact in document["retained_predecessor_input_facts"]:
        raw = (repository_root / fact["relative_path"]).read_bytes()
        if fact != {
            "relative_path": fact["relative_path"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }:
            _fail("V180r7 retained predecessor bytes changed")
    matches = [
        row
        for row in protocol.freeze_all_path_production_execution_protocol_v180r3()
        .to_document()["production_execution_slots"]
        if row["terminal_code"] == "FULL_GROUND_FALLBACK"
    ]
    if len(matches) != 1 or document["production_execution_slot"] != matches[0]:
        _fail("V180r7 authorization crossed its execution slot")
    return document, matches[0]


def _inventory(root: Path) -> list[dict[str, Any]]:
    rows = [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "canonical_byte_count": len(raw),
            "canonical_sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path in sorted(item for item in root.rglob("*") if item.is_file())
        for raw in (path.read_bytes(),)
    ]
    if {row["relative_path"] for row in rows} != _OUTPUT_FILENAMES:
        _fail("retained fallback output role set changed")
    return rows


def _source_vectors(root: Path) -> tuple[WorkVectorV1, ...]:
    document = _object((root / "WORK_VECTOR.json").read_bytes(), "source V6 vectors")
    if not (
        set(document)
        == {
            "artifact_role",
            "direct_fallback_work_vector",
            "io.output_bytes",
            "local_recovery_work_vector",
            "marginal_route_upper_compliance_authority",
            "route_family_vectors_remain_separate",
            "schema",
            "supervised_wrapper_work_vector",
        }
        and document["artifact_role"] == "WORK_VECTOR"
        and document["route_family_vectors_remain_separate"] is True
        and document["marginal_route_upper_compliance_authority"] is False
    ):
        _fail("source V6 work-vector artifact changed")
    registry = registry_v6.official_counter_registry_v6()
    vectors = tuple(
        WorkVectorV1.from_dict(document[_SOURCE_VECTOR_KEY_BY_ROUTE[route]], registry)
        for route in _ROUTES
    )
    if not (
        tuple(row.route_kind for row in vectors) == _ROUTES
        and all(len(row.records) == 202 for row in vectors)
        and vectors[0].values["io.output_bytes"] == document["io.output_bytes"]
        and vectors[2].values["fallback.ground_steps"] > 0
        and vectors[2].values["route.attempts"] == 1
        and vectors[2].values["route.successes"] == 1
    ):
        _fail("source V6 route semantics changed")
    return vectors


def _lineage_and_target(
    *,
    source_vector: WorkVectorV1,
    receipt_id: str,
    finalizer_output_bytes: int,
) -> tuple[list[dict[str, Any]], WorkVectorV1]:
    source_registry = registry_v6.official_counter_registry_v6()
    target_registry = registry_v9.official_counter_registry_v9()
    source_records = {row.path: row for row in source_vector.records}
    recorder_id = hashlib.sha256(
        b"acfqp:v180r7:v9-lift-recorder\x00"
        + receipt_id.encode()
        + b"\x00"
        + source_vector.route_kind.value.encode()
    ).hexdigest()
    records = []
    lineage = []
    for path in sorted(target_registry.by_path):
        source_record = source_records.get(path)
        value = source_record.value if source_record is not None else 0
        finalizer_increment = 0
        if (
            source_vector.route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
            and path == "io.output_bytes"
        ):
            value += finalizer_output_bytes
            finalizer_increment = finalizer_output_bytes
        record = CounterRecordV1.observe(
            target_registry, path, value, recorder_id=recorder_id
        )
        records.append(record)
        payload = {
            "schema": "acfqp.full_ground_fallback_v9_lift_lineage.v180r7",
            "source_counter_registry_id": source_registry.registry_id,
            "target_counter_registry_id": target_registry.registry_id,
            "source_work_vector_id": source_vector.work_vector_id,
            "route_kind": source_vector.route_kind.value,
            "path": path,
            "source_counter_record_id": (
                source_record.record_id if source_record is not None else None
            ),
            "source_value": source_record.value if source_record is not None else None,
            "target_counter_record_id": record.record_id,
            "value": value,
            "inherited_semantics_exact": source_record is not None,
            "source_value_plus_finalizer_increment_equals_target_value": (
                source_record is not None
                and source_record.value + finalizer_increment == value
            ),
            "finalizer_output_increment": finalizer_increment,
            "target_path_absent_from_source_vector_native_zero_observation": (
                source_record is None
            ),
            "historical_summary_translation_used": False,
        }
        lineage.append(
            {
                **payload,
                "lineage_id": domains.extension_content_id_v180r7(
                    domains.CONSTRUCTION_K7_FALLBACK_V9_LIFT_LINEAGE_V180R7_DOMAIN,
                    payload,
                ),
            }
        )
    vector = WorkVectorV1(
        target_registry.registry_id,
        source_vector.subject_id,
        source_vector.route_kind,
        tuple(records),
    )
    return lineage, vector


def _expected_component(
    *, source_vector: WorkVectorV1, receipt_id: str, finalizer_output_bytes: int
) -> dict[str, Any]:
    lineage, vector = _lineage_and_target(
        source_vector=source_vector,
        receipt_id=receipt_id,
        finalizer_output_bytes=finalizer_output_bytes,
    )
    registry = registry_v9.official_counter_registry_v9()
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=_SCOPE_BY_ROUTE[source_vector.route_kind],
    )
    zero = NativeZeroAttestationV1.derive(vector, registry)
    return {
        "source_work_vector": source_vector.to_dict(),
        "v9_work_vector": vector.to_dict(),
        "v9_comparison_vector": comparison.to_dict(),
        "v9_actual_projection_proof": proof.to_dict(),
        "v9_native_zero_attestation": zero.to_dict(),
        "counter_lift_lineage": lineage,
    }


def _replay_terminal_fixed_point(
    *,
    slot: Mapping[str, Any],
    receipt: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    inventory: list[dict[str, Any]],
    source_vectors: tuple[WorkVectorV1, ...],
) -> bytes:
    source_output_bytes = sum(row["canonical_byte_count"] for row in inventory)
    guess = 0
    for iteration in range(32):
        components = [
            _expected_component(
                source_vector=vector,
                receipt_id=receipt["production_occurrence_receipt_id"],
                finalizer_output_bytes=guess,
            )
            for vector in source_vectors
        ]
        payload = {
            "schema": "acfqp.full_ground_fallback_production_terminal_bundle.v180r7",
            "formalization_contract_id": _FORMALIZATION_CONTRACT_ID,
            "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
            "production_execution_slot": dict(slot),
            "terminal_code": "FULL_GROUND_FALLBACK",
            "production_occurrence_receipt": dict(receipt),
            "source_occurrence_accounting_bundle": dict(source_bundle),
            "source_output_inventory": inventory,
            "v9_lifted_route_components": components,
            "source_output_bytes": source_output_bytes,
            "finalizer_output_bytes": guess,
            "output_bytes_fixed_point": source_output_bytes + guess,
            "fixed_point_iteration": iteration,
            "fresh_v180r7_observed_occurrence_present": True,
            "three_route_family_vectors_remain_separate": True,
            "registered_counter_to_counter_v6_to_v9_lift_used": True,
            "v9_paths_absent_from_source_vector_have_explicit_native_zero_lineage": True,
            "historical_summary_translation_used": False,
            "development_fixture_only": False,
            "partial_campaign_cannot_unlock_any_gate": True,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "production_terminal_bundle_id": domains.extension_content_id_v180r7(
                domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r7 independent fixed-point replay did not converge")


def verify_full_ground_fallback_terminal_independently_v180r7(
    terminal_bytes: bytes, output_root: Path
) -> dict[str, Any]:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("retained full-fallback output root is absent")
    authorization_document, slot = _source_authorization()
    inventory = _inventory(output_root)
    document = _object(terminal_bytes, "V180r7 fallback terminal")
    if set(document) != _TOP_LEVEL_FIELDS:
        _fail("V180r7 fallback terminal field set changed")
    payload = dict(document)
    bundle_id = payload.pop("production_terminal_bundle_id", None)
    if not (
        document["schema"]
        == "acfqp.full_ground_fallback_production_terminal_bundle.v180r7"
        and document["production_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and document["production_execution_slot"] == slot
        and document["terminal_code"] == "FULL_GROUND_FALLBACK"
        and bundle_id
        == domains.extension_content_id_v180r7(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7_DOMAIN,
            payload,
        )
        and (
            EXPECTED_TERMINAL_BUNDLE_ID == "0" * 64
            or (
                bundle_id == EXPECTED_TERMINAL_BUNDLE_ID
                and len(terminal_bytes) == EXPECTED_TERMINAL_BYTE_COUNT
                and hashlib.sha256(terminal_bytes).hexdigest()
                == EXPECTED_TERMINAL_SHA256
            )
        )
    ):
        _fail("V180r7 fallback terminal identity changed")
    receipt = document["production_occurrence_receipt"]
    if type(receipt) is not dict or set(receipt) != _RECEIPT_FIELDS:
        _fail("V180r7 fallback receipt field set changed")
    receipt_payload = dict(receipt)
    receipt_id = receipt_payload.pop("production_occurrence_receipt_id", None)
    source_registry = registry_v6.official_counter_registry_v6()
    target_registry = registry_v9.official_counter_registry_v9()
    source_vectors = _source_vectors(output_root)
    source_bundle = document["source_occurrence_accounting_bundle"]
    if type(source_bundle) is not dict:
        _fail("source occurrence bundle is not an object")
    source_bundle_payload = dict(source_bundle)
    source_bundle_id = source_bundle_payload.pop(
        "occurrence_accounting_bundle_id", None
    )
    if not (
        source_bundle_id
        == content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
            source_bundle_payload,
        )
        and source_bundle["occurrence_id"] == authorization.LOGICAL_OCCURRENCE_ID
        and source_bundle["scientific_terminal_code"] == "FULL_GROUND_FALLBACK"
        and source_bundle["shared_resource_path_count"] == 9
        and len(source_bundle["shared_resource_receipt_ids"]) == 9
        and source_bundle["component_work_vector_ids"]
        == [row.work_vector_id for row in source_vectors]
        and source_bundle["route_family_work_vectors_issued"] == 3
        and source_bundle["route_family_exclusivity_preserved"] is True
    ):
        _fail("source occurrence accounting bundle identity changed")
    if not (
        receipt_id
        == domains.extension_content_id_v180r7(
            domains.CONSTRUCTION_K7_FALLBACK_OCCURRENCE_RECEIPT_V180R7_DOMAIN,
            receipt_payload,
        )
        and receipt["production_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and receipt["production_execution_slot_id"]
        == slot["production_execution_slot_id"]
        and receipt["predecessor_occurrence_slot_id"]
        == slot["predecessor_occurrence_slot_id"]
        and receipt["execution_nonce"] == slot["execution_nonce"]
        and receipt["terminal_code"] == "FULL_GROUND_FALLBACK"
        and receipt["logical_occurrence_id"] == authorization.LOGICAL_OCCURRENCE_ID
        and receipt["query_ordinal"] == authorization.QUERY_ORDINAL
        and receipt["source_occurrence_accounting_bundle_id"] == source_bundle_id
        and receipt["source_counter_registry_id"] == source_registry.registry_id
        and receipt["target_counter_registry_id"] == target_registry.registry_id
        and receipt["source_work_vector_ids"]
        == [row.work_vector_id for row in source_vectors]
        and receipt["source_shared_resource_receipt_ids"]
        == source_bundle["shared_resource_receipt_ids"]
        and len(receipt["source_shared_resource_receipt_ids"]) == 9
        and receipt["source_output_inventory"] == inventory
        and receipt["source_output_bytes"]
        == sum(row["canonical_byte_count"] for row in inventory)
        and receipt["production_execution_started_by_this_call"] is True
        and receipt["preexisting_occurrence_output_used"] is False
        and receipt["native_v6_counter_records_used"] is True
        and receipt["registered_v6_to_v9_counter_lift_required"] is True
        and receipt["historical_summary_translation_used"] is False
    ):
        _fail("V180r7 fallback receipt semantics changed")
    components = document["v9_lifted_route_components"]
    if type(components) is not list or len(components) != 3:
        _fail("V180r7 lifted component denominator changed")
    for component, source_vector, route in zip(
        components, source_vectors, _ROUTES, strict=True
    ):
        if type(component) is not dict or set(component) != _COMPONENT_FIELDS:
            _fail("V180r7 lifted component field set changed")
        expected_lineage, expected_vector = _lineage_and_target(
            source_vector=source_vector,
            receipt_id=receipt_id,
            finalizer_output_bytes=len(terminal_bytes),
        )
        if any(
            set(row) != _LINEAGE_FIELDS
            for row in component["counter_lift_lineage"]
        ):
            _fail("V180r7 lift lineage field set changed")
        observed_vector = WorkVectorV1.from_dict(component["v9_work_vector"], target_registry)
        comparison_profile = registry_v9.official_comparison_profile_v9(target_registry)
        actual_profile = registry_v9.official_actual_projection_profile_v9(
            target_registry, comparison_profile
        )
        comparison, proof = derive_actual_projection_v1(
            expected_vector,
            target_registry,
            comparison_profile,
            actual_profile,
            source_lane=LaneEnum.OPERATIONAL,
            work_scope=_SCOPE_BY_ROUTE[route],
        )
        zero = NativeZeroAttestationV1.derive(expected_vector, target_registry)
        if not (
            component["source_work_vector"] == source_vector.to_dict()
            and component["counter_lift_lineage"] == expected_lineage
            and observed_vector == expected_vector
            and component["v9_comparison_vector"] == comparison.to_dict()
            and component["v9_actual_projection_proof"] == proof.to_dict()
            and component["v9_native_zero_attestation"] == zero.to_dict()
            and len(observed_vector.records) == 269
        ):
            _fail("V180r7 record lift or V9 projection changed")
    if _replay_terminal_fixed_point(
        slot=slot,
        receipt=receipt,
        source_bundle=source_bundle,
        inventory=inventory,
        source_vectors=source_vectors,
    ) != terminal_bytes:
        _fail("V180r7 producer-free terminal fixed-point bytes changed")
    if not (
        document["source_output_inventory"] == inventory
        and document["source_output_bytes"] == receipt["source_output_bytes"]
        and document["finalizer_output_bytes"] == len(terminal_bytes)
        and document["output_bytes_fixed_point"]
        == document["source_output_bytes"] + len(terminal_bytes)
        and document["fresh_v180r7_observed_occurrence_present"] is True
        and document["three_route_family_vectors_remain_separate"] is True
        and document["registered_counter_to_counter_v6_to_v9_lift_used"] is True
        and document[
            "v9_paths_absent_from_source_vector_have_explicit_native_zero_lineage"
        ]
        is True
        and document["historical_summary_translation_used"] is False
        and document["development_fixture_only"] is False
        and document["partial_campaign_cannot_unlock_any_gate"] is True
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
    ):
        _fail("V180r7 output fixed point or claim lock changed")
    verification_payload = {
        "schema": "acfqp.full_ground_fallback_execution_verification.v180r7",
        "fallback_execution_authorization_id": authorization_document[
            "fallback_execution_authorization_id"
        ],
        "production_terminal_bundle_id": bundle_id,
        "production_terminal_bytes_sha256": hashlib.sha256(
            terminal_bytes
        ).hexdigest(),
        "source_occurrence_accounting_bundle_id": source_bundle_id,
        "retained_output_file_count": len(inventory),
        "source_v6_work_vector_count": len(source_vectors),
        "source_v6_counter_record_count": sum(
            len(row.records) for row in source_vectors
        ),
        "lifted_v9_work_vector_count": len(components),
        "lifted_v9_counter_record_count": 3 * 269,
        "shared_resource_receipt_count": 9,
        "source_records_replayed_without_producer_import": True,
        "registered_v6_to_v9_counter_lift_reconstructed": True,
        "three_route_family_vectors_remain_separate": True,
        "terminal_output_fixed_point_replayed": True,
        "fresh_single_path_verified": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v180r7(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_VERIFICATION_V180R7_DOMAIN,
            verification_payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FullGroundFallbackVerificationV180r7:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return _object(self.canonical_bytes, "V180r7 fallback verification")


def freeze_full_ground_fallback_verification_v180r7(
    terminal_bytes: bytes, output_root: Path
) -> FullGroundFallbackVerificationV180r7:
    document = verify_full_ground_fallback_terminal_independently_v180r7(
        terminal_bytes, output_root
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(raw) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V180r7 frozen fallback verification changed")
    return FullGroundFallbackVerificationV180r7(
        _ISSUER,
        raw,
        document["verification_id"],
    )


__all__ = (
    "EXPECTED_TERMINAL_BUNDLE_ID",
    "EXPECTED_VERIFICATION_ID",
    "freeze_full_ground_fallback_verification_v180r7",
    "verify_full_ground_fallback_terminal_independently_v180r7",
)
