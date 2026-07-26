"""V0-054A same-query H2 durable proof-state continuation.

This module is a downstream consumer of the owner-bound V0-053 result.  It
materializes the final V3 epoch and exactly thirty lower proof values into a
canonical, content-addressed checkpoint.  Fresh Python processes may load that
checkpoint for the same model/query/threshold identity, re-run four candidate
roots plus an independent selected root, and reuse only the lower proof nodes.

The registered control is deliberately narrow.  It is not cross-query cache
authority, generic persistence, crash recovery, sample-efficiency evidence, or
workload economics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import argparse
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import acfqp.h2_temporal_incremental_proof_dag_v1 as temporal
import acfqp.h2_durable_transport_v1 as durable_transport
import acfqp.live_query_local_epoch_invalidation_v1 as live
import acfqp.multistep_query_refinement_v1 as multistep
import acfqp.partial_model_planner_v1 as planner
import acfqp.partial_sound_audit_v1 as audit
from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
)
from acfqp.h2_durable_transport_v1 import (
    DurableH2TransportInvariantViolation,
    parse_frozen_contingent_abstract_plan_v1,
    parse_frozen_partial_audit_thresholds_v1,
    parse_query_scoped_partial_rapm_v3,
)
from acfqp.partial_sound_audit_v1 import FrozenContingentAbstractPlanV1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.17.0"
PROFILE_KEY = "lmb_h2_same_query_durable_proof_state_v0"
SUCCESS_STATUS = "CERTIFIED_REGISTERED_H2_SAME_QUERY_DURABLE_PROOF_STATE_CONTROL"

EXPECTED_SOURCE_LOWER_ENTRY_COUNT = 30
EXPECTED_SOURCE_LIVE_RESULT_ID = (
    "5e46f0eda3f6d9c96e955315034829913dc248d09ed1a73ca8384d4cbcd65d44"
)
EXPECTED_FINAL_THRESHOLDS_ID = (
    "019ee51eed8dc413dfecf11de033657dcb97caa3e03187e9051f8c732e28ed70"
)
EXPECTED_FINAL_BUILD_RESULT_ID = (
    "1789f7cb364bc7012fe392df494057dec6bee29614e8ffb281338e04f7ab4dc9"
)
EXPECTED_FINAL_THRESHOLD_REBASE_ID = (
    "1f15a26ad654249fea95af7813930ccf68b5677f92ee99ad3930495d3eac2e13"
)
EXPECTED_FINAL_EVIDENCE_REQUEST_ID = (
    "dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf"
)
EXPECTED_FINAL_EVIDENCE_BUNDLE_ID = (
    "9da973649ab05959fc3855467d3a314017a659ff0feb61dd0ab18c0c4824c20a"
)
EXPECTED_FINAL_CANDIDATE_REQUEST_IDS = (
    "53e246cf2ce049977193a5a278913d0d990bb3140dba2deb6c2b88b84d8fbfb8",
    "16ad10f3000d77c479680c81c7ce8a8a4daa84bc5193cff9d3a1ddf315837805",
    "d7b11f33606ed33545d1f42c2f0e949363fa95966ce1236b4cf280fdf6c474b0",
    "68393a1218ea9f5aff34bc29ee73c6c07f4fb4a39678de0b6187193832a4c545",
)
EXPECTED_FINAL_CANDIDATE_INNER_AUDIT_IDS = (
    "6a68944dba08b7b2266cd1376d60569de753d02cbcfab29f7edc34c337926d54",
    "c3d55e3813602189323309fa695135c9026c06977fd6a9b6fca5ff3ab8667641",
    "feb9c5e64f3046f78479ff12d8d85c283e8995cf4ef33ce4b662e759eee16e99",
    "1657a43346196feb0b0f7221dab70d1ee0c417c5c2944990ae6375f7ec481054",
)
EXPECTED_FINAL_PROPOSAL_ID = (
    "fb23e41d80f2597622443fe71ac57516ed12298f66a2ad2e56d4c6c8344a8acb"
)
EXPECTED_FINAL_PLAN_ID = (
    "0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb"
)
EXPECTED_FINAL_SELECTED_REQUEST_ID = (
    "961f01d6fd9bcf603372db1fc773932913cb17610758d09f1fb9f39da863bf47"
)
EXPECTED_FINAL_SELECTED_RECEIPT_ID = (
    "ee518c66dd4850db1ccc35a391b977d22798987c4154f56e18a962b8c41bf8d0"
)
EXPECTED_FINAL_SELECTED_INNER_AUDIT_ID = (
    "6a68944dba08b7b2266cd1376d60569de753d02cbcfab29f7edc34c337926d54"
)
EXPECTED_FINAL_SELECTED_WRAPPER_AUDIT_ID = (
    "81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529"
)
EXPECTED_FINAL_EXECUTION_ID = (
    "3cbe43d106be12824e8d15a27a8fc0e82d37cf37a8c772a191eacd2b5fb77279"
)
EXPECTED_WARM_OCCURRENCE_IDS = (
    "6291c9f3e29ce6bd782d1fbdfc1d05eb016aef10b0b69e8605acbbd9c079177c",
    "44ba0b14093527880475a57689f6bfd828af7451fc4342e860bc938a35429cac",
)
EXPECTED_DURABLE_PROTOCOL_ID = (
    "764fc56721c2b65fc3c55b644053814715b2bb2507046f4af80e34c7d8eed13e"
)
EXPECTED_DURABLE_PAYLOAD_ID = (
    "cdba69f2520255561ad7708b2037faae36d64ca69189328e4d50e70de172f6aa"
)
EXPECTED_DURABLE_MANIFEST_ID = (
    "3cec7e67f116cc9ec94166e9340afd463b8fca7116872d1f0549aace7312ba7d"
)
EXPECTED_DURABLE_COMMIT_ID = (
    "a4f5ef9fa083d04c9e3e8bc847c137588433b804e7c4f9c423a8cf64c08fbaa3"
)
EXPECTED_DURABLE_SNAPSHOT_ID = (
    "74510d7e4ec5fbcb701ac9dbeed8c5d9ad718059c8fe2c6e65ab98d69feb922f"
)
EXPECTED_WARM_OCCURRENCE_RESULT_IDS = (
    "dbee0b5aa0eddcad7a1fba64b1d40469fe4d78c2e92c90dc539cebf1ab97e5fb",
    "3155b7b9420a04a55f353a2f0f5e61d311340df8dc2a5017216917664d186d4d",
)
EXPECTED_WARM_ARM_IDS = (
    (
        "cf76a93b886e06e1d4a824c15174ae869e83ef808e3d4c9ef77820c110579f09",
        "fe18be01e1d8c7f0c5155bc7b463f02339407ee478d33cf215a56c5241062af2",
        "9b27ed49fb66d76c89e9681782609d8dea40b14e06dee8e4959f3c61ddb7d6f1",
    ),
    (
        "31037707c15d424f058c1374a2216b3c7696ab2a913765521e1d5d0b30eb2ffa",
        "ec97730ed42458e13312f2859c6bdc9eb1424135b3f47ef110d8b69f0a228526",
        "c4d71ed835b17f437158b1bdeafaa8552729958ce3deeb34a2a1e6b2ad4df940",
    ),
)
EXPECTED_DURABLE_CAMPAIGN_RESULT_ID = (
    "80a97998c5ef1c0a8323615b51ea9c8abcd786587ef877d84c00257eded43ce0"
)
EXPECTED_DURABLE_VERIFICATION_REPORT_ID = (
    "d4396c5b6207a31d8babf706a7481577b4a732ee0916bdb779580e1094560ce0"
)

DOMAIN_TAGS = {
    "occurrence": "acfqp:h2-durable-logical-occurrence:v1",
    "protocol": "acfqp:h2-durable-workload-protocol:v1",
    "value": "acfqp:h2-durable-lower-proof-entry:v1",
    "payload": "acfqp:h2-durable-lower-proof-payload:v1",
    "manifest": "acfqp:h2-durable-proof-checkpoint-manifest:v1",
    "commit": "acfqp:h2-durable-proof-checkpoint-commit:v1",
    "snapshot": "acfqp:h2-durable-proof-checkpoint-byte-snapshot:v1",
    "load_receipt": "acfqp:h2-durable-proof-checkpoint-load:v1",
    "proposal": "acfqp:h2-durable-plan-proposal:v1",
    "root": "acfqp:h2-durable-occurrence-root:v1",
    "arm": "acfqp:h2-durable-occurrence-arm:v1",
    "occurrence_result": "acfqp:h2-durable-proof-occurrence:v1",
    "campaign_result": "acfqp:h2-durable-proof-result:v1",
    "verification": "acfqp:h2-durable-verification-report:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-054A content domains must be unique")

_LEASE_ISSUER = object()
_RESULT_ISSUER = object()


class DurableH2InvariantViolation(ValueError):
    """The durable checkpoint, proof continuation, or claim is invalid."""


class DurableH2ArmKind(str, Enum):
    REQUEST_RESET = "REQUEST_RESET"
    OCCURRENCE_RESET_GLOBAL_DAG = "OCCURRENCE_RESET_GLOBAL_DAG"
    DURABLE_CROSS_PROCESS_CONTINUATION = "DURABLE_CROSS_PROCESS_CONTINUATION"


@contextmanager
def _deny_lmb_ground_kernel_access() -> Any:
    """Make any accidental warm-worker ground-kernel access fail closed."""

    from acfqp.domains.matching_buffer import LMBKernel

    method_names = (
        "__post_init__",
        "registered_reward_features",
        "registered_goals",
        "reward_upper_bound",
        "_validate_dag_depth",
        "initial_distribution",
        "_validate_state",
        "actions",
        "step",
        "is_terminal",
    )
    originals = {name: getattr(LMBKernel, name) for name in method_names}

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise DurableH2InvariantViolation(
            "warm durable proof worker attempted target ground-kernel access"
        )

    try:
        for name in method_names:
            setattr(LMBKernel, name, forbidden)
        yield
    finally:
        for name, original in originals.items():
            setattr(LMBKernel, name, original)


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise DurableH2InvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise DurableH2InvariantViolation(f"{name} is not a canonical content ID") from error


def _source_sha(module: Any) -> str:
    return hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()


def _exact_mapping(
    value: Any,
    fields: set[str],
    name: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise DurableH2InvariantViolation(f"{name} has missing or unknown fields")
    return value


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DurableH2InvariantViolation(f"{name} must be an integer >= {minimum}")
    return value


def _fraction(value: Any, name: str) -> Fraction:
    if type(value) is Fraction:
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
            raise DurableH2InvariantViolation(f"{name} is not an exact rational")
        result = Fraction(numerator, denominator)
        if result.numerator != numerator or result.denominator != denominator:
            raise DurableH2InvariantViolation(f"{name} rational is not reduced")
        return result
    raise DurableH2InvariantViolation(f"{name} is not exact")


def _normalize_document(value: Any) -> Any:
    """Convert ``loads_canonical_json`` Fractions back to public documents."""

    if type(value) is Fraction:
        return {"numerator": value.numerator, "denominator": value.denominator}
    if type(value) is list:
        return [_normalize_document(item) for item in value]
    if type(value) is dict:
        return {key: _normalize_document(item) for key, item in value.items()}
    return value


def _occurrence_id(label: str) -> str:
    return _content_id(
        "occurrence",
        {
            "schema": "acfqp.h2_durable_logical_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "label": label,
        },
    )


SOURCE_OCCURRENCE_ID = _occurrence_id("SOURCE_OCCURRENCE")
WARM_OCCURRENCE_IDS = (
    _occurrence_id("WARM_OCCURRENCE_1"),
    _occurrence_id("WARM_OCCURRENCE_2"),
)
if WARM_OCCURRENCE_IDS != EXPECTED_WARM_OCCURRENCE_IDS:  # pragma: no cover
    raise RuntimeError("V0-054A warm occurrence identities changed")


@dataclass(frozen=True, slots=True)
class DurableH2WorkloadProtocolV1:
    source_live_result_id: str
    model_id: str
    thresholds_id: str
    proof_semantics_id: str
    source_occurrence_id: str = SOURCE_OCCURRENCE_ID
    warm_occurrence_ids: tuple[str, str] = WARM_OCCURRENCE_IDS
    occurrence_order: tuple[str, str, str] = (
        SOURCE_OCCURRENCE_ID,
        *WARM_OCCURRENCE_IDS,
    )
    source_lower_entry_count: int = EXPECTED_SOURCE_LOWER_ENTRY_COUNT
    warm_request_count: int = 5
    warm_resolution_count: int = 55
    fresh_process_required: bool = True
    canonical_json_only: bool = True
    roots_persisted: bool = False
    same_query_only: bool = True
    live_source_sha256: str = field(default_factory=lambda: _source_sha(live))
    temporal_source_sha256: str = field(default_factory=lambda: _source_sha(temporal))
    planner_source_sha256: str = field(default_factory=lambda: _source_sha(planner))
    audit_source_sha256: str = field(default_factory=lambda: _source_sha(audit))
    multistep_source_sha256: str = field(
        default_factory=lambda: _source_sha(multistep)
    )
    transport_source_sha256: str = field(
        default_factory=lambda: _source_sha(durable_transport)
    )

    def __post_init__(self) -> None:
        for value in (
            self.source_live_result_id,
            self.model_id,
            self.thresholds_id,
            self.proof_semantics_id,
            self.source_occurrence_id,
            *self.warm_occurrence_ids,
            *self.occurrence_order,
        ):
            _cid(value, "durable protocol identity")
        for value in (
            self.live_source_sha256,
            self.temporal_source_sha256,
            self.planner_source_sha256,
            self.audit_source_sha256,
            self.multistep_source_sha256,
            self.transport_source_sha256,
        ):
            _cid(value, "durable protocol source digest")
        if (
            self.source_live_result_id != EXPECTED_SOURCE_LIVE_RESULT_ID
            or self.source_live_result_id != live.EXPECTED_LIVE_RESULT_ID
            or self.model_id != live.EXPECTED_FINAL_MODEL_ID
            or self.thresholds_id != EXPECTED_FINAL_THRESHOLDS_ID
            or self.proof_semantics_id != live.EXPECTED_SEMANTICS_ID
            or self.source_occurrence_id != SOURCE_OCCURRENCE_ID
            or self.warm_occurrence_ids != WARM_OCCURRENCE_IDS
            or self.occurrence_order
            != (SOURCE_OCCURRENCE_ID, *WARM_OCCURRENCE_IDS)
            or self.source_lower_entry_count != 30
            or self.warm_request_count != 5
            or self.warm_resolution_count != 55
            or self.fresh_process_required is not True
            or self.canonical_json_only is not True
            or self.roots_persisted is not False
            or self.same_query_only is not True
            or self.live_source_sha256 != _source_sha(live)
            or self.temporal_source_sha256 != _source_sha(temporal)
            or self.planner_source_sha256 != _source_sha(planner)
            or self.audit_source_sha256 != _source_sha(audit)
            or self.multistep_source_sha256 != _source_sha(multistep)
            or self.transport_source_sha256 != _source_sha(durable_transport)
        ):
            raise DurableH2InvariantViolation("durable workload protocol changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_workload_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_live_result_id": self.source_live_result_id,
            "model_id": self.model_id,
            "thresholds_id": self.thresholds_id,
            "proof_semantics_id": self.proof_semantics_id,
            "source_occurrence_id": self.source_occurrence_id,
            "warm_occurrence_ids": list(self.warm_occurrence_ids),
            "occurrence_order": list(self.occurrence_order),
            "source_lower_entry_count": self.source_lower_entry_count,
            "warm_request_count": self.warm_request_count,
            "warm_resolution_count": self.warm_resolution_count,
            "fresh_process_required": self.fresh_process_required,
            "canonical_json_only": self.canonical_json_only,
            "roots_persisted": self.roots_persisted,
            "same_query_only": self.same_query_only,
            "live_source_sha256": self.live_source_sha256,
            "temporal_source_sha256": self.temporal_source_sha256,
            "planner_source_sha256": self.planner_source_sha256,
            "audit_source_sha256": self.audit_source_sha256,
            "multistep_source_sha256": self.multistep_source_sha256,
            "transport_source_sha256": self.transport_source_sha256,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("protocol", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


def _parse_live_node_key(document: Any) -> live.LiveEpochProofNodeKeyV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema",
            "schema_version",
            "profile_key",
            "slot",
            "semantics_id",
            "model_slice_content_id",
            "time_index",
            "stage_assignment_id",
            "ordered_parent_entry_ids",
            "identity_terms",
            "node_key_id",
        },
        "live node key",
    )
    if (
        record["schema"] != "acfqp.live_epoch_proof_node_key.v1"
        or record["schema_version"] != live.SCHEMA_VERSION
        or record["profile_key"] != live.PROFILE_KEY
        or type(record["ordered_parent_entry_ids"]) is not list
        or type(record["identity_terms"]) is not list
    ):
        raise DurableH2InvariantViolation("live node-key schema changed")
    terms: list[tuple[str, str]] = []
    for item in record["identity_terms"]:
        term = _exact_mapping(item, {"name", "value"}, "live node identity term")
        if type(term["name"]) is not str or type(term["value"]) is not str:
            raise DurableH2InvariantViolation("live node identity term is not textual")
        terms.append((term["name"], term["value"]))
    try:
        result = live.LiveEpochProofNodeKeyV1(
            temporal.H2TemporalProofSlot(record["slot"]),
            record["semantics_id"],
            record["model_slice_content_id"],
            record["time_index"],
            record["stage_assignment_id"],
            tuple(record["ordered_parent_entry_ids"]),
            tuple(terms),
        )
    except (ValueError, TypeError) as error:
        raise DurableH2InvariantViolation("live node key failed reconstruction") from error
    if result.to_document() != record:
        raise DurableH2InvariantViolation("live node key is not canonical")
    return result


def _parse_live_entry(document: Any) -> live.LiveEpochProofNodeEntryV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema",
            "schema_version",
            "profile_key",
            "key",
            "result_digest",
            "result_semantics",
            "entry_id",
        },
        "live proof entry",
    )
    if (
        record["schema"] != "acfqp.live_epoch_proof_entry.v1"
        or record["schema_version"] != live.SCHEMA_VERSION
        or record["profile_key"] != live.PROFILE_KEY
    ):
        raise DurableH2InvariantViolation("live proof-entry schema changed")
    result = live.LiveEpochProofNodeEntryV1(
        _parse_live_node_key(record["key"]),
        record["result_digest"],
        record["result_semantics"],
    )
    if result.to_document() != record:
        raise DurableH2InvariantViolation("live proof entry is not canonical")
    return result


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _parse_bound_map(
    rows: Any,
    key_name: str,
    value_name: str,
    name: str,
) -> dict[str, Fraction]:
    if type(rows) is not list:
        raise DurableH2InvariantViolation(f"{name} must be a list")
    result: dict[str, Fraction] = {}
    for item in rows:
        record = _exact_mapping(item, {key_name, value_name}, name)
        key = record[key_name]
        if type(key) is not str or key in result:
            raise DurableH2InvariantViolation(f"{name} keys are invalid")
        result[key] = _fraction(record[value_name], f"{name} value")
    if list(result) != sorted(result):
        raise DurableH2InvariantViolation(f"{name} is not canonically sorted")
    return result


def _parse_temporal_value(
    slot: temporal.H2TemporalProofSlot,
    document: Any,
) -> Any:
    record = _normalize_document(document)
    try:
        if slot in (temporal.H2TemporalProofSlot.U1, temporal.H2TemporalProofSlot.U0):
            value = _exact_mapping(
                record, {"time_index", "cell_upper", "state_upper", "rows"}, "U value"
            )
            rows = []
            if type(value["rows"]) is not list:
                raise DurableH2InvariantViolation("U rows are not a list")
            for item in value["rows"]:
                row = _exact_mapping(
                    item,
                    {
                        "time_index", "remaining_horizon", "state_id", "cell_id",
                        "ground_row_id", "ground_action_id", "reward_upper",
                    },
                    "U row",
                )
                rows.append(
                    temporal._URow(
                        _integer(row["time_index"], "U row time"),
                        _integer(row["remaining_horizon"], "U remaining", 1),
                        row["state_id"],
                        row["cell_id"],
                        row["ground_row_id"],
                        row["ground_action_id"],
                        _fraction(row["reward_upper"], "U reward"),
                    )
                )
            result = temporal._UStage(
                _integer(value["time_index"], "U time"),
                _parse_bound_map(value["cell_upper"], "cell_id", "reward_upper", "U cell"),
                _parse_bound_map(value["state_upper"], "state_id", "reward_upper", "U state"),
                tuple(rows),
            )
        elif slot in (temporal.H2TemporalProofSlot.P1, temporal.H2TemporalProofSlot.P0):
            value = _exact_mapping(record, {"time_index", "rows"}, "P value")
            if type(value["rows"]) is not list:
                raise DurableH2InvariantViolation("P rows are not a list")
            rows = []
            table: dict[str, Any] = {}
            for item in value["rows"]:
                row = _exact_mapping(
                    item,
                    {
                        "time_index", "remaining_horizon", "cell_id", "action_id",
                        "representative_state_ids", "missing_ground_row_ids",
                        "reward_lower", "reward_upper", "failure_lower", "failure_upper",
                        "max_shared_unknown_mass", "external_boundary_possible",
                        "representative_disagreement",
                    },
                    "P row",
                )
                parsed = temporal._PRow(
                    _integer(row["time_index"], "P row time"),
                    _integer(row["remaining_horizon"], "P remaining", 1),
                    row["cell_id"],
                    row["action_id"],
                    tuple(row["representative_state_ids"]),
                    tuple(row["missing_ground_row_ids"]),
                    _fraction(row["reward_lower"], "P reward lower"),
                    _fraction(row["reward_upper"], "P reward upper"),
                    _fraction(row["failure_lower"], "P failure lower"),
                    _fraction(row["failure_upper"], "P failure upper"),
                    _fraction(row["max_shared_unknown_mass"], "P unknown"),
                    row["external_boundary_possible"],
                    row["representative_disagreement"],
                )
                rows.append(parsed)
                if parsed.cell_id in table:
                    raise DurableH2InvariantViolation("P table has duplicate cells")
                table[parsed.cell_id] = audit._Bound(
                    parsed.reward_lower,
                    parsed.reward_upper,
                    parsed.failure_lower,
                    parsed.failure_upper,
                )
            result = temporal._PStage(
                _integer(value["time_index"], "P time"), table, tuple(rows)
            )
        elif slot in (temporal.H2TemporalProofSlot.C0, temporal.H2TemporalProofSlot.C1):
            value = _exact_mapping(
                record, {"time_index", "next_reach", "rows", "reachable_pairs"}, "C value"
            )
            next_reach = _parse_bound_map(
                value["next_reach"], "cell_id", "mass_upper", "C reach"
            )
            if type(value["rows"]) is not list or type(value["reachable_pairs"]) is not list:
                raise DurableH2InvariantViolation("C rows/pairs are not lists")
            rows = []
            for item in value["rows"]:
                row = _exact_mapping(
                    item,
                    {
                        "time_index", "remaining_horizon", "state_id", "cell_id",
                        "action_id", "support_ground_row_ids", "observed_ground_row_ids",
                        "missing_ground_row_ids", "reachable_cell_mass_upper",
                        "shared_unknown_mass", "known_external_successor_mass",
                        "reachable_unknown_mass_upper",
                        "reachable_external_continuation_mass_upper",
                        "representative_disagreement", "realization_singleton",
                    },
                    "C row",
                )
                rows.append(
                    temporal._CRow(
                        _integer(row["time_index"], "C row time"),
                        _integer(row["remaining_horizon"], "C remaining", 1),
                        row["state_id"],
                        row["cell_id"],
                        row["action_id"],
                        tuple(row["support_ground_row_ids"]),
                        tuple(row["observed_ground_row_ids"]),
                        tuple(row["missing_ground_row_ids"]),
                        _fraction(row["reachable_cell_mass_upper"], "C reach"),
                        _fraction(row["shared_unknown_mass"], "C unknown"),
                        _fraction(row["known_external_successor_mass"], "C external"),
                        _fraction(row["reachable_unknown_mass_upper"], "C unknown reach"),
                        _fraction(
                            row["reachable_external_continuation_mass_upper"],
                            "C external reach",
                        ),
                        row["representative_disagreement"],
                        row["realization_singleton"],
                    )
                )
            pairs = []
            for item in value["reachable_pairs"]:
                pair = _exact_mapping(item, {"time_index", "cell_id"}, "C reachable pair")
                pairs.append((_integer(pair["time_index"], "C pair time"), pair["cell_id"]))
            result = temporal._CStage(
                _integer(value["time_index"], "C time"),
                next_reach,
                tuple(rows),
                tuple(pairs),
            )
        elif slot is temporal.H2TemporalProofSlot.D:
            value = _exact_mapping(
                record,
                {
                    "unrestricted_upper", "root_reward_lower", "root_reward_upper",
                    "root_failure_lower", "root_failure_upper",
                    "raw_distribution_regret", "normalized_distribution_regret",
                    "reachable_state_time_cell_count", "support_metrics",
                },
                "D value",
            )
            if type(value["support_metrics"]) is not list:
                raise DurableH2InvariantViolation("D support metrics are not a list")
            metrics = []
            for item in value["support_metrics"]:
                metric = _exact_mapping(
                    item,
                    {
                        "state_id", "cell_id", "probability", "unrestricted_upper",
                        "policy_lower", "raw_regret", "normalized_regret",
                    },
                    "D support metric",
                )
                metrics.append(
                    (
                        metric["state_id"],
                        metric["cell_id"],
                        _fraction(metric["probability"], "D probability"),
                        _fraction(metric["unrestricted_upper"], "D unrestricted"),
                        _fraction(metric["policy_lower"], "D policy"),
                        _fraction(metric["raw_regret"], "D raw regret"),
                        _fraction(metric["normalized_regret"], "D normalized regret"),
                    )
                )
            result = temporal._NeutralD(
                {},
                _fraction(value["unrestricted_upper"], "D unrestricted"),
                _fraction(value["root_reward_lower"], "D reward lower"),
                _fraction(value["root_reward_upper"], "D reward upper"),
                _fraction(value["root_failure_lower"], "D failure lower"),
                _fraction(value["root_failure_upper"], "D failure upper"),
                _fraction(value["raw_distribution_regret"], "D raw regret"),
                _fraction(value["normalized_distribution_regret"], "D normalized regret"),
                _integer(value["reachable_state_time_cell_count"], "D reachable"),
                tuple(metrics),
            )
        elif slot is temporal.H2TemporalProofSlot.E:
            value = _exact_mapping(
                record, {"support_certified", "reward_certified"}, "E value"
            )
            result = temporal._NeutralE(
                tuple(value["support_certified"]), value["reward_certified"]
            )
        elif slot is temporal.H2TemporalProofSlot.F:
            value = _exact_mapping(record, {"risk_certified"}, "F value")
            result = temporal._NeutralF(value["risk_certified"])
        elif slot is temporal.H2TemporalProofSlot.G:
            value = _exact_mapping(
                record, {"external_row_indices", "coverage_certified"}, "G value"
            )
            result = temporal._NeutralG(
                tuple(value["external_row_indices"]), value["coverage_certified"]
            )
        else:
            raise DurableH2InvariantViolation("durable values may not contain R")
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, DurableH2InvariantViolation):
            raise
        raise DurableH2InvariantViolation("durable temporal value failed reconstruction") from error
    if temporal._value_document(slot, result) != record:
        raise DurableH2InvariantViolation("durable temporal value is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class DurableH2ProofValueV1:
    node_key_id: str
    entry: live.LiveEpochProofNodeEntryV1
    slot: temporal.H2TemporalProofSlot
    value_document: Mapping[str, Any]

    def __post_init__(self) -> None:
        _cid(self.node_key_id, "durable value node key")
        if (
            type(self.entry) is not live.LiveEpochProofNodeEntryV1
            or type(self.slot) is not temporal.H2TemporalProofSlot
            or self.slot is temporal.H2TemporalProofSlot.R
            or self.node_key_id != self.entry.key.node_key_id
            or self.slot is not self.entry.key.slot
            or type(self.value_document) is not dict
        ):
            raise DurableH2InvariantViolation("durable proof value binding changed")
        value = _parse_temporal_value(self.slot, dict(self.value_document))
        canonical = temporal._value_document(self.slot, value)
        if (
            canonical != dict(self.value_document)
            or live._node_result_digest(self.slot, value) != self.entry.result_digest
            or live._result_semantics(self.slot) != self.entry.result_semantics
        ):
            raise DurableH2InvariantViolation("durable proof value digest/semantics changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_proof_value.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "node_key_id": self.node_key_id,
            "entry": self.entry.to_document(),
            "slot": self.slot.value,
            "value_document": dict(self.value_document),
        }

    @property
    def value_id(self) -> str:
        return _content_id("value", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "value_id": self.value_id}

    @classmethod
    def from_document(cls, document: Any) -> "DurableH2ProofValueV1":
        record = _exact_mapping(
            _normalize_document(document),
            {
                "schema", "schema_version", "profile_key", "node_key_id",
                "entry", "slot", "value_document", "value_id",
            },
            "durable proof value",
        )
        if (
            record["schema"] != "acfqp.h2_durable_proof_value.v1"
            or record["schema_version"] != SCHEMA_VERSION
            or record["profile_key"] != PROFILE_KEY
        ):
            raise DurableH2InvariantViolation("durable proof-value schema changed")
        result = cls(
            record["node_key_id"],
            _parse_live_entry(record["entry"]),
            temporal.H2TemporalProofSlot(record["slot"]),
            record["value_document"],
        )
        if result.to_document() != record:
            raise DurableH2InvariantViolation("durable proof value is not canonical")
        return result


def _parse_live_request(document: Any) -> live.LiveEpochProofRequestV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema",
            "schema_version",
            "profile_key",
            "epoch",
            "request_index",
            "role",
            "schedule_code",
            "model_id",
            "thresholds_id",
            "contingent_plan",
            "stage_assignment_ids",
            "planner_result_id",
            "request_id",
        },
        "live proof request",
    )
    if (
        record["schema"] != "acfqp.live_epoch_proof_request.v1"
        or record["schema_version"] != live.SCHEMA_VERSION
        or record["profile_key"] != live.PROFILE_KEY
        or type(record["stage_assignment_ids"]) is not list
        or len(record["stage_assignment_ids"]) != 2
    ):
        raise DurableH2InvariantViolation("live proof request schema changed")
    planner_id = record["planner_result_id"]
    if type(planner_id) is dict:
        typed_null = _exact_mapping(
            planner_id, {"kind", "reason"}, "candidate planner typed null"
        )
        if typed_null != {
            "kind": "NOT_APPLICABLE",
            "reason": "CANDIDATE_PRECEDES_SELECTION",
        }:
            raise DurableH2InvariantViolation("candidate planner typed null changed")
        planner_id = None
    result = live.LiveEpochProofRequestV1(
        live.LiveEpochName(record["epoch"]),
        record["request_index"],
        temporal.H2TemporalProofRole(record["role"]),
        record["schedule_code"],
        record["model_id"],
        record["thresholds_id"],
        parse_frozen_contingent_abstract_plan_v1(record["contingent_plan"]),
        tuple(record["stage_assignment_ids"]),
        planner_id,
    )
    if result.to_document() != record:
        raise DurableH2InvariantViolation("live proof request is not canonical")
    return result


def _parse_live_resolution(document: Any) -> live.LiveEpochProofResolutionV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema",
            "schema_version",
            "profile_key",
            "sequence_number",
            "epoch",
            "request_id",
            "slot",
            "slice_binding_id",
            "node_key_id",
            "entry_id",
            "outcome",
            "pre_cache_state_id",
            "post_cache_state_id",
            "resolution_id",
        },
        "live proof resolution",
    )
    if (
        record["schema"] != "acfqp.live_epoch_proof_resolution.v1"
        or record["schema_version"] != live.SCHEMA_VERSION
        or record["profile_key"] != live.PROFILE_KEY
    ):
        raise DurableH2InvariantViolation("live proof resolution schema changed")
    try:
        result = live.LiveEpochProofResolutionV1(
            record["sequence_number"],
            live.LiveEpochName(record["epoch"]),
            record["request_id"],
            temporal.H2TemporalProofSlot(record["slot"]),
            record["slice_binding_id"],
            record["node_key_id"],
            record["entry_id"],
            live.LiveEpochResolutionOutcome(record["outcome"]),
            record["pre_cache_state_id"],
            record["post_cache_state_id"],
        )
    except (TypeError, ValueError) as error:
        raise DurableH2InvariantViolation(
            "live proof resolution failed reconstruction"
        ) from error
    if result.to_document() != record:
        raise DurableH2InvariantViolation("live proof resolution is not canonical")
    return result


def _parse_protocol(document: Any) -> DurableH2WorkloadProtocolV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema",
            "schema_version",
            "contract_version",
            "profile_key",
            "source_live_result_id",
            "model_id",
            "thresholds_id",
            "proof_semantics_id",
            "source_occurrence_id",
            "warm_occurrence_ids",
            "occurrence_order",
            "source_lower_entry_count",
            "warm_request_count",
            "warm_resolution_count",
            "fresh_process_required",
            "canonical_json_only",
            "roots_persisted",
            "same_query_only",
            "live_source_sha256",
            "temporal_source_sha256",
            "planner_source_sha256",
            "audit_source_sha256",
            "multistep_source_sha256",
            "transport_source_sha256",
            "protocol_id",
        },
        "durable workload protocol",
    )
    if (
        record["schema"] != "acfqp.h2_durable_workload_protocol.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["contract_version"] != CONTRACT_VERSION
        or record["profile_key"] != PROFILE_KEY
    ):
        raise DurableH2InvariantViolation("durable protocol schema changed")
    result = DurableH2WorkloadProtocolV1(
        record["source_live_result_id"],
        record["model_id"],
        record["thresholds_id"],
        record["proof_semantics_id"],
        record["source_occurrence_id"],
        tuple(record["warm_occurrence_ids"]),
        tuple(record["occurrence_order"]),
        record["source_lower_entry_count"],
        record["warm_request_count"],
        record["warm_resolution_count"],
        record["fresh_process_required"],
        record["canonical_json_only"],
        record["roots_persisted"],
        record["same_query_only"],
        record["live_source_sha256"],
        record["temporal_source_sha256"],
        record["planner_source_sha256"],
        record["audit_source_sha256"],
        record["multistep_source_sha256"],
        record["transport_source_sha256"],
    )
    if result.to_document() != record:
        raise DurableH2InvariantViolation("durable protocol is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class DurableH2LowerProofPayloadV1:
    protocol_id: str
    model_id: str
    thresholds_id: str
    values: tuple[DurableH2ProofValueV1, ...]
    entry_count: int = EXPECTED_SOURCE_LOWER_ENTRY_COUNT
    root_entry_count: int = 0

    def __post_init__(self) -> None:
        for value in (self.protocol_id, self.model_id, self.thresholds_id):
            _cid(value, "durable payload identity")
        if (
            type(self.values) is not tuple
            or any(type(item) is not DurableH2ProofValueV1 for item in self.values)
            or self.entry_count != 30
            or len(self.values) != self.entry_count
            or self.root_entry_count != 0
        ):
            raise DurableH2InvariantViolation("durable payload cardinality changed")
        expected = tuple(
            sorted(
                self.values,
                key=lambda item: (
                    live.LOWER_SLOT_ORDER.index(item.slot),
                    item.node_key_id,
                ),
            )
        )
        if self.values != expected:
            raise DurableH2InvariantViolation("durable payload order changed")
        if len({item.node_key_id for item in self.values}) != 30:
            raise DurableH2InvariantViolation("durable payload has duplicate node keys")
        entry_ids = {item.entry.entry_id for item in self.values}
        if len(entry_ids) != 30:
            raise DurableH2InvariantViolation("durable payload has duplicate entries")
        seen: set[str] = set()
        for item in self.values:
            if any(
                parent not in seen
                for parent in item.entry.key.ordered_parent_entry_ids
            ):
                raise DurableH2InvariantViolation(
                    "durable payload parent is absent or not topologically earlier"
                )
            seen.add(item.entry.entry_id)
        counts = {
            slot: sum(item.slot is slot for item in self.values)
            for slot in live.LOWER_SLOT_ORDER
        }
        expected_counts = {
            temporal.H2TemporalProofSlot.U1: 1,
            temporal.H2TemporalProofSlot.U0: 1,
            temporal.H2TemporalProofSlot.P1: 2,
            temporal.H2TemporalProofSlot.P0: 4,
            temporal.H2TemporalProofSlot.C0: 2,
            temporal.H2TemporalProofSlot.C1: 4,
            temporal.H2TemporalProofSlot.D: 4,
            temporal.H2TemporalProofSlot.E: 4,
            temporal.H2TemporalProofSlot.F: 4,
            temporal.H2TemporalProofSlot.G: 4,
        }
        if counts != expected_counts:
            raise DurableH2InvariantViolation("durable payload slot cardinalities changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_lower_proof_payload.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "model_id": self.model_id,
            "thresholds_id": self.thresholds_id,
            "values": [item.to_document() for item in self.values],
            "entry_count": self.entry_count,
            "root_entry_count": self.root_entry_count,
        }

    @property
    def payload_id(self) -> str:
        return _content_id("payload", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "payload_id": self.payload_id}

    @classmethod
    def from_document(cls, document: Any) -> "DurableH2LowerProofPayloadV1":
        record = _exact_mapping(
            _normalize_document(document),
            {
                "schema", "schema_version", "profile_key", "protocol_id",
                "model_id", "thresholds_id", "values", "entry_count",
                "root_entry_count", "payload_id",
            },
            "durable lower payload",
        )
        if (
            record["schema"] != "acfqp.h2_durable_lower_proof_payload.v1"
            or record["schema_version"] != SCHEMA_VERSION
            or record["profile_key"] != PROFILE_KEY
            or type(record["values"]) is not list
        ):
            raise DurableH2InvariantViolation("durable lower-payload schema changed")
        result = cls(
            record["protocol_id"],
            record["model_id"],
            record["thresholds_id"],
            tuple(DurableH2ProofValueV1.from_document(item) for item in record["values"]),
            record["entry_count"],
            record["root_entry_count"],
        )
        if result.to_document() != record:
            raise DurableH2InvariantViolation("durable lower payload is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class DurableH2ProofCheckpointManifestV1:
    protocol: DurableH2WorkloadProtocolV1
    payload_id: str
    payload_sha256: str
    payload_size_bytes: int
    final_model_document: Mapping[str, Any]
    thresholds_document: Mapping[str, Any]
    candidate_request_documents: tuple[Mapping[str, Any], ...]
    build_result_id: str
    threshold_rebase_id: str
    evidence_request_id: str
    evidence_bundle_id: str
    source_candidate_inner_audit_ids: tuple[str, ...]
    source_proposal_id: str
    source_selected_plan_id: str
    source_selected_request_id: str
    source_selected_receipt_id: str
    source_selected_inner_audit_id: str
    source_selected_wrapper_audit_id: str
    source_final_execution_id: str
    canonical_schedule_order: tuple[str, ...] = live.GRAY_CODES
    checkpoint_lower_entry_count: int = 30
    checkpoint_root_entry_count: int = 0

    def __post_init__(self) -> None:
        if type(self.protocol) is not DurableH2WorkloadProtocolV1:
            raise DurableH2InvariantViolation("manifest rejects substituted protocol")
        for value in (
            self.payload_id,
            self.payload_sha256,
            self.build_result_id,
            self.threshold_rebase_id,
            self.evidence_request_id,
            self.evidence_bundle_id,
            *self.source_candidate_inner_audit_ids,
            self.source_proposal_id,
            self.source_selected_plan_id,
            self.source_selected_request_id,
            self.source_selected_receipt_id,
            self.source_selected_inner_audit_id,
            self.source_selected_wrapper_audit_id,
            self.source_final_execution_id,
        ):
            _cid(value, "durable manifest identity")
        _integer(self.payload_size_bytes, "durable payload size", 1)
        if (
            type(self.final_model_document) is not dict
            or type(self.thresholds_document) is not dict
            or type(self.candidate_request_documents) is not tuple
            or len(self.candidate_request_documents) != 4
            or type(self.source_candidate_inner_audit_ids) is not tuple
            or len(self.source_candidate_inner_audit_ids) != 4
            or self.canonical_schedule_order != live.GRAY_CODES
            or self.checkpoint_lower_entry_count != 30
            or self.checkpoint_root_entry_count != 0
        ):
            raise DurableH2InvariantViolation("durable manifest shape changed")
        model = parse_query_scoped_partial_rapm_v3(dict(self.final_model_document))
        thresholds = parse_frozen_partial_audit_thresholds_v1(
            dict(self.thresholds_document)
        )
        requests = tuple(
            _parse_live_request(item) for item in self.candidate_request_documents
        )
        if (
            model.model_id != live.EXPECTED_FINAL_MODEL_ID
            or model.overlay_version != 2
            or len(model.coverage.observed_ground_row_ids) != 20
            or len(model.coverage.missing_ground_row_ids) != 0
            or model.model_id != self.protocol.model_id
            or thresholds.partial_model_id != model.model_id
            or thresholds.thresholds_id != self.protocol.thresholds_id
            or thresholds.thresholds_id != EXPECTED_FINAL_THRESHOLDS_ID
            or tuple(item.schedule_code for item in requests) != live.GRAY_CODES
            or tuple(item.request_index for item in requests) != (1, 2, 3, 4)
            or tuple(item.request_id for item in requests)
            != EXPECTED_FINAL_CANDIDATE_REQUEST_IDS
            or any(
                item.role
                is not temporal.H2TemporalProofRole.CANDIDATE_RANKING_AUDIT
                for item in requests
            )
            or tuple(item.to_document() for item in requests)
            != tuple(
                item.to_document()
                for item in _canonical_candidate_requests(model, thresholds)
            )
            or self.build_result_id != EXPECTED_FINAL_BUILD_RESULT_ID
            or self.threshold_rebase_id != EXPECTED_FINAL_THRESHOLD_REBASE_ID
            or self.evidence_request_id != EXPECTED_FINAL_EVIDENCE_REQUEST_ID
            or self.evidence_bundle_id != EXPECTED_FINAL_EVIDENCE_BUNDLE_ID
            or self.source_candidate_inner_audit_ids
            != EXPECTED_FINAL_CANDIDATE_INNER_AUDIT_IDS
            or self.source_proposal_id != EXPECTED_FINAL_PROPOSAL_ID
            or self.source_selected_plan_id != EXPECTED_FINAL_PLAN_ID
            or self.source_selected_request_id != EXPECTED_FINAL_SELECTED_REQUEST_ID
            or self.source_selected_receipt_id != EXPECTED_FINAL_SELECTED_RECEIPT_ID
            or self.source_selected_inner_audit_id
            != EXPECTED_FINAL_SELECTED_INNER_AUDIT_ID
            or self.source_selected_wrapper_audit_id
            != EXPECTED_FINAL_SELECTED_WRAPPER_AUDIT_ID
            or self.source_selected_wrapper_audit_id != live.EXPECTED_FINAL_AUDIT_ID
            or self.source_final_execution_id != EXPECTED_FINAL_EXECUTION_ID
            or self.source_final_execution_id
            != live.EXPECTED_FINAL_LIVE_EXECUTION_ID
        ):
            raise DurableH2InvariantViolation("durable manifest source scope changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_proof_checkpoint_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol": self.protocol.to_document(),
            "payload_id": self.payload_id,
            "payload_sha256": self.payload_sha256,
            "payload_size_bytes": self.payload_size_bytes,
            "final_model_document": dict(self.final_model_document),
            "thresholds_document": dict(self.thresholds_document),
            "candidate_request_documents": [
                dict(item) for item in self.candidate_request_documents
            ],
            "build_result_id": self.build_result_id,
            "threshold_rebase_id": self.threshold_rebase_id,
            "evidence_request_id": self.evidence_request_id,
            "evidence_bundle_id": self.evidence_bundle_id,
            "source_candidate_inner_audit_ids": list(
                self.source_candidate_inner_audit_ids
            ),
            "source_proposal_id": self.source_proposal_id,
            "source_selected_plan_id": self.source_selected_plan_id,
            "source_selected_request_id": self.source_selected_request_id,
            "source_selected_receipt_id": self.source_selected_receipt_id,
            "source_selected_inner_audit_id": self.source_selected_inner_audit_id,
            "source_selected_wrapper_audit_id": (
                self.source_selected_wrapper_audit_id
            ),
            "source_final_execution_id": self.source_final_execution_id,
            "canonical_schedule_order": list(self.canonical_schedule_order),
            "checkpoint_lower_entry_count": self.checkpoint_lower_entry_count,
            "checkpoint_root_entry_count": self.checkpoint_root_entry_count,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}

    @classmethod
    def from_document(cls, document: Any) -> "DurableH2ProofCheckpointManifestV1":
        record = _exact_mapping(
            _normalize_document(document),
            {
                "schema", "schema_version", "profile_key", "protocol",
                "payload_id", "payload_sha256", "payload_size_bytes",
                "final_model_document", "thresholds_document",
                "candidate_request_documents",
                "build_result_id", "threshold_rebase_id", "evidence_request_id",
                "evidence_bundle_id", "source_candidate_inner_audit_ids",
                "source_proposal_id", "source_selected_plan_id",
                "source_selected_request_id", "source_selected_receipt_id",
                "source_selected_inner_audit_id",
                "source_selected_wrapper_audit_id",
                "source_final_execution_id", "canonical_schedule_order",
                "checkpoint_lower_entry_count", "checkpoint_root_entry_count",
                "manifest_id",
            },
            "durable checkpoint manifest",
        )
        if (
            record["schema"] != "acfqp.h2_durable_proof_checkpoint_manifest.v1"
            or record["schema_version"] != SCHEMA_VERSION
            or record["profile_key"] != PROFILE_KEY
        ):
            raise DurableH2InvariantViolation("durable manifest schema changed")
        result = cls(
            _parse_protocol(record["protocol"]),
            record["payload_id"],
            record["payload_sha256"],
            record["payload_size_bytes"],
            record["final_model_document"],
            record["thresholds_document"],
            tuple(record["candidate_request_documents"]),
            record["build_result_id"],
            record["threshold_rebase_id"],
            record["evidence_request_id"],
            record["evidence_bundle_id"],
            tuple(record["source_candidate_inner_audit_ids"]),
            record["source_proposal_id"],
            record["source_selected_plan_id"],
            record["source_selected_request_id"],
            record["source_selected_receipt_id"],
            record["source_selected_inner_audit_id"],
            record["source_selected_wrapper_audit_id"],
            record["source_final_execution_id"],
            tuple(record["canonical_schedule_order"]),
            record["checkpoint_lower_entry_count"],
            record["checkpoint_root_entry_count"],
        )
        if result.to_document() != record:
            raise DurableH2InvariantViolation("durable manifest is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class DurableH2StateCommitV1:
    protocol_id: str
    payload_id: str
    payload_sha256: str
    payload_size_bytes: int
    manifest_id: str
    manifest_sha256: str
    manifest_size_bytes: int
    generation: int = 1
    previous_commit_id: str | None = None
    commit_complete: bool = True

    def __post_init__(self) -> None:
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
        if (
            self.generation != 1
            or self.previous_commit_id is not None
            or self.commit_complete is not True
        ):
            raise DurableH2InvariantViolation("initial durable commit chain changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_state_commit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "payload_id": self.payload_id,
            "payload_sha256": self.payload_sha256,
            "payload_size_bytes": self.payload_size_bytes,
            "manifest_id": self.manifest_id,
            "manifest_sha256": self.manifest_sha256,
            "manifest_size_bytes": self.manifest_size_bytes,
            "generation": self.generation,
            "previous_commit_id": {
                "kind": "NOT_APPLICABLE",
                "reason": "INITIAL_COMMIT",
            },
            "commit_complete": self.commit_complete,
        }

    @property
    def commit_id(self) -> str:
        return _content_id("commit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commit_id": self.commit_id}

    @classmethod
    def from_document(cls, document: Any) -> "DurableH2StateCommitV1":
        record = _exact_mapping(
            _normalize_document(document),
            {
                "schema", "schema_version", "profile_key", "protocol_id",
                "payload_id", "payload_sha256", "payload_size_bytes",
                "manifest_id", "manifest_sha256", "manifest_size_bytes",
                "generation", "previous_commit_id", "commit_complete", "commit_id",
            },
            "durable state commit",
        )
        if (
            record["schema"] != "acfqp.h2_durable_state_commit.v1"
            or record["schema_version"] != SCHEMA_VERSION
            or record["profile_key"] != PROFILE_KEY
            or record["previous_commit_id"]
            != {"kind": "NOT_APPLICABLE", "reason": "INITIAL_COMMIT"}
        ):
            raise DurableH2InvariantViolation("durable commit schema changed")
        result = cls(
            record["protocol_id"],
            record["payload_id"],
            record["payload_sha256"],
            record["payload_size_bytes"],
            record["manifest_id"],
            record["manifest_sha256"],
            record["manifest_size_bytes"],
            record["generation"],
            None,
            record["commit_complete"],
        )
        if result.to_document() != record:
            raise DurableH2InvariantViolation("durable commit is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class VerifiedDurableH2LeaseV1:
    expected_commit_id: str
    commit: DurableH2StateCommitV1
    manifest: DurableH2ProofCheckpointManifestV1
    payload: DurableH2LowerProofPayloadV1
    model: Any
    thresholds: Any
    candidate_requests: tuple[live.LiveEpochProofRequestV1, ...]
    semantic_replay_computes: int
    semantic_replay_hits: int
    canonical_bytes_retained: bool = True
    kernel_transition_calls: int = 0
    action_catalogue_calls: int = 0
    ground_optimizer_calls: int = 0
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _cid(self.expected_commit_id, "verified durable lease commit")
        if (
            type(self.commit) is not DurableH2StateCommitV1
            or type(self.manifest) is not DurableH2ProofCheckpointManifestV1
            or type(self.payload) is not DurableH2LowerProofPayloadV1
            or self.expected_commit_id != self.commit.commit_id
            or self.manifest.manifest_id != self.commit.manifest_id
            or self.payload.payload_id != self.commit.payload_id
            or self.payload.protocol_id != self.manifest.protocol.protocol_id
            or self.model.model_id != self.manifest.protocol.model_id
            or self.thresholds.thresholds_id != self.manifest.protocol.thresholds_id
            or len(self.candidate_requests) != 4
            or self.semantic_replay_computes != 34
            or self.semantic_replay_hits != 10
            or self.canonical_bytes_retained is not True
            or self.kernel_transition_calls != 0
            or self.action_catalogue_calls != 0
            or self.ground_optimizer_calls != 0
        ):
            raise DurableH2InvariantViolation("verified durable lease changed")


def require_verified_durable_h2_lease_v1(
    lease: VerifiedDurableH2LeaseV1,
) -> VerifiedDurableH2LeaseV1:
    if type(lease) is not VerifiedDurableH2LeaseV1:
        raise DurableH2InvariantViolation("durable loader rejects substituted leases")
    try:
        require_runtime_authority_v1(lease, issuer=_LEASE_ISSUER)
    except ValueError as error:
        raise DurableH2InvariantViolation("durable lease lacks live reader authority") from error
    return lease


@dataclass(frozen=True, slots=True)
class _BuildView:
    model: Any
    result_id: str


@dataclass(frozen=True, slots=True)
class _RebaseView:
    rebased_thresholds: Any
    rebase_id: str


@dataclass(frozen=True, slots=True)
class _EvidenceRequestView:
    request_id: str


@dataclass(frozen=True, slots=True)
class _EvidenceBundleView:
    bundle_id: str


def _stage_maps(
    requests: tuple[live.LiveEpochProofRequestV1, ...],
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for request in requests:
        stages = tuple(sorted(request.contingent_plan.stages, key=lambda item: item.time_index))
        if len(stages) != 2:
            raise DurableH2InvariantViolation("durable H2 request stage count changed")
        for stage_id, stage in zip(request.stage_assignment_ids, stages):
            mapping = {
                item.cell_id: item.semantic_action_id for item in stage.assignments
            }
            if stage_id in result and result[stage_id] != mapping:
                raise DurableH2InvariantViolation(
                    "stage assignment ID maps to inconsistent actions"
                )
            result[stage_id] = mapping
    return result


def _canonical_candidate_requests(
    model: Any,
    thresholds: Any,
) -> tuple[live.LiveEpochProofRequestV1, ...]:
    """Derive the registered four-request workload from model semantics alone."""

    active_cells = tuple(
        sorted(
            (
                item
                for item in model.cells
                if item.planning_kind is audit.PlanningKind.ACTIVE
            ),
            key=lambda item: item.cell_id,
        )
    )
    actions_by_cell: dict[str, list[str]] = {
        item.cell_id: [] for item in active_cells
    }
    for action in model.semantic_actions:
        if action.cell_id in actions_by_cell:
            actions_by_cell[action.cell_id].append(action.semantic_action_id)
    domains = tuple(
        planner.PartialPlannerCellActionDomainV1(
            cell.cell_id,
            tuple(sorted(actions_by_cell[cell.cell_id])),
        )
        for cell in active_cells
    )
    assignments = tuple(
        sorted(
            planner._stage_assignments(domains),
            key=lambda item: (
                live._semantic_stage_key(model, item),
                tuple(row.semantic_action_id for row in item),
            ),
        )
    )
    if len(assignments) != 2:
        raise DurableH2InvariantViolation(
            "registered durable model must expose exactly two stage assignments"
        )
    stage_artifacts = tuple(
        temporal.H2TemporalStageAssignmentV1(
            index,
            tuple(
                (
                    row.cell_id,
                    row.semantic_action_id,
                    tuple(
                        int(value)
                        for value in next(
                            action.label_values
                            for action in model.semantic_actions
                            if action.semantic_action_id == row.semantic_action_id
                        )
                    ),
                )
                for row in stage
            ),
        )
        for index, stage in enumerate(assignments)
    )
    requests: list[live.LiveEpochProofRequestV1] = []
    for request_index, (code, bits) in enumerate(
        zip(live.GRAY_CODES, live.GRAY_BITS),
        start=1,
    ):
        plan = FrozenContingentAbstractPlanV1(
            model.model_id,
            2,
            tuple(
                audit.ContingentPlanStageV1(time_index, assignments[bit])
                for time_index, bit in enumerate(bits)
            ),
        )
        requests.append(
            live.LiveEpochProofRequestV1(
                live.LiveEpochName.FINAL,
                request_index,
                temporal.H2TemporalProofRole.CANDIDATE_RANKING_AUDIT,
                code,
                model.model_id,
                thresholds.thresholds_id,
                plan,
                tuple(stage_artifacts[bit].stage_assignment_id for bit in bits),
                None,
            )
        )
    return tuple(requests)


def _reconstruct_source_runtime(
    source: live.LiveQueryLocalEpochInvalidationResultV1,
) -> tuple[live._Runtime, live.LiveEpochProofExecutionV1]:
    live.require_live_query_local_epoch_invalidation_result_v1(source)
    execution = source.global_cross_epoch_facet_arm.final_epoch
    source_chain = source.live_multistep_result
    requests = tuple(item.request for item in execution.request_receipts)
    runtime = live._Runtime(
        live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG,
        source.semantics,
    )
    maps = _stage_maps(requests)
    for expected in execution.request_receipts:
        rebuilt = live._run_request(
            runtime,
            live.LiveEpochName.FINAL,
            expected.request,
            source_chain.final_overlay_build,
            source_chain.final_threshold_rebase,
            source_chain.round_two_request,
            source_chain.round_two_bundle,
            maps,
        )
        # This is a fresh final-epoch reconstruction.  The authoritative
        # V0-053 receipt was produced after the first epoch and therefore has
        # different resolution sequence/cache-state provenance even when the
        # semantic request, root and audit are identical.
        if (
            rebuilt.request.to_document() != expected.request.to_document()
            or rebuilt.audit_result.to_document() != expected.audit_result.to_document()
            or rebuilt.root_entry_id != expected.root_entry_id
        ):
            raise DurableH2InvariantViolation(
                "checkpoint source recomputation differs from V0-053 final root"
            )
    lower_entries = tuple(
        entry
        for entry in runtime.entries.values()
        if entry.key.slot is not temporal.H2TemporalProofSlot.R
    )
    if (
        len(lower_entries) != 30
        or runtime.resolutions[-1].sequence_number != 55
        or sum(
            item.outcome is live.LiveEpochResolutionOutcome.COMPUTED
            for item in runtime.resolutions
        )
        != 35
        or sum(
            item.outcome is live.LiveEpochResolutionOutcome.REUSED
            for item in runtime.resolutions
        )
        != 20
    ):
        raise DurableH2InvariantViolation("source lower-DAG reconstruction counts changed")
    return runtime, execution


def _payload_from_runtime(
    runtime: live._Runtime,
    protocol: DurableH2WorkloadProtocolV1,
    model_id: str,
    thresholds_id: str,
) -> DurableH2LowerProofPayloadV1:
    values: list[DurableH2ProofValueV1] = []
    for node_key_id, entry_id in runtime.cache.items():
        entry = runtime.entries[entry_id]
        if entry.key.slot is temporal.H2TemporalProofSlot.R:
            continue
        value = runtime.live_values[node_key_id]
        values.append(
            DurableH2ProofValueV1(
                node_key_id,
                entry,
                entry.key.slot,
                temporal._value_document(entry.key.slot, value),
            )
        )
    return DurableH2LowerProofPayloadV1(
        protocol.protocol_id,
        model_id,
        thresholds_id,
        tuple(
            sorted(
                values,
                key=lambda item: (
                    live.LOWER_SLOT_ORDER.index(item.slot),
                    item.node_key_id,
                ),
            )
        ),
    )


def _recompute_expected_payload(
    protocol: DurableH2WorkloadProtocolV1,
    model: Any,
    thresholds: Any,
    candidate_requests: tuple[live.LiveEpochProofRequestV1, ...],
    build_result_id: str,
    threshold_rebase_id: str,
    evidence_request_id: str,
    evidence_bundle_id: str,
) -> tuple[DurableH2LowerProofPayloadV1, int, int, tuple[str, ...]]:
    """Recompute the complete expected lower graph before accepting a seed."""

    expected_requests = _canonical_candidate_requests(model, thresholds)
    if tuple(item.to_document() for item in candidate_requests) != tuple(
        item.to_document() for item in expected_requests
    ):
        raise DurableH2InvariantViolation(
            "checkpoint requests differ from canonical model-derived workload"
        )
    runtime = live._Runtime(
        live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG,
        live.live_epoch_proof_semantics_v1(),
    )
    build = _BuildView(model, build_result_id)
    rebase = _RebaseView(thresholds, threshold_rebase_id)
    evidence_request = _EvidenceRequestView(evidence_request_id)
    evidence_bundle = _EvidenceBundleView(evidence_bundle_id)
    maps = _stage_maps(candidate_requests)
    candidate_audit_ids: list[str] = []
    for request in candidate_requests:
        receipt = live._run_request(
            runtime,
            live.LiveEpochName.FINAL,
            request,
            build,
            rebase,
            evidence_request,
            evidence_bundle,
            maps,
        )
        candidate_audit_ids.append(receipt.audit_result.result_id)
    expected = _payload_from_runtime(
        runtime,
        protocol,
        model.model_id,
        thresholds.thresholds_id,
    )
    computes = sum(
        item.outcome is live.LiveEpochResolutionOutcome.COMPUTED
        for item in runtime.resolutions
    )
    hits = sum(
        item.outcome is live.LiveEpochResolutionOutcome.REUSED
        for item in runtime.resolutions
    )
    if len(runtime.resolutions) != 44 or (computes, hits) != (34, 10):
        raise DurableH2InvariantViolation(
            "checkpoint semantic replay counts changed"
        )
    frozen_candidate_audits = tuple(candidate_audit_ids)
    if frozen_candidate_audits != EXPECTED_FINAL_CANDIDATE_INNER_AUDIT_IDS:
        raise DurableH2InvariantViolation(
            "checkpoint candidate-audit identities changed"
        )
    return expected, computes, hits, frozen_candidate_audits


def _materialize_checkpoint(
    source: live.LiveQueryLocalEpochInvalidationResultV1,
) -> tuple[
    DurableH2WorkloadProtocolV1,
    DurableH2LowerProofPayloadV1,
    DurableH2ProofCheckpointManifestV1,
    bytes,
    bytes,
]:
    runtime, execution = _reconstruct_source_runtime(source)
    source_chain = source.live_multistep_result
    model = source_chain.final_overlay_build.model
    thresholds = source_chain.final_threshold_rebase.rebased_thresholds
    protocol = DurableH2WorkloadProtocolV1(
        source.result_id,
        model.model_id,
        thresholds.thresholds_id,
        source.semantics.semantics_id,
    )
    payload = _payload_from_runtime(
        runtime,
        protocol,
        model.model_id,
        thresholds.thresholds_id,
    )
    payload_bytes = canonical_json_bytes(payload.to_document())
    candidate_receipts = execution.request_receipts[:4]
    selected_receipt = execution.request_receipts[-1]
    manifest = DurableH2ProofCheckpointManifestV1(
        protocol,
        payload.payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        model.to_document(),
        thresholds.to_document(),
        tuple(item.request.to_document() for item in candidate_receipts),
        source_chain.final_overlay_build.result_id,
        source_chain.final_threshold_rebase.rebase_id,
        source_chain.round_two_request.request_id,
        source_chain.round_two_bundle.bundle_id,
        tuple(item.audit_result.result_id for item in candidate_receipts),
        execution.plan_proposal.result_id,
        execution.plan_proposal.selected_plan.plan_id,
        selected_receipt.request.request_id,
        selected_receipt.receipt_id,
        selected_receipt.audit_result.result_id,
        execution.selected_plan_audit.result_id,
        execution.execution_id,
    )
    manifest_bytes = canonical_json_bytes(manifest.to_document())
    return protocol, payload, manifest, payload_bytes, manifest_bytes


def _atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists() or path.exists():
        raise DurableH2InvariantViolation("durable store refuses overwrite")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(temporary, flags, 0o600)
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


def write_durable_h2_checkpoint_v1(
    source: live.LiveQueryLocalEpochInvalidationResultV1,
    store_root: Path,
) -> DurableH2StateCommitV1:
    """Materialize and atomically commit one canonical V0-054A checkpoint."""

    if not isinstance(store_root, Path):
        raise DurableH2InvariantViolation("durable store root must be a pathlib Path")
    if store_root.exists():
        if store_root.is_symlink() or not store_root.is_dir() or any(store_root.iterdir()):
            raise DurableH2InvariantViolation("durable writer requires an empty real directory")
    else:
        store_root.mkdir(parents=True)
    blobs = store_root / "blobs"
    commits = store_root / "commits"
    blobs.mkdir()
    commits.mkdir()
    protocol, payload, manifest, payload_bytes, manifest_bytes = _materialize_checkpoint(
        source
    )
    if (
        protocol.protocol_id != EXPECTED_DURABLE_PROTOCOL_ID
        or payload.payload_id != EXPECTED_DURABLE_PAYLOAD_ID
        or manifest.manifest_id != EXPECTED_DURABLE_MANIFEST_ID
    ):
        raise DurableH2InvariantViolation(
            "canonical durable checkpoint identities changed"
        )
    payload_path = blobs / f"{payload.payload_id}.json"
    manifest_path = blobs / f"{manifest.manifest_id}.json"
    _atomic_write(payload_path, payload_bytes)
    # The producer rereads and reconstructs the payload before publishing the
    # manifest.  Bytes are canonical and the typed graph is revalidated.
    payload_reread = payload_path.read_bytes()
    if (
        payload_reread != payload_bytes
        or DurableH2LowerProofPayloadV1.from_document(
            loads_canonical_json(payload_reread)
        ).to_document()
        != payload.to_document()
    ):
        raise DurableH2InvariantViolation("durable payload reread failed")
    _atomic_write(manifest_path, manifest_bytes)
    manifest_reread = manifest_path.read_bytes()
    if (
        manifest_reread != manifest_bytes
        or DurableH2ProofCheckpointManifestV1.from_document(
            loads_canonical_json(manifest_reread)
        ).to_document()
        != manifest.to_document()
    ):
        raise DurableH2InvariantViolation("durable manifest reread failed")
    commit = DurableH2StateCommitV1(
        protocol.protocol_id,
        payload.payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        manifest.manifest_id,
        hashlib.sha256(manifest_bytes).hexdigest(),
        len(manifest_bytes),
    )
    if commit.commit_id != EXPECTED_DURABLE_COMMIT_ID:
        raise DurableH2InvariantViolation("canonical durable commit identity changed")
    commit_path = commits / f"{commit.commit_id}.json"
    commit_bytes = canonical_json_bytes(commit.to_document())
    _atomic_write(commit_path, commit_bytes)
    if DurableH2StateCommitV1.from_document(
        loads_canonical_json(commit_path.read_bytes())
    ).to_document() != commit.to_document():
        raise DurableH2InvariantViolation("durable commit reread failed")
    return commit


def _read_stable_regular(path: Path) -> bytes:
    before = path.lstat()
    if (
        path.is_symlink()
        or not path.is_file()
        or before.st_nlink != 1
        or before.st_size <= 0
    ):
        raise DurableH2InvariantViolation("durable artifact is not a unique regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
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
    signature = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_nlink,
    )
    if (
        signature(before) != signature(opened)
        or signature(opened) != signature(after_open)
        or signature(after_open) != signature(after_path)
    ):
        raise DurableH2InvariantViolation("durable artifact changed during snapshot")
    return b"".join(chunks)


def _checkpoint_byte_snapshot_id(
    store_root: Path,
    commit: DurableH2StateCommitV1,
) -> str:
    artifacts = (
        ("payload", store_root / "blobs" / f"{commit.payload_id}.json"),
        ("manifest", store_root / "blobs" / f"{commit.manifest_id}.json"),
        ("commit", store_root / "commits" / f"{commit.commit_id}.json"),
    )
    rows = []
    for role, path in artifacts:
        data = _read_stable_regular(path)
        rows.append(
            {
                "role": role,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return _content_id(
        "snapshot",
        {
            "schema": "acfqp.h2_durable_proof_checkpoint_byte_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "commit_id": commit.commit_id,
            "artifacts": rows,
        },
    )


def load_verified_durable_h2_checkpoint_v1(
    store_root: Path,
    expected_commit_id: str,
) -> VerifiedDurableH2LeaseV1:
    """Strictly load a committed checkpoint using an external expected head."""

    if not isinstance(store_root, Path):
        raise DurableH2InvariantViolation("durable loader root must be a pathlib Path")
    expected = _cid(expected_commit_id, "externally expected commit")
    if (
        not store_root.exists()
        or store_root.is_symlink()
        or not store_root.is_dir()
        or {item.name for item in store_root.iterdir()}
        != {"blobs", "commits"}
    ):
        raise DurableH2InvariantViolation("durable store topology changed")
    blobs = store_root / "blobs"
    commits = store_root / "commits"
    if blobs.is_symlink() or commits.is_symlink() or not blobs.is_dir() or not commits.is_dir():
        raise DurableH2InvariantViolation("durable store directories are not real")
    expected_commit_name = f"{expected}.json"
    if {item.name for item in commits.iterdir()} != {expected_commit_name}:
        raise DurableH2InvariantViolation("durable commit directory is not exact")
    commit = DurableH2StateCommitV1.from_document(
        loads_canonical_json(_read_stable_regular(commits / expected_commit_name))
    )
    if (
        commit.commit_id != expected
        or commit.generation != 1
    ):
        raise DurableH2InvariantViolation("durable commit chain changed")
    expected_blob_names = {
        f"{commit.payload_id}.json",
        f"{commit.manifest_id}.json",
    }
    if {item.name for item in blobs.iterdir()} != expected_blob_names:
        raise DurableH2InvariantViolation("durable blob directory is not exact")
    payload_bytes = _read_stable_regular(blobs / f"{commit.payload_id}.json")
    manifest_bytes = _read_stable_regular(blobs / f"{commit.manifest_id}.json")
    if (
        len(payload_bytes) != commit.payload_size_bytes
        or hashlib.sha256(payload_bytes).hexdigest() != commit.payload_sha256
        or len(manifest_bytes) != commit.manifest_size_bytes
        or hashlib.sha256(manifest_bytes).hexdigest() != commit.manifest_sha256
    ):
        raise DurableH2InvariantViolation("durable blob size or SHA changed")
    payload = DurableH2LowerProofPayloadV1.from_document(
        loads_canonical_json(payload_bytes)
    )
    manifest = DurableH2ProofCheckpointManifestV1.from_document(
        loads_canonical_json(manifest_bytes)
    )
    if (
        payload.payload_id != commit.payload_id
        or manifest.manifest_id != commit.manifest_id
        or manifest.payload_id != payload.payload_id
        or manifest.payload_sha256 != commit.payload_sha256
        or manifest.payload_size_bytes != commit.payload_size_bytes
        or manifest.protocol.protocol_id != commit.protocol_id
        or payload.protocol_id != commit.protocol_id
        or manifest.protocol.live_source_sha256 != _source_sha(live)
        or manifest.protocol.temporal_source_sha256 != _source_sha(temporal)
        or manifest.protocol.planner_source_sha256 != _source_sha(planner)
        or manifest.protocol.audit_source_sha256 != _source_sha(audit)
        or manifest.protocol.multistep_source_sha256 != _source_sha(multistep)
        or manifest.protocol.transport_source_sha256
        != _source_sha(durable_transport)
    ):
        raise DurableH2InvariantViolation("durable checkpoint identity chain changed")
    model = parse_query_scoped_partial_rapm_v3(manifest.final_model_document)
    thresholds = parse_frozen_partial_audit_thresholds_v1(
        manifest.thresholds_document
    )
    candidates = tuple(
        _parse_live_request(item) for item in manifest.candidate_request_documents
    )
    (
        expected_payload,
        replay_computes,
        replay_hits,
        replay_candidate_audit_ids,
    ) = _recompute_expected_payload(
        manifest.protocol,
        model,
        thresholds,
        candidates,
        manifest.build_result_id,
        manifest.threshold_rebase_id,
        manifest.evidence_request_id,
        manifest.evidence_bundle_id,
    )
    if (
        expected_payload.to_document() != payload.to_document()
        or replay_candidate_audit_ids != manifest.source_candidate_inner_audit_ids
    ):
        raise DurableH2InvariantViolation(
            "durable lower payload differs from exact model-derived proof state"
        )
    if (
        manifest.protocol.protocol_id != EXPECTED_DURABLE_PROTOCOL_ID
        or payload.payload_id != EXPECTED_DURABLE_PAYLOAD_ID
        or manifest.manifest_id != EXPECTED_DURABLE_MANIFEST_ID
        or commit.commit_id != EXPECTED_DURABLE_COMMIT_ID
    ):
        raise DurableH2InvariantViolation(
            "verified durable checkpoint canonical identities changed"
        )
    lease = VerifiedDurableH2LeaseV1(
        expected,
        commit,
        manifest,
        payload,
        model,
        thresholds,
        candidates,
        replay_computes,
        replay_hits,
    )
    return bind_runtime_authority_v1(lease, issuer=_LEASE_ISSUER)


@dataclass(frozen=True, slots=True)
class DurableH2PlanProposalV1:
    occurrence_id: str
    commit_id: str
    model_id: str
    thresholds_id: str
    candidate_root_ids: tuple[str, ...]
    candidate_plan_ids: tuple[str, ...]
    selection_mode: str
    selected_plan_id: str
    selected_schedule_code: str
    selected_semantic_key: tuple[int, ...]
    candidate_count: int = 4
    tie_break_rule: str = "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"

    def __post_init__(self) -> None:
        for value in (
            self.occurrence_id,
            self.commit_id,
            self.model_id,
            self.thresholds_id,
            self.selected_plan_id,
            *self.candidate_root_ids,
            *self.candidate_plan_ids,
        ):
            _cid(value, "durable proposal identity")
        if (
            type(self.candidate_root_ids) is not tuple
            or type(self.candidate_plan_ids) is not tuple
            or len(self.candidate_root_ids) != 4
            or len(self.candidate_plan_ids) != 4
            or len(set(self.candidate_root_ids)) != 4
            or len(set(self.candidate_plan_ids)) != 4
            or self.selected_plan_id not in self.candidate_plan_ids
            or self.selected_plan_id != EXPECTED_FINAL_PLAN_ID
            or self.selected_schedule_code != "A0A0"
            or type(self.selected_semantic_key) is not tuple
            or any(type(item) is not int or item not in (0, 1) for item in self.selected_semantic_key)
            or self.selected_semantic_key != (0, 1, 0, 1, 0, 1, 0, 1)
            or self.candidate_count != 4
            or self.tie_break_rule
            != "NUMERIC_GATE_THEN_SEMANTIC_LABEL_LEXICOGRAPHIC_V1"
        ):
            raise DurableH2InvariantViolation("durable proposal changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_plan_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "commit_id": self.commit_id,
            "model_id": self.model_id,
            "thresholds_id": self.thresholds_id,
            "candidate_root_ids": list(self.candidate_root_ids),
            "candidate_plan_ids": list(self.candidate_plan_ids),
            "selection_mode": self.selection_mode,
            "selected_plan_id": self.selected_plan_id,
            "selected_schedule_code": self.selected_schedule_code,
            "selected_semantic_key": list(self.selected_semantic_key),
            "candidate_count": self.candidate_count,
            "tie_break_rule": self.tie_break_rule,
        }

    @property
    def proposal_id(self) -> str:
        return _content_id("proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}


@dataclass(frozen=True, slots=True)
class DurableH2OccurrenceRootV1:
    occurrence_id: str
    commit_id: str
    request_id: str
    request_index: int
    request_role: str
    schedule_code: str
    plan_id: str
    durable_proposal_id: str | None
    legacy_root_entry_id: str
    legacy_root_result_digest: str
    audit_result_id: str

    def __post_init__(self) -> None:
        for value in (
            self.occurrence_id,
            self.commit_id,
            self.request_id,
            self.plan_id,
            self.legacy_root_entry_id,
            self.legacy_root_result_digest,
            self.audit_result_id,
        ):
            _cid(value, "durable occurrence-root identity")
        _integer(self.request_index, "durable root request", 1)
        selected = self.request_index == 5
        if (
            self.request_index not in range(1, 6)
            or self.schedule_code not in live.GRAY_CODES
            or selected
            != (
                self.request_role
                == temporal.H2TemporalProofRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE.value
            )
            or selected != (self.durable_proposal_id is not None)
        ):
            raise DurableH2InvariantViolation("durable occurrence root role changed")
        if self.durable_proposal_id is not None:
            _cid(self.durable_proposal_id, "durable root proposal")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_occurrence_root.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "commit_id": self.commit_id,
            "request_id": self.request_id,
            "request_index": self.request_index,
            "request_role": self.request_role,
            "schedule_code": self.schedule_code,
            "plan_id": self.plan_id,
            "durable_proposal_id": (
                self.durable_proposal_id
                if self.durable_proposal_id is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "CANDIDATE_PRECEDES_SELECTION",
                }
            ),
            "legacy_root_entry_id": self.legacy_root_entry_id,
            "legacy_root_result_digest": self.legacy_root_result_digest,
            "audit_result_id": self.audit_result_id,
        }

    @property
    def root_id(self) -> str:
        return _content_id("root", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "root_id": self.root_id}


@dataclass(frozen=True, slots=True)
class DurableH2OccurrenceArmV1:
    occurrence_id: str
    commit_id: str
    kind: DurableH2ArmKind
    proposal: DurableH2PlanProposalV1
    roots: tuple[DurableH2OccurrenceRootV1, ...]
    selected_audit_result_id: str
    preloaded_entry_bindings: tuple[tuple[str, str], ...]
    resolution_documents: tuple[Mapping[str, Any], ...]
    computes: int
    hits: int
    lower_computes: int
    lower_hits: int
    root_computes: int
    root_hits: int
    preloaded_lower_entries: int
    request_count: int = 5
    resolution_count: int = 55
    kernel_transition_calls: int = 0
    action_catalogue_calls: int = 0
    ground_optimizer_calls: int = 0

    def __post_init__(self) -> None:
        for value in (
            self.occurrence_id,
            self.commit_id,
            self.selected_audit_result_id,
        ):
            _cid(value, "durable arm identity")
        if (
            type(self.preloaded_entry_bindings) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) is not str
                for item in self.preloaded_entry_bindings
            )
            or self.preloaded_entry_bindings
            != tuple(sorted(set(self.preloaded_entry_bindings)))
            or type(self.resolution_documents) is not tuple
            or len(self.resolution_documents) != 55
            or any(type(item) is not dict for item in self.resolution_documents)
        ):
            raise DurableH2InvariantViolation(
                "durable arm cache/resolution receipts changed"
            )
        for node_key_id, entry_id in self.preloaded_entry_bindings:
            _cid(node_key_id, "durable arm preloaded node")
            _cid(entry_id, "durable arm preloaded entry")
        resolutions = tuple(
            _parse_live_resolution(item) for item in self.resolution_documents
        )
        if (
            type(self.kind) is not DurableH2ArmKind
            or type(self.proposal) is not DurableH2PlanProposalV1
            or type(self.roots) is not tuple
            or len(self.roots) != 5
            or self.proposal.occurrence_id != self.occurrence_id
            or self.proposal.commit_id != self.commit_id
            or any(
                item.occurrence_id != self.occurrence_id
                or item.commit_id != self.commit_id
                for item in self.roots
            )
            or tuple(item.request_index for item in self.roots) != (1, 2, 3, 4, 5)
            or tuple(item.schedule_code for item in self.roots[:4])
            != live.GRAY_CODES
            or any(
                item.request_role
                != temporal.H2TemporalProofRole.CANDIDATE_RANKING_AUDIT.value
                or item.durable_proposal_id is not None
                for item in self.roots[:4]
            )
            or self.roots[-1].request_role
            != temporal.H2TemporalProofRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE.value
            or len({item.request_id for item in self.roots}) != 5
            or self.proposal.candidate_root_ids
            != tuple(item.root_id for item in self.roots[:4])
            or self.proposal.candidate_plan_ids
            != tuple(item.plan_id for item in self.roots[:4])
            or self.roots[-1].plan_id != self.proposal.selected_plan_id
            or self.roots[-1].schedule_code != self.proposal.selected_schedule_code
            or self.roots[-1].durable_proposal_id != self.proposal.proposal_id
            or self.roots[-1].audit_result_id != self.selected_audit_result_id
            or self.request_count != 5
            or self.resolution_count != 55
            or self.computes + self.hits != 55
            or self.lower_computes + self.lower_hits != 50
            or self.root_computes + self.root_hits != 5
            or self.computes != self.lower_computes + self.root_computes
            or self.hits != self.lower_hits + self.root_hits
            or self.root_computes != 5
            or self.root_hits != 0
            or self.kernel_transition_calls != 0
            or self.action_catalogue_calls != 0
            or self.ground_optimizer_calls != 0
        ):
            raise DurableH2InvariantViolation("durable occurrence arm changed")
        expected = {
            DurableH2ArmKind.REQUEST_RESET: (55, 0, 50, 0, 0),
            DurableH2ArmKind.OCCURRENCE_RESET_GLOBAL_DAG: (35, 20, 30, 20, 0),
            DurableH2ArmKind.DURABLE_CROSS_PROCESS_CONTINUATION: (
                5,
                50,
                0,
                50,
                30,
            ),
        }[self.kind]
        actual = (
            self.computes,
            self.hits,
            self.lower_computes,
            self.lower_hits,
            self.preloaded_lower_entries,
        )
        if actual != expected:
            raise DurableH2InvariantViolation("durable arm golden counts changed")
        expected_preloaded = (
            30
            if self.kind is DurableH2ArmKind.DURABLE_CROSS_PROCESS_CONTINUATION
            else 0
        )
        if len(self.preloaded_entry_bindings) != expected_preloaded:
            raise DurableH2InvariantViolation("durable arm preload cardinality changed")
        scope = (
            live.LiveEpochCacheScope.REQUEST_RESET
            if self.kind is DurableH2ArmKind.REQUEST_RESET
            else live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG
        )
        cache = dict(self.preloaded_entry_bindings)
        derived_computes = 0
        derived_hits = 0
        for request_offset in range(5):
            if self.kind is DurableH2ArmKind.REQUEST_RESET:
                cache = {}
            group = resolutions[request_offset * 11 : (request_offset + 1) * 11]
            root = self.roots[request_offset]
            if (
                tuple(item.slot for item in group) != live.SLOT_ORDER
                or any(item.request_id != root.request_id for item in group)
            ):
                raise DurableH2InvariantViolation(
                    "durable arm resolution request/slot order changed"
                )
            for expected_sequence, resolution in enumerate(
                group,
                start=request_offset * 11 + 1,
            ):
                if (
                    resolution.sequence_number != expected_sequence
                    or resolution.epoch is not live.LiveEpochName.FINAL
                    or resolution.pre_cache_state_id
                    != live._cache_state_id(scope, cache)
                ):
                    raise DurableH2InvariantViolation(
                        "durable arm resolution pre-state changed"
                    )
                if resolution.outcome is live.LiveEpochResolutionOutcome.COMPUTED:
                    if resolution.node_key_id in cache:
                        raise DurableH2InvariantViolation(
                            "durable arm computed an already-present node"
                        )
                    cache[resolution.node_key_id] = resolution.entry_id
                    derived_computes += 1
                else:
                    if cache.get(resolution.node_key_id) != resolution.entry_id:
                        raise DurableH2InvariantViolation(
                            "durable arm reused an absent or foreign node"
                        )
                    derived_hits += 1
                if resolution.post_cache_state_id != live._cache_state_id(scope, cache):
                    raise DurableH2InvariantViolation(
                        "durable arm resolution post-state changed"
                    )
            if group[-1].entry_id != root.legacy_root_entry_id:
                raise DurableH2InvariantViolation(
                    "durable arm root differs from its R resolution"
                )
        if (derived_computes, derived_hits) != (self.computes, self.hits):
            raise DurableH2InvariantViolation(
                "durable arm aggregate counts are not receipt-derived"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_occurrence_arm.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "commit_id": self.commit_id,
            "kind": self.kind.value,
            "proposal": self.proposal.to_document(),
            "roots": [item.to_document() for item in self.roots],
            "selected_audit_result_id": self.selected_audit_result_id,
            "preloaded_entry_bindings": [
                {"node_key_id": node_key_id, "entry_id": entry_id}
                for node_key_id, entry_id in self.preloaded_entry_bindings
            ],
            "resolution_documents": [
                dict(item) for item in self.resolution_documents
            ],
            "computes": self.computes,
            "hits": self.hits,
            "lower_computes": self.lower_computes,
            "lower_hits": self.lower_hits,
            "root_computes": self.root_computes,
            "root_hits": self.root_hits,
            "preloaded_lower_entries": self.preloaded_lower_entries,
            "request_count": self.request_count,
            "resolution_count": self.resolution_count,
            "kernel_transition_calls": self.kernel_transition_calls,
            "action_catalogue_calls": self.action_catalogue_calls,
            "ground_optimizer_calls": self.ground_optimizer_calls,
        }

    @property
    def arm_id(self) -> str:
        return _content_id("arm", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "arm_id": self.arm_id}


@dataclass(frozen=True, slots=True)
class DurableH2LoadReceiptV1:
    occurrence_id: str
    commit_id: str
    protocol_id: str
    payload_id: str
    manifest_id: str
    loaded_entry_bindings: tuple[tuple[str, str], ...]
    empty_cache_state_id: str
    seeded_cache_state_id: str
    semantic_replay_computes: int
    semantic_replay_hits: int
    semantic_replay_resolution_count: int = 44
    loaded_lower_entry_count: int = 30
    loaded_root_entry_count: int = 0
    canonical_bytes_verified: bool = True
    exact_model_derived_payload_verified: bool = True
    kernel_transition_calls: int = 0
    action_catalogue_calls: int = 0
    ground_optimizer_calls: int = 0

    def __post_init__(self) -> None:
        for value in (
            self.occurrence_id,
            self.commit_id,
            self.protocol_id,
            self.payload_id,
            self.manifest_id,
            self.empty_cache_state_id,
            self.seeded_cache_state_id,
        ):
            _cid(value, "durable load-receipt identity")
        if (
            self.occurrence_id not in WARM_OCCURRENCE_IDS
            or type(self.loaded_entry_bindings) is not tuple
            or self.loaded_entry_bindings
            != tuple(sorted(set(self.loaded_entry_bindings)))
            or len(self.loaded_entry_bindings) != 30
        ):
            raise DurableH2InvariantViolation("durable load binding set changed")
        for item in self.loaded_entry_bindings:
            if (
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) is not str
            ):
                raise DurableH2InvariantViolation(
                    "durable load binding is not an exact pair"
                )
            _cid(item[0], "durable load node key")
            _cid(item[1], "durable load entry")
        expected_empty = live._cache_state_id(
            live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG,
            {},
        )
        expected_seeded = live._cache_state_id(
            live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG,
            dict(self.loaded_entry_bindings),
        )
        if (
            self.empty_cache_state_id != expected_empty
            or self.seeded_cache_state_id != expected_seeded
            or self.semantic_replay_computes != 34
            or self.semantic_replay_hits != 10
            or self.semantic_replay_resolution_count != 44
            or self.loaded_lower_entry_count != 30
            or self.loaded_root_entry_count != 0
            or self.canonical_bytes_verified is not True
            or self.exact_model_derived_payload_verified is not True
            or self.kernel_transition_calls != 0
            or self.action_catalogue_calls != 0
            or self.ground_optimizer_calls != 0
        ):
            raise DurableH2InvariantViolation("durable load receipt changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_proof_checkpoint_load.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "commit_id": self.commit_id,
            "protocol_id": self.protocol_id,
            "payload_id": self.payload_id,
            "manifest_id": self.manifest_id,
            "loaded_entry_bindings": [
                {"node_key_id": node_key_id, "entry_id": entry_id}
                for node_key_id, entry_id in self.loaded_entry_bindings
            ],
            "empty_cache_state_id": self.empty_cache_state_id,
            "seeded_cache_state_id": self.seeded_cache_state_id,
            "semantic_replay_computes": self.semantic_replay_computes,
            "semantic_replay_hits": self.semantic_replay_hits,
            "semantic_replay_resolution_count": self.semantic_replay_resolution_count,
            "loaded_lower_entry_count": self.loaded_lower_entry_count,
            "loaded_root_entry_count": self.loaded_root_entry_count,
            "canonical_bytes_verified": self.canonical_bytes_verified,
            "exact_model_derived_payload_verified": (
                self.exact_model_derived_payload_verified
            ),
            "kernel_transition_calls": self.kernel_transition_calls,
            "action_catalogue_calls": self.action_catalogue_calls,
            "ground_optimizer_calls": self.ground_optimizer_calls,
        }

    @property
    def load_receipt_id(self) -> str:
        return _content_id("load_receipt", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "load_receipt_id": self.load_receipt_id}


@dataclass(frozen=True, slots=True)
class DurableH2WarmOccurrenceV1:
    occurrence_id: str
    commit_id: str
    load_receipt: DurableH2LoadReceiptV1
    request_reset: DurableH2OccurrenceArmV1
    occurrence_reset: DurableH2OccurrenceArmV1
    durable_continuation: DurableH2OccurrenceArmV1
    fresh_process_attested: bool = True
    parent_process_distinct: bool = True
    process_launch_count: int = 1
    target_kernel_object_available: bool = False
    ground_kernel_module_import_free_claimed: bool = False
    kernel_access_guard_installed: bool = True
    operational_ground_calls: int = 0

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "warm occurrence")
        _cid(self.commit_id, "warm occurrence commit")
        arms = (
            self.request_reset,
            self.occurrence_reset,
            self.durable_continuation,
        )
        if (
            type(self.load_receipt) is not DurableH2LoadReceiptV1
            or self.load_receipt.occurrence_id != self.occurrence_id
            or self.load_receipt.commit_id != self.commit_id
            or tuple(item.kind for item in arms)
            != (
                DurableH2ArmKind.REQUEST_RESET,
                DurableH2ArmKind.OCCURRENCE_RESET_GLOBAL_DAG,
                DurableH2ArmKind.DURABLE_CROSS_PROCESS_CONTINUATION,
            )
            or any(
                item.occurrence_id != self.occurrence_id
                or item.commit_id != self.commit_id
                for item in arms
            )
            or len({item.proposal.selected_plan_id for item in arms}) != 1
            or len({item.proposal.selected_semantic_key for item in arms}) != 1
            or len({item.selected_audit_result_id for item in arms}) != 1
            or self.fresh_process_attested is not True
            or self.parent_process_distinct is not True
            or self.process_launch_count != 1
            or self.target_kernel_object_available is not False
            or self.ground_kernel_module_import_free_claimed is not False
            or self.kernel_access_guard_installed is not True
            or self.operational_ground_calls != 0
            or self.durable_continuation.preloaded_entry_bindings
            != self.load_receipt.loaded_entry_bindings
        ):
            raise DurableH2InvariantViolation("warm occurrence isolation changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "commit_id": self.commit_id,
            "load_receipt": self.load_receipt.to_document(),
            "request_reset": self.request_reset.to_document(),
            "occurrence_reset": self.occurrence_reset.to_document(),
            "durable_continuation": self.durable_continuation.to_document(),
            "fresh_process_attested": self.fresh_process_attested,
            "parent_process_distinct": self.parent_process_distinct,
            "process_launch_count": self.process_launch_count,
            "target_kernel_object_available": self.target_kernel_object_available,
            "ground_kernel_module_import_free_claimed": (
                self.ground_kernel_module_import_free_claimed
            ),
            "kernel_access_guard_installed": self.kernel_access_guard_installed,
            "operational_ground_calls": self.operational_ground_calls,
        }

    @property
    def occurrence_result_id(self) -> str:
        return _content_id("occurrence_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_result_id": self.occurrence_result_id}


def _preload_runtime(
    lease: VerifiedDurableH2LeaseV1,
) -> live._Runtime:
    require_verified_durable_h2_lease_v1(lease)
    runtime = live._Runtime(
        live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG,
        live.live_epoch_proof_semantics_v1(),
    )
    if runtime.semantics.semantics_id != lease.manifest.protocol.proof_semantics_id:
        raise DurableH2InvariantViolation("durable proof semantics changed at load")
    for record in lease.payload.values:
        if record.slot is temporal.H2TemporalProofSlot.R:
            raise DurableH2InvariantViolation("durable preload contains forbidden R")
        runtime.cache[record.node_key_id] = record.entry.entry_id
        runtime.entries[record.entry.entry_id] = record.entry
        runtime.live_values[record.node_key_id] = _parse_temporal_value(
            record.slot, dict(record.value_document)
        )
    if len(runtime.cache) != 30:
        raise DurableH2InvariantViolation("durable preload did not install 30 lower entries")
    return runtime


def _empty_runtime(kind: DurableH2ArmKind) -> live._Runtime:
    scope = (
        live.LiveEpochCacheScope.REQUEST_RESET
        if kind is DurableH2ArmKind.REQUEST_RESET
        else live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG
    )
    return live._Runtime(scope, live.live_epoch_proof_semantics_v1())


def _root_wrapper(
    occurrence_id: str,
    commit_id: str,
    request: live.LiveEpochProofRequestV1,
    receipt: live.LiveEpochProofReceiptV1,
    runtime: live._Runtime,
    durable_proposal_id: str | None,
) -> DurableH2OccurrenceRootV1:
    entry = runtime.entries[receipt.root_entry_id]
    if entry.key.slot is not temporal.H2TemporalProofSlot.R:
        raise DurableH2InvariantViolation("durable root receipt does not resolve R")
    return DurableH2OccurrenceRootV1(
        occurrence_id,
        commit_id,
        request.request_id,
        request.request_index,
        request.role.value,
        request.schedule_code,
        request.contingent_plan.plan_id,
        durable_proposal_id,
        entry.entry_id,
        entry.result_digest,
        receipt.audit_result.result_id,
    )


def _execute_arm(
    lease: VerifiedDurableH2LeaseV1,
    occurrence_id: str,
    kind: DurableH2ArmKind,
) -> DurableH2OccurrenceArmV1:
    require_verified_durable_h2_lease_v1(lease)
    _cid(occurrence_id, "warm occurrence")
    if occurrence_id not in WARM_OCCURRENCE_IDS:
        raise DurableH2InvariantViolation("warm occurrence is not preregistered")
    runtime = (
        _preload_runtime(lease)
        if kind is DurableH2ArmKind.DURABLE_CROSS_PROCESS_CONTINUATION
        else _empty_runtime(kind)
    )
    preloaded = 30 if kind is DurableH2ArmKind.DURABLE_CROSS_PROCESS_CONTINUATION else 0
    build = _BuildView(lease.model, lease.manifest.build_result_id)
    rebase = _RebaseView(lease.thresholds, lease.manifest.threshold_rebase_id)
    evidence_request = _EvidenceRequestView(lease.manifest.evidence_request_id)
    evidence_bundle = _EvidenceBundleView(lease.manifest.evidence_bundle_id)
    stage_maps = _stage_maps(lease.candidate_requests)
    receipts: list[live.LiveEpochProofReceiptV1] = []
    candidate_roots: list[DurableH2OccurrenceRootV1] = []
    start = len(runtime.resolutions)
    for request in lease.candidate_requests:
        if kind is DurableH2ArmKind.REQUEST_RESET:
            runtime.reset()
        receipt = live._run_request(
            runtime,
            live.LiveEpochName.FINAL,
            request,
            build,
            rebase,
            evidence_request,
            evidence_bundle,
            stage_maps,
        )
        receipts.append(receipt)
        candidate_roots.append(
            _root_wrapper(
                occurrence_id,
                lease.expected_commit_id,
                request,
                receipt,
                runtime,
                None,
            )
        )
    plans = {
        request.contingent_plan.plan_id: request.contingent_plan
        for request in lease.candidate_requests
    }
    summaries = tuple(
        sorted(
            (
                planner._candidate_summary(
                    lease.thresholds,
                    receipt.request.contingent_plan,
                    receipt.audit_result,
                )
                for receipt in receipts
            ),
            key=lambda item: item.contingent_plan_id,
        )
    )
    selection_mode, selected_summary, semantic_key = (
        multistep._select_with_semantic_tie_break(lease.model, summaries, plans)
    )
    selected_plan = plans[selected_summary.contingent_plan_id]
    selected_candidate = next(
        request
        for request in lease.candidate_requests
        if request.contingent_plan.plan_id == selected_plan.plan_id
    )
    proposal = DurableH2PlanProposalV1(
        occurrence_id,
        lease.expected_commit_id,
        lease.model.model_id,
        lease.thresholds.thresholds_id,
        tuple(item.root_id for item in candidate_roots),
        tuple(request.contingent_plan.plan_id for request in lease.candidate_requests),
        selection_mode.value,
        selected_plan.plan_id,
        selected_candidate.schedule_code,
        semantic_key,
    )
    if kind is DurableH2ArmKind.REQUEST_RESET:
        runtime.reset()
    selected_request = live.LiveEpochProofRequestV1(
        live.LiveEpochName.FINAL,
        5,
        temporal.H2TemporalProofRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
        selected_candidate.schedule_code,
        lease.model.model_id,
        lease.thresholds.thresholds_id,
        selected_plan,
        selected_candidate.stage_assignment_ids,
        proposal.proposal_id,
    )
    selected_receipt = live._run_request(
        runtime,
        live.LiveEpochName.FINAL,
        selected_request,
        build,
        rebase,
        evidence_request,
        evidence_bundle,
        stage_maps,
    )
    selected_root = _root_wrapper(
        occurrence_id,
        lease.expected_commit_id,
        selected_request,
        selected_receipt,
        runtime,
        proposal.proposal_id,
    )
    roots = (*candidate_roots, selected_root)
    current = tuple(runtime.resolutions[start:])
    if len(current) != 55:
        raise DurableH2InvariantViolation("warm arm did not resolve exactly 55 slots")
    computes = sum(
        item.outcome is live.LiveEpochResolutionOutcome.COMPUTED for item in current
    )
    hits = sum(
        item.outcome is live.LiveEpochResolutionOutcome.REUSED for item in current
    )
    lower = tuple(item for item in current if item.slot is not temporal.H2TemporalProofSlot.R)
    root_rows = tuple(item for item in current if item.slot is temporal.H2TemporalProofSlot.R)
    preloaded_bindings = (
        tuple(
            sorted(
                (item.node_key_id, item.entry.entry_id)
                for item in lease.payload.values
            )
        )
        if kind is DurableH2ArmKind.DURABLE_CROSS_PROCESS_CONTINUATION
        else ()
    )
    return DurableH2OccurrenceArmV1(
        occurrence_id,
        lease.expected_commit_id,
        kind,
        proposal,
        roots,
        selected_receipt.audit_result.result_id,
        preloaded_bindings,
        tuple(item.to_document() for item in current),
        computes,
        hits,
        sum(item.outcome is live.LiveEpochResolutionOutcome.COMPUTED for item in lower),
        sum(item.outcome is live.LiveEpochResolutionOutcome.REUSED for item in lower),
        sum(item.outcome is live.LiveEpochResolutionOutcome.COMPUTED for item in root_rows),
        sum(item.outcome is live.LiveEpochResolutionOutcome.REUSED for item in root_rows),
        preloaded,
    )


def _derive_expected_warm_occurrence_v1(
    lease: VerifiedDurableH2LeaseV1,
    occurrence_id: str,
) -> DurableH2WarmOccurrenceV1:
    """Derive the complete lease-bound occurrence document."""

    require_verified_durable_h2_lease_v1(lease)
    loaded_bindings = tuple(
        sorted(
            (item.node_key_id, item.entry.entry_id)
            for item in lease.payload.values
        )
    )
    load_receipt = DurableH2LoadReceiptV1(
        occurrence_id,
        lease.expected_commit_id,
        lease.manifest.protocol.protocol_id,
        lease.payload.payload_id,
        lease.manifest.manifest_id,
        loaded_bindings,
        live._cache_state_id(
            live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG,
            {},
        ),
        live._cache_state_id(
            live.LiveEpochCacheScope.GLOBAL_CROSS_EPOCH_FACET_DAG,
            dict(loaded_bindings),
        ),
        lease.semantic_replay_computes,
        lease.semantic_replay_hits,
    )
    request_reset = _execute_arm(
        lease, occurrence_id, DurableH2ArmKind.REQUEST_RESET
    )
    occurrence_reset = _execute_arm(
        lease, occurrence_id, DurableH2ArmKind.OCCURRENCE_RESET_GLOBAL_DAG
    )
    durable = _execute_arm(
        lease, occurrence_id, DurableH2ArmKind.DURABLE_CROSS_PROCESS_CONTINUATION
    )
    return DurableH2WarmOccurrenceV1(
        occurrence_id,
        lease.expected_commit_id,
        load_receipt,
        request_reset,
        occurrence_reset,
        durable,
    )


def execute_durable_h2_warm_occurrence_v1(
    lease: VerifiedDurableH2LeaseV1,
    occurrence_id: str,
    parent_process_id: int,
) -> DurableH2WarmOccurrenceV1:
    """Execute all matched proof arms inside one fresh worker process."""

    require_verified_durable_h2_lease_v1(lease)
    if type(parent_process_id) is not int or parent_process_id <= 0:
        raise DurableH2InvariantViolation("worker parent process ID is invalid")
    if os.getpid() == parent_process_id:
        raise DurableH2InvariantViolation("warm occurrence did not cross a process boundary")
    return _derive_expected_warm_occurrence_v1(lease, occurrence_id)


def _parse_proposal(document: Any) -> DurableH2PlanProposalV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema", "schema_version", "profile_key", "occurrence_id",
            "commit_id", "model_id", "thresholds_id", "candidate_root_ids",
            "candidate_plan_ids", "selection_mode", "selected_plan_id",
            "selected_schedule_code", "selected_semantic_key", "candidate_count",
            "tie_break_rule", "proposal_id",
        },
        "durable proposal",
    )
    if (
        record["schema"] != "acfqp.h2_durable_plan_proposal.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
    ):
        raise DurableH2InvariantViolation("durable proposal schema changed")
    result = DurableH2PlanProposalV1(
        record["occurrence_id"],
        record["commit_id"],
        record["model_id"],
        record["thresholds_id"],
        tuple(record["candidate_root_ids"]),
        tuple(record["candidate_plan_ids"]),
        record["selection_mode"],
        record["selected_plan_id"],
        record["selected_schedule_code"],
        tuple(record["selected_semantic_key"]),
        record["candidate_count"],
        record["tie_break_rule"],
    )
    if result.to_document() != record:
        raise DurableH2InvariantViolation("durable proposal is not canonical")
    return result


def _parse_root(document: Any) -> DurableH2OccurrenceRootV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema", "schema_version", "profile_key", "occurrence_id",
            "commit_id", "request_id", "request_index", "request_role", "schedule_code",
            "plan_id", "durable_proposal_id", "legacy_root_entry_id",
            "legacy_root_result_digest", "audit_result_id", "root_id",
        },
        "durable occurrence root",
    )
    if (
        record["schema"] != "acfqp.h2_durable_occurrence_root.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
    ):
        raise DurableH2InvariantViolation("durable root schema changed")
    proposal_id = record["durable_proposal_id"]
    if type(proposal_id) is dict:
        typed_null = _exact_mapping(
            proposal_id, {"kind", "reason"}, "durable root proposal typed null"
        )
        if typed_null != {
            "kind": "NOT_APPLICABLE",
            "reason": "CANDIDATE_PRECEDES_SELECTION",
        }:
            raise DurableH2InvariantViolation("durable root typed null changed")
        proposal_id = None
    result = DurableH2OccurrenceRootV1(
        record["occurrence_id"],
        record["commit_id"],
        record["request_id"],
        record["request_index"],
        record["request_role"],
        record["schedule_code"],
        record["plan_id"],
        proposal_id,
        record["legacy_root_entry_id"],
        record["legacy_root_result_digest"],
        record["audit_result_id"],
    )
    if result.to_document() != record:
        raise DurableH2InvariantViolation("durable root is not canonical")
    return result


def _parse_arm(document: Any) -> DurableH2OccurrenceArmV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema", "schema_version", "profile_key", "occurrence_id",
            "commit_id", "kind", "proposal", "roots",
            "selected_audit_result_id", "preloaded_entry_bindings",
            "resolution_documents", "computes", "hits", "lower_computes",
            "lower_hits", "root_computes", "root_hits",
            "preloaded_lower_entries", "request_count", "resolution_count",
            "kernel_transition_calls", "action_catalogue_calls",
            "ground_optimizer_calls", "arm_id",
        },
        "durable occurrence arm",
    )
    if (
        record["schema"] != "acfqp.h2_durable_occurrence_arm.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
        or type(record["roots"]) is not list
        or type(record["preloaded_entry_bindings"]) is not list
        or type(record["resolution_documents"]) is not list
    ):
        raise DurableH2InvariantViolation("durable arm schema changed")
    result = DurableH2OccurrenceArmV1(
        record["occurrence_id"],
        record["commit_id"],
        DurableH2ArmKind(record["kind"]),
        _parse_proposal(record["proposal"]),
        tuple(_parse_root(item) for item in record["roots"]),
        record["selected_audit_result_id"],
        tuple(
            (
                _exact_mapping(
                    item,
                    {"node_key_id", "entry_id"},
                    "durable arm preloaded binding",
                )["node_key_id"],
                item["entry_id"],
            )
            for item in record["preloaded_entry_bindings"]
        ),
        tuple(record["resolution_documents"]),
        record["computes"],
        record["hits"],
        record["lower_computes"],
        record["lower_hits"],
        record["root_computes"],
        record["root_hits"],
        record["preloaded_lower_entries"],
        record["request_count"],
        record["resolution_count"],
        record["kernel_transition_calls"],
        record["action_catalogue_calls"],
        record["ground_optimizer_calls"],
    )
    if result.to_document() != record:
        raise DurableH2InvariantViolation("durable arm is not canonical")
    return result


def _parse_load_receipt(document: Any) -> DurableH2LoadReceiptV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "commit_id",
            "protocol_id",
            "payload_id",
            "manifest_id",
            "loaded_entry_bindings",
            "empty_cache_state_id",
            "seeded_cache_state_id",
            "semantic_replay_computes",
            "semantic_replay_hits",
            "semantic_replay_resolution_count",
            "loaded_lower_entry_count",
            "loaded_root_entry_count",
            "canonical_bytes_verified",
            "exact_model_derived_payload_verified",
            "kernel_transition_calls",
            "action_catalogue_calls",
            "ground_optimizer_calls",
            "load_receipt_id",
        },
        "durable load receipt",
    )
    if (
        record["schema"] != "acfqp.h2_durable_proof_checkpoint_load.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
        or type(record["loaded_entry_bindings"]) is not list
    ):
        raise DurableH2InvariantViolation("durable load receipt schema changed")
    bindings: list[tuple[str, str]] = []
    for item in record["loaded_entry_bindings"]:
        binding = _exact_mapping(
            item,
            {"node_key_id", "entry_id"},
            "durable load binding",
        )
        bindings.append((binding["node_key_id"], binding["entry_id"]))
    result = DurableH2LoadReceiptV1(
        record["occurrence_id"],
        record["commit_id"],
        record["protocol_id"],
        record["payload_id"],
        record["manifest_id"],
        tuple(bindings),
        record["empty_cache_state_id"],
        record["seeded_cache_state_id"],
        record["semantic_replay_computes"],
        record["semantic_replay_hits"],
        record["semantic_replay_resolution_count"],
        record["loaded_lower_entry_count"],
        record["loaded_root_entry_count"],
        record["canonical_bytes_verified"],
        record["exact_model_derived_payload_verified"],
        record["kernel_transition_calls"],
        record["action_catalogue_calls"],
        record["ground_optimizer_calls"],
    )
    if result.to_document() != record:
        raise DurableH2InvariantViolation("durable load receipt is not canonical")
    return result


def parse_durable_h2_warm_occurrence_v1(
    document: Any,
) -> DurableH2WarmOccurrenceV1:
    record = _exact_mapping(
        _normalize_document(document),
        {
            "schema", "schema_version", "profile_key", "occurrence_id",
            "commit_id", "load_receipt", "request_reset", "occurrence_reset",
            "durable_continuation", "fresh_process_attested",
            "parent_process_distinct", "process_launch_count",
            "target_kernel_object_available",
            "ground_kernel_module_import_free_claimed",
            "kernel_access_guard_installed", "operational_ground_calls",
            "occurrence_result_id",
        },
        "durable warm occurrence",
    )
    if (
        record["schema"] != "acfqp.h2_durable_occurrence_result.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
    ):
        raise DurableH2InvariantViolation("durable occurrence schema changed")
    result = DurableH2WarmOccurrenceV1(
        record["occurrence_id"],
        record["commit_id"],
        _parse_load_receipt(record["load_receipt"]),
        _parse_arm(record["request_reset"]),
        _parse_arm(record["occurrence_reset"]),
        _parse_arm(record["durable_continuation"]),
        record["fresh_process_attested"],
        record["parent_process_distinct"],
        record["process_launch_count"],
        record["target_kernel_object_available"],
        record["ground_kernel_module_import_free_claimed"],
        record["kernel_access_guard_installed"],
        record["operational_ground_calls"],
    )
    if result.to_document() != record:
        raise DurableH2InvariantViolation("durable occurrence is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class DurableH2CampaignResultV1:
    source_live_result_id: str
    protocol_id: str
    payload_id: str
    manifest_id: str
    commit_id: str
    checkpoint_byte_snapshot_id: str
    occurrences: tuple[DurableH2WarmOccurrenceV1, ...]
    occurrence_artifact_bytes: tuple[int, int]
    source_checkpoint_lower_constructions: int = 30
    source_checkpoint_root_constructions: int = 5
    source_upstream_transition_calls: int = 13
    source_upstream_catalogue_calls: int = 3
    warm_process_launches: int = 2
    request_reset_computes: int = 110
    request_reset_hits: int = 0
    occurrence_reset_computes: int = 70
    occurrence_reset_hits: int = 40
    durable_computes: int = 10
    durable_hits: int = 100
    parent_checkpoint_semantic_replay_computes: int = 34
    parent_checkpoint_semantic_replay_hits: int = 10
    parent_worker_output_verification_computes: int = 190
    parent_worker_output_verification_hits: int = 140
    worker_output_exactly_bound_to_verified_lease: bool = True
    avoided_cross_occurrence_lower_constructions: int = 60
    warm_kernel_transition_calls: int = 0
    warm_action_catalogue_calls: int = 0
    warm_ground_optimizer_calls: int = 0
    checkpoint_bytes_immutable_across_occurrences: bool = True
    registered_h2_same_query_durable_proof_state_claimed: bool = True
    generic_persistent_cache_claimed: bool = False
    durable_complete_certificate_cache_claimed: bool = False
    durable_R_persistence_claimed: bool = False
    cross_query_cache_claimed: bool = False
    cross_query_incremental_proof_claimed: bool = False
    changed_threshold_incremental_proof_claimed: bool = False
    changed_reward_incremental_proof_claimed: bool = False
    generic_changed_model_incremental_proof_claimed: bool = False
    generic_h_gt_1_recurrence_claimed: bool = False
    semantic_policy_change_claimed: bool = False
    generic_semantic_policy_change_claimed: bool = False
    horizon_greater_than_two_claimed: bool = False
    sample_reduction_claimed: bool = False
    sample_efficiency_claimed: bool = False
    total_work_or_wallclock_reduction_claimed: bool = False
    workload_economics_claimed: bool = False
    learned_or_partial_dynamics_claimed: bool = False
    coordinate_invention_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    counter_completeness_gate: str = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    sample_efficiency_gate: str = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    sample_efficiency_gate_blocks_mainline: bool = False
    status: str = SUCCESS_STATUS
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for value in (
            self.source_live_result_id,
            self.protocol_id,
            self.payload_id,
            self.manifest_id,
            self.commit_id,
            self.checkpoint_byte_snapshot_id,
        ):
            _cid(value, "durable campaign identity")
        if (
            type(self.occurrences) is not tuple
            or self.source_live_result_id != EXPECTED_SOURCE_LIVE_RESULT_ID
            or self.protocol_id != EXPECTED_DURABLE_PROTOCOL_ID
            or self.payload_id != EXPECTED_DURABLE_PAYLOAD_ID
            or self.manifest_id != EXPECTED_DURABLE_MANIFEST_ID
            or self.commit_id != EXPECTED_DURABLE_COMMIT_ID
            or self.checkpoint_byte_snapshot_id != EXPECTED_DURABLE_SNAPSHOT_ID
            or len(self.occurrences) != 2
            or tuple(item.occurrence_id for item in self.occurrences)
            != WARM_OCCURRENCE_IDS
            or any(item.commit_id != self.commit_id for item in self.occurrences)
            or tuple(item.occurrence_result_id for item in self.occurrences)
            != EXPECTED_WARM_OCCURRENCE_RESULT_IDS
            or tuple(
                (
                    item.request_reset.arm_id,
                    item.occurrence_reset.arm_id,
                    item.durable_continuation.arm_id,
                )
                for item in self.occurrences
            )
            != EXPECTED_WARM_ARM_IDS
            or any(
                item.load_receipt.protocol_id != self.protocol_id
                or item.load_receipt.payload_id != self.payload_id
                or item.load_receipt.manifest_id != self.manifest_id
                for item in self.occurrences
            )
            or type(self.occurrence_artifact_bytes) is not tuple
            or len(self.occurrence_artifact_bytes) != 2
            or any(
                type(item) is not int or item <= 0
                for item in self.occurrence_artifact_bytes
            )
            or self.source_checkpoint_lower_constructions != 30
            or self.source_checkpoint_root_constructions != 5
            or self.source_upstream_transition_calls != 13
            or self.source_upstream_catalogue_calls != 3
            or self.warm_process_launches != 2
            or (
                self.request_reset_computes,
                self.request_reset_hits,
                self.occurrence_reset_computes,
                self.occurrence_reset_hits,
                self.durable_computes,
                self.durable_hits,
            )
            != (110, 0, 70, 40, 10, 100)
            or (
                self.parent_checkpoint_semantic_replay_computes,
                self.parent_checkpoint_semantic_replay_hits,
                self.parent_worker_output_verification_computes,
                self.parent_worker_output_verification_hits,
            )
            != (34, 10, 190, 140)
            or self.worker_output_exactly_bound_to_verified_lease is not True
            or self.avoided_cross_occurrence_lower_constructions != 60
            or self.warm_kernel_transition_calls != 0
            or self.warm_action_catalogue_calls != 0
            or self.warm_ground_optimizer_calls != 0
            or self.checkpoint_bytes_immutable_across_occurrences is not True
            or self.registered_h2_same_query_durable_proof_state_claimed
            is not True
            or self.result_id != EXPECTED_DURABLE_CAMPAIGN_RESULT_ID
        ):
            raise DurableH2InvariantViolation("durable campaign golden result changed")
        locked_false = (
            self.generic_persistent_cache_claimed,
            self.durable_complete_certificate_cache_claimed,
            self.durable_R_persistence_claimed,
            self.cross_query_cache_claimed,
            self.cross_query_incremental_proof_claimed,
            self.changed_threshold_incremental_proof_claimed,
            self.changed_reward_incremental_proof_claimed,
            self.generic_changed_model_incremental_proof_claimed,
            self.generic_h_gt_1_recurrence_claimed,
            self.semantic_policy_change_claimed,
            self.generic_semantic_policy_change_claimed,
            self.horizon_greater_than_two_claimed,
            self.sample_reduction_claimed,
            self.sample_efficiency_claimed,
            self.total_work_or_wallclock_reduction_claimed,
            self.workload_economics_claimed,
            self.learned_or_partial_dynamics_claimed,
            self.coordinate_invention_claimed,
            self.official_execution_allowed,
            self.sample_efficiency_gate_blocks_mainline,
        )
        if (
            any(locked_false)
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.counter_completeness_gate != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            or self.sample_efficiency_gate != "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
            or self.status != SUCCESS_STATUS
        ):
            raise DurableH2InvariantViolation("durable campaign crossed claim locks")
        selected_plans = {
            item.durable_continuation.proposal.selected_plan_id
            for item in self.occurrences
        }
        selected_keys = {
            item.durable_continuation.proposal.selected_semantic_key
            for item in self.occurrences
        }
        selected_audits = {
            item.durable_continuation.selected_audit_result_id
            for item in self.occurrences
        }
        if (
            selected_plans != {EXPECTED_FINAL_PLAN_ID}
            or selected_keys != {(0, 1, 0, 1, 0, 1, 0, 1)}
            or selected_audits != {EXPECTED_FINAL_SELECTED_INNER_AUDIT_ID}
        ):
            raise DurableH2InvariantViolation("warm occurrences disagree semantically")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_campaign_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_live_result_id": self.source_live_result_id,
            "protocol_id": self.protocol_id,
            "payload_id": self.payload_id,
            "manifest_id": self.manifest_id,
            "commit_id": self.commit_id,
            "checkpoint_byte_snapshot_id": self.checkpoint_byte_snapshot_id,
            "occurrences": [item.to_document() for item in self.occurrences],
            "occurrence_artifact_bytes": list(self.occurrence_artifact_bytes),
            "source_checkpoint_lower_constructions": (
                self.source_checkpoint_lower_constructions
            ),
            "source_checkpoint_root_constructions": (
                self.source_checkpoint_root_constructions
            ),
            "source_upstream_transition_calls": self.source_upstream_transition_calls,
            "source_upstream_catalogue_calls": self.source_upstream_catalogue_calls,
            "warm_process_launches": self.warm_process_launches,
            "request_reset_computes": self.request_reset_computes,
            "request_reset_hits": self.request_reset_hits,
            "occurrence_reset_computes": self.occurrence_reset_computes,
            "occurrence_reset_hits": self.occurrence_reset_hits,
            "durable_computes": self.durable_computes,
            "durable_hits": self.durable_hits,
            "parent_checkpoint_semantic_replay_computes": (
                self.parent_checkpoint_semantic_replay_computes
            ),
            "parent_checkpoint_semantic_replay_hits": (
                self.parent_checkpoint_semantic_replay_hits
            ),
            "parent_worker_output_verification_computes": (
                self.parent_worker_output_verification_computes
            ),
            "parent_worker_output_verification_hits": (
                self.parent_worker_output_verification_hits
            ),
            "worker_output_exactly_bound_to_verified_lease": (
                self.worker_output_exactly_bound_to_verified_lease
            ),
            "avoided_cross_occurrence_lower_constructions": (
                self.avoided_cross_occurrence_lower_constructions
            ),
            "warm_kernel_transition_calls": self.warm_kernel_transition_calls,
            "warm_action_catalogue_calls": self.warm_action_catalogue_calls,
            "warm_ground_optimizer_calls": self.warm_ground_optimizer_calls,
            "checkpoint_bytes_immutable_across_occurrences": (
                self.checkpoint_bytes_immutable_across_occurrences
            ),
            "registered_h2_same_query_durable_proof_state_claimed": (
                self.registered_h2_same_query_durable_proof_state_claimed
            ),
            "generic_persistent_cache_claimed": self.generic_persistent_cache_claimed,
            "durable_complete_certificate_cache_claimed": (
                self.durable_complete_certificate_cache_claimed
            ),
            "durable_R_persistence_claimed": self.durable_R_persistence_claimed,
            "cross_query_cache_claimed": self.cross_query_cache_claimed,
            "cross_query_incremental_proof_claimed": (
                self.cross_query_incremental_proof_claimed
            ),
            "changed_threshold_incremental_proof_claimed": (
                self.changed_threshold_incremental_proof_claimed
            ),
            "changed_reward_incremental_proof_claimed": (
                self.changed_reward_incremental_proof_claimed
            ),
            "generic_changed_model_incremental_proof_claimed": (
                self.generic_changed_model_incremental_proof_claimed
            ),
            "generic_h_gt_1_recurrence_claimed": (
                self.generic_h_gt_1_recurrence_claimed
            ),
            "semantic_policy_change_claimed": self.semantic_policy_change_claimed,
            "generic_semantic_policy_change_claimed": (
                self.generic_semantic_policy_change_claimed
            ),
            "horizon_greater_than_two_claimed": self.horizon_greater_than_two_claimed,
            "sample_reduction_claimed": self.sample_reduction_claimed,
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "total_work_or_wallclock_reduction_claimed": (
                self.total_work_or_wallclock_reduction_claimed
            ),
            "workload_economics_claimed": self.workload_economics_claimed,
            "learned_or_partial_dynamics_claimed": (
                self.learned_or_partial_dynamics_claimed
            ),
            "coordinate_invention_claimed": self.coordinate_invention_claimed,
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "workload_economics_gate": self.workload_economics_gate,
            "counter_completeness_gate": self.counter_completeness_gate,
            "sample_efficiency_gate": self.sample_efficiency_gate,
            "sample_efficiency_gate_blocks_mainline": (
                self.sample_efficiency_gate_blocks_mainline
            ),
            "status": self.status,
        }

    @property
    def result_id(self) -> str:
        return _content_id("campaign_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def require_durable_h2_campaign_result_v1(
    result: DurableH2CampaignResultV1,
) -> DurableH2CampaignResultV1:
    if type(result) is not DurableH2CampaignResultV1:
        raise DurableH2InvariantViolation("durable result rejects substitutions")
    try:
        require_runtime_authority_v1(result, issuer=_RESULT_ISSUER)
    except ValueError as error:
        raise DurableH2InvariantViolation("durable result lacks live runner authority") from error
    return result


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


def _launch_warm_worker(
    store_root: Path,
    commit_id: str,
    occurrence_id: str,
    output_path: Path,
) -> tuple[DurableH2WarmOccurrenceV1, int]:
    source_root = Path(__file__).resolve().parents[1]
    bootstrap = (
        "import runpy,sys;"
        f"sys.path.insert(0,{str(source_root)!r});"
        "runpy.run_module('acfqp.h2_durable_proof_state_v1',run_name='__main__')"
    )
    command = (
        sys.executable,
        "-I",
        "-s",
        "-B",
        "-c",
        bootstrap,
        "--worker",
        "--store-root",
        str(store_root.resolve()),
        "--expected-commit-id",
        commit_id,
        "--occurrence-id",
        occurrence_id,
        "--output",
        str(output_path),
        "--parent-process-id",
        str(os.getpid()),
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
        raise DurableH2InvariantViolation("fresh warm worker timed out") from error
    if process.returncode != 0:
        diagnostic = stderr.decode("utf-8", errors="replace")[-2000:]
        raise DurableH2InvariantViolation(
            f"fresh warm worker failed with code {process.returncode}: {diagnostic}"
        )
    if stdout:
        raise DurableH2InvariantViolation("fresh warm worker emitted unexpected stdout")
    if not output_path.is_file() or output_path.is_symlink():
        raise DurableH2InvariantViolation("fresh warm worker omitted its canonical result")
    output_bytes = _read_stable_regular(output_path)
    envelope = _exact_mapping(
        _normalize_document(loads_canonical_json(output_bytes)),
        {
            "schema",
            "schema_version",
            "profile_key",
            "child_process_id",
            "parent_process_id",
            "occurrence",
        },
        "fresh worker output envelope",
    )
    if (
        envelope["schema"] != "acfqp.h2_durable_worker_output_envelope.v1"
        or envelope["schema_version"] != SCHEMA_VERSION
        or envelope["profile_key"] != PROFILE_KEY
        or envelope["child_process_id"] != process.pid
        or envelope["parent_process_id"] != os.getpid()
    ):
        raise DurableH2InvariantViolation(
            "fresh worker OS process attestation changed"
        )
    occurrence = parse_durable_h2_warm_occurrence_v1(envelope["occurrence"])
    if (
        occurrence.occurrence_id != occurrence_id
        or occurrence.commit_id != commit_id
    ):
        raise DurableH2InvariantViolation("fresh worker result context changed")
    return occurrence, len(canonical_json_bytes(occurrence.to_document()))


def _execute_lmb_h2_same_query_durable_proof_state_v1(
    source_live_result: live.LiveQueryLocalEpochInvalidationResultV1,
    store_root: Path,
) -> DurableH2CampaignResultV1:
    """Commit V0-053 lower proof state and consume it in two fresh processes."""

    if type(source_live_result) is not live.LiveQueryLocalEpochInvalidationResultV1:
        raise DurableH2InvariantViolation("durable runner rejects substituted sources")
    live.require_live_query_local_epoch_invalidation_result_v1(source_live_result)
    commit = write_durable_h2_checkpoint_v1(source_live_result, store_root)
    trusted_lease = load_verified_durable_h2_checkpoint_v1(
        store_root,
        commit.commit_id,
    )
    checkpoint_snapshot_id = _checkpoint_byte_snapshot_id(store_root, commit)
    occurrences: list[DurableH2WarmOccurrenceV1] = []
    output_sizes: list[int] = []
    with tempfile.TemporaryDirectory(prefix="acfqp-v0054a-workers-") as directory:
        output_root = Path(directory)
        for index, occurrence_id in enumerate(WARM_OCCURRENCE_IDS, start=1):
            if _checkpoint_byte_snapshot_id(store_root, commit) != checkpoint_snapshot_id:
                raise DurableH2InvariantViolation(
                    "checkpoint bytes changed before a warm occurrence"
                )
            output = output_root / f"occurrence-{index}.json"
            occurrence, size = _launch_warm_worker(
                store_root, commit.commit_id, occurrence_id, output
            )
            expected_occurrence = _derive_expected_warm_occurrence_v1(
                trusted_lease,
                occurrence_id,
            )
            if occurrence.to_document() != expected_occurrence.to_document():
                raise DurableH2InvariantViolation(
                    "fresh worker output differs from trusted lease-bound replay"
                )
            occurrences.append(occurrence)
            output_sizes.append(size)
            if _checkpoint_byte_snapshot_id(store_root, commit) != checkpoint_snapshot_id:
                raise DurableH2InvariantViolation(
                    "checkpoint bytes changed during a warm occurrence"
                )
    result = DurableH2CampaignResultV1(
        source_live_result.result_id,
        commit.protocol_id,
        commit.payload_id,
        commit.manifest_id,
        commit.commit_id,
        checkpoint_snapshot_id,
        tuple(occurrences),
        tuple(output_sizes),
    )
    return bind_runtime_authority_v1(result, issuer=_RESULT_ISSUER)


def run_lmb_h2_same_query_durable_proof_state_v1(
    source_live_result: live.LiveQueryLocalEpochInvalidationResultV1,
    store_root: Path,
) -> DurableH2CampaignResultV1:
    """Public V0-054A producer over one owner-bound V0-053 source."""

    return _execute_lmb_h2_same_query_durable_proof_state_v1(
        source_live_result,
        store_root,
    )


@dataclass(frozen=True, slots=True)
class DurableH2VerificationReportV1:
    claimed_result_id: str
    replayed_result_id: str
    exact_document_match: bool
    source_result_id: str
    evaluation_lane_only: bool = True
    included_in_operational_work: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.claimed_result_id,
            self.replayed_result_id,
            self.source_result_id,
        ):
            _cid(value, "durable verification identity")
        if (
            self.claimed_result_id != self.replayed_result_id
            or self.exact_document_match is not True
            or self.evaluation_lane_only is not True
            or self.included_in_operational_work is not False
            or self.report_id != EXPECTED_DURABLE_VERIFICATION_REPORT_ID
        ):
            raise DurableH2InvariantViolation("durable verification report changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_durable_verification_report.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "claimed_result_id": self.claimed_result_id,
            "replayed_result_id": self.replayed_result_id,
            "exact_document_match": self.exact_document_match,
            "source_result_id": self.source_result_id,
            "evaluation_lane_only": self.evaluation_lane_only,
            "included_in_operational_work": self.included_in_operational_work,
        }

    @property
    def report_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "report_id": self.report_id}


def verify_lmb_h2_same_query_durable_proof_state_v1(
    source_live_result: live.LiveQueryLocalEpochInvalidationResultV1,
    store_root: Path,
    claimed_result: DurableH2CampaignResultV1,
) -> DurableH2VerificationReportV1:
    """Verify original raw bytes, then independently rebuild both occurrences."""

    live.require_live_query_local_epoch_invalidation_result_v1(source_live_result)
    require_durable_h2_campaign_result_v1(claimed_result)
    original_lease = load_verified_durable_h2_checkpoint_v1(
        store_root,
        claimed_result.commit_id,
    )
    require_verified_durable_h2_lease_v1(original_lease)
    original_snapshot = _checkpoint_byte_snapshot_id(
        store_root,
        original_lease.commit,
    )
    if (
        original_lease.manifest.protocol.source_live_result_id
        != source_live_result.result_id
        or original_lease.commit.protocol_id != claimed_result.protocol_id
        or original_lease.payload.payload_id != claimed_result.payload_id
        or original_lease.manifest.manifest_id != claimed_result.manifest_id
        or original_snapshot != claimed_result.checkpoint_byte_snapshot_id
    ):
        raise DurableH2InvariantViolation(
            "claimed result differs from its original checkpoint bytes"
        )
    with tempfile.TemporaryDirectory(prefix="acfqp-v0054a-verifier-") as directory:
        replayed = _execute_lmb_h2_same_query_durable_proof_state_v1(
            source_live_result, Path(directory) / "store"
        )
    if (
        _checkpoint_byte_snapshot_id(store_root, original_lease.commit)
        != original_snapshot
    ):
        raise DurableH2InvariantViolation(
            "original checkpoint bytes changed during evaluation replay"
        )
    exact = replayed.to_document() == claimed_result.to_document()
    return DurableH2VerificationReportV1(
        claimed_result.result_id,
        replayed.result_id,
        exact,
        source_live_result.result_id,
    )


def _worker_cli(arguments: argparse.Namespace) -> int:
    try:
        store_root = Path(arguments.store_root)
        output = Path(arguments.output)
        if output.exists() or not output.parent.is_dir():
            raise DurableH2InvariantViolation("worker output target is not fresh")
        with _deny_lmb_ground_kernel_access():
            lease = load_verified_durable_h2_checkpoint_v1(
                store_root, arguments.expected_commit_id
            )
            result = execute_durable_h2_warm_occurrence_v1(
                lease,
                arguments.occurrence_id,
                arguments.parent_process_id,
            )
        envelope = {
            "schema": "acfqp.h2_durable_worker_output_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "child_process_id": os.getpid(),
            "parent_process_id": arguments.parent_process_id,
            "occurrence": result.to_document(),
        }
        _atomic_write(output, canonical_json_bytes(envelope))
        return 0
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


def _main(argv: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="acfqp-h2-durable-proof-state-v1")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--store-root")
    parser.add_argument("--expected-commit-id")
    parser.add_argument("--occurrence-id")
    parser.add_argument("--output")
    parser.add_argument("--parent-process-id", type=int)
    arguments = parser.parse_args(argv)
    if (
        arguments.worker is not True
        or type(arguments.store_root) is not str
        or type(arguments.expected_commit_id) is not str
        or type(arguments.occurrence_id) is not str
        or type(arguments.output) is not str
        or type(arguments.parent_process_id) is not int
    ):
        parser.error("the module is an internal fresh-process worker")
    return _worker_cli(arguments)


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(_main())
