"""Producer-free worker evidence primitives for V180r12r3.

This module freezes the two V180r12r2 documents that a *fresh* measurement
attempt may read and the typed receipts that cross the supervisor/worker
boundary.  It deliberately contains no filesystem opener, process launcher,
cgroup mutator, producer import, V180r12r2 verifier call, or output commit.
Those effects must be supplied by the separately authorized runtime and every
effect must be reported to the observer-owned campaign ledger.

The receipt classes prove only internal schema, identity, and cross-reference
consistency.  They do not turn caller supplied values into operating-system
facts.  A production verifier must replay the corresponding stable reads,
memfd seal queries, descriptor inventories, pidfd observations, and cgroup-v2
files independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import re
from typing import Any, Callable, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v180r12r3e as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_campaign_measurement_worker_v180r12r3"

TERMINAL_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation/TERMINAL.json"
)
VERIFICATION_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_verification.json"
)
TERMINAL_SCHEMA = "acfqp.ten_terminal_production_aggregation.v180r12r2"
VERIFICATION_SCHEMA = "acfqp.ten_terminal_aggregation_verification.v180r12r2"
TERMINAL_ID_FIELD = "production_aggregation_bundle_id"
VERIFICATION_ID_FIELD = "verification_id"
TERMINAL_BYTE_COUNT = 199_755
VERIFICATION_BYTE_COUNT = 2_752
TERMINAL_SHA256 = (
    "11c4431eb5aef1fa6d6805e38755d48ea252e7d3f26ba28f6bf9f4780029e6bf"
)
VERIFICATION_SHA256 = (
    "95ef7a8b98ddf2ff8214c0eafef00d250430b19951184feb87b302c62dcd2c05"
)
TERMINAL_CONTENT_ID = (
    "aba966326ff9e245d1758c65d8c3103614dd1a5a7be96b86e5eb2306bade15f0"
)
VERIFICATION_CONTENT_ID = (
    "551881bb9bc6baa8dfaa112228f9160986b8106572d6f3f6c85af49434ec14ee"
)
EXPECTED_TOTAL_INPUT_BYTES = TERMINAL_BYTE_COUNT + VERIFICATION_BYTE_COUNT

EVIDENCE_DOCUMENT_CONTRACT_ROWS = (
    (
        "STABLE_INPUT_SNAPSHOT",
        "acfqp.campaign_stable_input_snapshot.v180r12r3",
        domains.CONSTRUCTION_K7_STABLE_INPUT_SNAPSHOT_V180R12R3E_DOMAIN,
        "stable_input_snapshot_id",
    ),
    (
        "MEMFD_STAGE_RECEIPT",
        "acfqp.campaign_memfd_stage_receipt.v180r12r3",
        domains.CONSTRUCTION_K7_MEMFD_STAGE_RECEIPT_V180R12R3E_DOMAIN,
        "memfd_stage_receipt_id",
    ),
    (
        "FD_VISIBILITY_RECEIPT",
        "acfqp.campaign_fd_visibility_receipt.v180r12r3",
        domains.CONSTRUCTION_K7_FD_VISIBILITY_RECEIPT_V180R12R3E_DOMAIN,
        "fd_visibility_receipt_id",
    ),
    (
        "SEMANTIC_OPERATION_RECEIPT",
        "acfqp.campaign_semantic_operation_receipt.v180r12r3",
        domains.CONSTRUCTION_K7_SEMANTIC_OPERATION_RECEIPT_V180R12R3E_DOMAIN,
        "semantic_operation_receipt_id",
    ),
    (
        "REPLAY_SUBJECT_RECEIPT",
        "acfqp.campaign_replay_subject_receipt.v180r12r3",
        domains.CONSTRUCTION_K7_REPLAY_SUBJECT_RECEIPT_V180R12R3E_DOMAIN,
        "replay_subject_receipt_id",
    ),
    (
        "CAMPAIGN_SUBJECT_RESULT",
        "acfqp.campaign_measurement_subject_result.v180r12r3",
        domains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3E_DOMAIN,
        "subject_result_id",
    ),
)

CAMPAIGN_SUBJECT_RESULT_FIELD_KEYSET = frozenset(
    {
        "schema", "schema_version", "scope", "protocol_id",
        "authorization_id", "authorization_evidence_id", "attempt_id",
        "campaign_attempt_record_id",
        "execution_slot_id", "execution_nonce", "logical_occurrence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256", "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
        "terminal_content_id", "terminal_byte_count", "terminal_sha256",
        "verification_content_id", "verification_byte_count",
        "verification_sha256", "terminal_snapshot_id",
        "verification_snapshot_id", "memfd_stage_receipt_ids",
        "open_visibility_receipt_ids", "worker_birth_receipt_id",
        "operation_manifest_id", "inner_content_ids", "inner_content_id_count",
        "semantic_hash_operation_count", "integrity_check_operation_count",
        "protocol_check_operation_count",
        "route_component_counter_closure_status",
        "exact_v180r12r2_verification_replayed", "producer_module_imported",
        "producer_entrypoint_called", "v180r12r2_verifier_imported",
        "v180r12r2_verifier_called", "retroactive_v180r12r2_cost_claimed",
        "counter_completeness_gate", "workload_economics_gate",
        "scalar_calibration_gate", "break_even_gate",
        "official_execution_gate", "official_scalar_cost",
        "official_N_break_even", "official_execution_allowed",
        "subject_byte_count", "subject_result_id",
    }
)

EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS = (
    (
        "STABLE_INPUT_SNAPSHOT",
        "acfqp.campaign_stable_input_snapshot.v180r12r3",
        "stable_input_snapshot_id",
        frozenset(
            {
                "schema", "schema_version", "stable_input_fact_id", "role",
                "observed_byte_count", "observed_sha256", "observed_content_id",
                "canonical_json_replayed", "read_from_frozen_input_only",
                "stable_input_snapshot_id",
            }
        ),
    ),
    (
        "MEMFD_STAGE_RECEIPT",
        "acfqp.campaign_memfd_stage_receipt.v180r12r3",
        "memfd_stage_receipt_id",
        frozenset(
            {
                "schema", "schema_version", "input_snapshot_id", "role",
                "supervisor_fd", "worker_fd", "device", "inode", "byte_count",
                "sha256", "observed_seals", "supervisor_cloexec",
                "worker_read_only", "anonymous_inode", "link_count",
                "write_probe_errno", "memfd_stage_receipt_id",
            }
        ),
    ),
    (
        "FD_VISIBILITY_RECEIPT",
        "acfqp.campaign_fd_visibility_receipt.v180r12r3",
        "fd_visibility_receipt_id",
        frozenset(
            {
                "schema", "schema_version", "attempt_id", "operation_id",
                "stage_receipt_id", "holder_process_birth_receipt_id",
                "holder_role", "role", "state", "designated_worker_fd",
                "expected_device", "expected_inode", "observed_device",
                "observed_inode", "visible", "read_only",
                "unexpected_stage_fds", "fd_visibility_receipt_id",
            }
        ),
    ),
    (
        "SEMANTIC_OPERATION_RECEIPT",
        "acfqp.campaign_semantic_operation_receipt.v180r12r3",
        "semantic_operation_receipt_id",
        frozenset(
            {
                "schema", "schema_version", "attempt_id", "operation_id", "kind",
                "label", "family", "family_ordinal", "ordinal",
                "operation_manifest_id", "native_zero_source_manifest_id",
                "native_zero_import_inventory_id", "evidence_subject_id",
                "outcome_code", "measured_value", "auxiliary_values",
                "semantic_operation_receipt_id",
            }
        ),
    ),
    (
        "REPLAY_SUBJECT_RECEIPT",
        "acfqp.campaign_replay_subject_receipt.v180r12r3",
        "replay_subject_receipt_id",
        frozenset(
            {
                "schema", "schema_version", "subject_result_id",
                "campaign_attempt_record_id", "operation_manifest_id",
                "native_zero_source_manifest_id",
                "native_zero_import_inventory_id", "terminal_snapshot_id",
                "verification_snapshot_id", "open_visibility_receipt_ids",
                "semantic_operation_receipt_ids", "subject_byte_count",
                "subject_sha256", "producer_module_imported",
                "producer_entrypoint_called",
                "exact_v180r12r2_verification_replayed",
                "route_component_counter_closure_status", "fresh_replay_cost_only",
                "retroactive_v180r12r2_cost_claimed", "replay_subject_receipt_id",
            }
        ),
    ),
    (
        "CAMPAIGN_SUBJECT_RESULT",
        "acfqp.campaign_measurement_subject_result.v180r12r3",
        "subject_result_id",
        CAMPAIGN_SUBJECT_RESULT_FIELD_KEYSET,
    ),
)

REQUIRED_MEMFD_SEALS = (
    "F_SEAL_GROW",
    "F_SEAL_SEAL",
    "F_SEAL_SHRINK",
    "F_SEAL_WRITE",
)
SEMANTIC_HASH_OPERATION_COUNT = 137
INTEGRITY_CHECK_OPERATION_COUNT = 145
PROTOCOL_CHECK_OPERATION_COUNT = 15

INNER_CONTENT_ID_OPERATION_SUFFIXES = (
    *(f"source_receipt.{index:02d}" for index in range(5)),
    *(f"route_component_chain_receipt.{index:02d}" for index in range(12)),
    *(f"terminal_receipt.{index:02d}" for index in range(10)),
    *(f"terminal_shared_resource_receipt.{index:03d}" for index in range(90)),
    *(f"terminal_shared_resource_receipt_set.{index:02d}" for index in range(10)),
    "v180r7r1_construction_axis_receipt",
    "campaign_scope_structural_boundary",
)
SEMANTIC_HASH_OPERATION_LABELS = (
    "hash.source_file_sha256.terminal",
    "hash.source_file_sha256.verification",
    "hash.staged_file_sha256.terminal",
    "hash.staged_file_sha256.verification",
    "hash.top_content_id.terminal",
    "hash.top_content_id.verification",
    *(f"hash.inner_content_id.{suffix}" for suffix in INNER_CONTENT_ID_OPERATION_SUFFIXES),
    "hash.subject_result_id",
    "hash.subject_readback_sha256",
)
INTEGRITY_CHECK_OPERATION_LABELS = (
    "integrity.stage_source.terminal.stable_read",
    "integrity.stage_source.verification.stable_read",
    "integrity.stage_source.terminal.sha256",
    "integrity.stage_source.verification.sha256",
    "integrity.stage_source.terminal.memfd_seals",
    "integrity.stage_source.verification.memfd_seals",
    "integrity.worker_staged.terminal.sha256",
    "integrity.worker_staged.verification.sha256",
    "integrity.worker_staged.terminal.canonical_json",
    "integrity.worker_staged.verification.canonical_json",
    "integrity.worker_staged.terminal.top_content_id",
    "integrity.worker_staged.verification.top_content_id",
    *(f"integrity.worker_inner_content_id.{suffix}" for suffix in INNER_CONTENT_ID_OPERATION_SUFFIXES),
    "integrity.worker_inner_content_id.denominator_and_uniqueness",
    "integrity.worker_subject.canonical_json_and_content_id",
    "integrity.commit_subject.readback_size_and_sha256",
    "integrity.commit_subject.stable_mode_and_nlink",
)
PROTOCOL_CHECK_FAMILIES = (
    "TERMINAL_SCHEMA_AND_KEYSET",
    "VERIFICATION_SCHEMA_AND_KEYSET",
    "LINEAGE_IDS",
    "SOURCE_RECEIPT_ORDER",
    "ROUTE_COMPONENT_ORDER",
    "TERMINAL_RECEIPT_ORDER",
    "SHARED_SET_AND_RECEIPT_ORDER",
    "CONSTRUCTION_AXIS_SEPARATION",
    "STRUCTURAL_NINE_ZERO_ROUTE_FREE",
    "VERIFICATION_TERMINAL_BYTES_SHA_JOIN",
    "GLOBAL_DENOMINATORS",
    "PENDING_TO_PASS_TRANSITION",
    "FOUR_GATES_BLOCKER_AND_OFFICIAL",
    "SUCCESSOR_NONRETROACTIVITY_AND_IMPORT_BOUNDARY",
    "SUBJECT_SCHEMA_AND_KEYSET",
)
PROTOCOL_CHECK_OPERATION_LABELS = tuple(
    f"protocol.{family.lower()}" for family in PROTOCOL_CHECK_FAMILIES
)
if not (
    len(INNER_CONTENT_ID_OPERATION_SUFFIXES) == 129
    and len(SEMANTIC_HASH_OPERATION_LABELS) == SEMANTIC_HASH_OPERATION_COUNT
    and len(INTEGRITY_CHECK_OPERATION_LABELS) == INTEGRITY_CHECK_OPERATION_COUNT
    and len(PROTOCOL_CHECK_FAMILIES) == PROTOCOL_CHECK_OPERATION_COUNT
    and len(PROTOCOL_CHECK_OPERATION_LABELS) == PROTOCOL_CHECK_OPERATION_COUNT
    and len(
        set(
            SEMANTIC_HASH_OPERATION_LABELS
            + INTEGRITY_CHECK_OPERATION_LABELS
            + PROTOCOL_CHECK_OPERATION_LABELS
        )
    )
    == SEMANTIC_HASH_OPERATION_COUNT
    + INTEGRITY_CHECK_OPERATION_COUNT
    + PROTOCOL_CHECK_OPERATION_COUNT
):  # pragma: no cover
    raise RuntimeError("V180r12r3 semantic operation manifest is inconsistent")

V180R12R2_TERMINAL_DOMAIN = (
    "acfqp:construction-k7-ten-terminal-aggregation-terminal-bundle:v180r12r2"
)
V180R12R2_VERIFICATION_DOMAIN = (
    "acfqp:construction-k7-ten-terminal-aggregation-verification:v180r12r2"
)
V180R12R2_INNER_DOMAINS = {
    "source_receipt": (
        "acfqp:construction-k7-ten-terminal-source-verification-receipt:"
        "v180r12r2e"
    ),
    "route_component_chain_receipt": (
        "acfqp:construction-k7-route-component-chain-receipt:v180r12r2e"
    ),
    "terminal_receipt": (
        "acfqp:construction-k7-ten-terminal-chain-receipt:v180r12r2e"
    ),
    "terminal_shared_resource_receipt": (
        "acfqp:construction-k7-terminal-shared-resource-receipt:v180r12r2e"
    ),
    "terminal_shared_resource_receipt_set": (
        "acfqp:construction-k7-terminal-shared-resource-receipt-set:v180r12r2e"
    ),
    "v180r7r1_construction_axis_receipt": (
        "acfqp:construction-k7-v180r7r1-construction-axis-receipt:v180r12r2e"
    ),
    "campaign_scope_structural_boundary": (
        "acfqp:construction-k7-campaign-scope-structural-boundary:v180r12r2e"
    ),
}

EXPECTED_TERMINAL_CODES = (
    "ABSTRACT_CERTIFIED",
    "LOCAL_GROUND_RECOVERY",
    "FULL_GROUND_FALLBACK",
    "CACHED_EXACT_INFEASIBLE",
    "FULL_GROUND_EXACT_INFEASIBLE",
    "INTEGRITY_FAILURE",
    "PROTOCOL_FAILURE",
    "REBUILD_REQUIRED",
    "FALLBACK_CAP_EXHAUSTED",
    "ATTEMPT_BUDGET_EXHAUSTED",
)
EXPECTED_ROUTE_COMPONENTS = (
    ("ABSTRACT_CERTIFIED", "ABSTRACT_ONLY_CERTIFICATE"),
    ("LOCAL_GROUND_RECOVERY", "LOCAL_ATTEMPT"),
    ("FULL_GROUND_FALLBACK", "ABSTRACT_FAILED_PREFIX"),
    ("FULL_GROUND_FALLBACK", "LOCAL_ATTEMPT"),
    ("FULL_GROUND_FALLBACK", "DIRECT_FALLBACK"),
    ("CACHED_EXACT_INFEASIBLE", "ABSTRACT_FAILED_PREFIX"),
    ("FULL_GROUND_EXACT_INFEASIBLE", "DIRECT_FALLBACK"),
    ("INTEGRITY_FAILURE", "ABSTRACT_FAILED_PREFIX"),
    ("PROTOCOL_FAILURE", "ABSTRACT_FAILED_PREFIX"),
    ("REBUILD_REQUIRED", "REBUILD"),
    ("FALLBACK_CAP_EXHAUSTED", "DIRECT_FALLBACK"),
    ("ATTEMPT_BUDGET_EXHAUSTED", "ABSTRACT_FAILED_PREFIX"),
)
EXPECTED_SOURCE_KINDS = (
    "V180R11_RETAINED_V34_FINISH_FORWARD",
    "V180R10R1_RETAINED_V36_FINISH_FORWARD",
    "V180R7R1_FRESH_FULL_GROUND_FALLBACK",
    "V180R8_FRESH_CACHED_EXACT",
    "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
)

TERMINAL_KEYSET = frozenset(
    {
        "BREAK_EVEN_GATE", "COUNTER_COMPLETENESS_BLOCKER",
        "COUNTER_COMPLETENESS_GATE", "SCALAR_CALIBRATION_GATE",
        "WORKLOAD_ECONOMICS_GATE", "aggregation_protocol_id",
        "all_five_source_independent_verifiers_replayed",
        "all_ten_occurrence_shared_resource_receipt_sets_present",
        "all_twelve_route_component_chains_present",
        "campaign_scope_actual_comparison_vector_count",
        "campaign_scope_actual_counter_record_count",
        "campaign_scope_actual_native_zero_attestation_count",
        "campaign_scope_actual_projection_proof_count",
        "campaign_scope_actual_shared_resource_receipt_count",
        "campaign_scope_actual_work_vector_count",
        "campaign_scope_authoritative_receipt_count",
        "campaign_scope_structural_boundary",
        "campaign_scope_structural_obligation_count",
        "execution_authorization_id", "fixed_point_iteration",
        "historical_summary_translation_used",
        "occurrence_shared_resource_receipt_count", "official_N_break_even",
        "official_execution_allowed", "official_scalar_cost",
        "ordered_route_components", "ordered_terminal_codes",
        "output_bytes_fixed_point", "producer_bundle_independently_replayed",
        "production_aggregation_bundle_id", "route_component_chain_receipt_count",
        "route_component_chain_receipts", "route_component_counter_closure_status",
        "route_component_counter_record_count", "schema", "source_group_count",
        "source_verification_receipt_count", "source_verification_receipts",
        "ten_terminal_representative_counter_record_count", "terminal_code_count",
        "terminal_receipt_count", "terminal_receipts",
        "terminal_shared_resource_receipt_sets",
        "total_authoritative_shared_resource_receipt_count",
        "v180r7r1_additional_counter_record_count",
        "v180r7r1_construction_axis_receipt",
        "v180r7r1_construction_axis_receipt_count",
        "v180r7r1_construction_work_charged_to_route_components",
    }
)
VERIFICATION_KEYSET = frozenset(
    {
        "BREAK_EVEN_GATE", "COUNTER_COMPLETENESS_BLOCKER",
        "COUNTER_COMPLETENESS_GATE", "SCALAR_CALIBRATION_GATE",
        "WORKLOAD_ECONOMICS_GATE", "aggregation_byte_count",
        "aggregation_protocol_id", "aggregation_sha256",
        "all_five_source_independent_verifiers_replayed",
        "all_ninety_terminal_shared_resource_receipts_replayed",
        "all_route_component_actual_projection_proofs_replayed",
        "all_route_component_comparison_vectors_rederived",
        "all_route_component_counter_records_replayed",
        "all_route_component_native_zero_attestations_replayed",
        "all_route_component_work_vectors_replayed",
        "all_ten_terminal_receipts_replayed",
        "all_twelve_route_component_chains_replayed",
        "campaign_scope_actual_comparison_vector_count",
        "campaign_scope_actual_counter_record_count",
        "campaign_scope_actual_measurement_ledger_present",
        "campaign_scope_actual_native_zero_attestation_count",
        "campaign_scope_actual_projection_proof_count",
        "campaign_scope_actual_shared_resource_receipt_count",
        "campaign_scope_actual_work_vector_count",
        "campaign_scope_authoritative_receipt_count",
        "campaign_scope_has_no_route_kind",
        "campaign_scope_structural_boundary_replayed",
        "campaign_scope_structural_obligation_count", "execution_authorization_id",
        "historical_summary_translation_used",
        "occurrence_shared_resource_receipt_count", "official_N_break_even",
        "official_execution_allowed", "official_scalar_cost",
        "producer_aggregate_exact_bytes_reconstructed", "producer_module_imported",
        "production_aggregation_bundle_id", "route_component_chain_receipt_count",
        "route_component_counter_closure_status", "route_component_counter_record_count",
        "schema", "source_group_count", "source_verification_receipt_count",
        "ten_terminal_representative_counter_record_count", "terminal_code_count",
        "terminal_receipt_count", "terminal_receipt_denominators_replayed",
        "total_authoritative_shared_resource_receipt_count",
        "v180r12r3_actual_campaign_measurement_ledger_required",
        "v180r7r1_additional_counter_record_count",
        "v180r7r1_construction_axis_receipt_count",
        "v180r7r1_construction_axis_replayed_separately",
        "v180r7r1_construction_work_charged_to_route_components", "verification_id",
    }
)
VERIFICATION_REQUIRED_TRUE_FIELDS = (
    "all_five_source_independent_verifiers_replayed",
    "all_twelve_route_component_chains_replayed",
    "all_ten_terminal_receipts_replayed",
    "all_ninety_terminal_shared_resource_receipts_replayed",
    "all_route_component_counter_records_replayed",
    "all_route_component_work_vectors_replayed",
    "all_route_component_comparison_vectors_rederived",
    "all_route_component_actual_projection_proofs_replayed",
    "all_route_component_native_zero_attestations_replayed",
    "terminal_receipt_denominators_replayed",
    "campaign_scope_structural_boundary_replayed",
    "campaign_scope_has_no_route_kind",
    "v180r7r1_construction_axis_replayed_separately",
    "producer_aggregate_exact_bytes_reconstructed",
)
if (
    len(VERIFICATION_REQUIRED_TRUE_FIELDS)
    != len(set(VERIFICATION_REQUIRED_TRUE_FIELDS))
    or not set(VERIFICATION_REQUIRED_TRUE_FIELDS).issubset(VERIFICATION_KEYSET)
):
    raise AssertionError("verification required-true field contract changed")

_CID = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_AUXILIARY_NAME = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_MODULE_NAME = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
)
_FORBIDDEN_PRELOADED_MODULE_SUFFIXES = (
    "construction_k7_ten_terminal_aggregation_finalizer_v180r12r2",
    "construction_k7_ten_terminal_aggregation_independent_verifier_v180r12r2",
)


class ConstructionK7CampaignMeasurementWorkerV180R12R3Error(ValueError):
    """Worker input or evidence failed the frozen V180r12r3 contract."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CampaignMeasurementWorkerV180R12R3Error(message)


def _cid(value: Any, label: str) -> str:
    if type(value) is not str or _CID.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256 content ID")
    return value


def _token(value: Any, label: str) -> str:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        _fail(f"{label} must be one bounded uppercase token")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    value = _nonnegative(value, label)
    if value == 0:
        _fail(f"{label} must be positive")
    return value


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CampaignMeasurementWorkerV180R12R3Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} must be one canonical JSON object")
    return document


def _identity(domain: str, payload: Mapping[str, Any]) -> str:
    return domains.extension_content_id_v180r12r3e(domain, dict(payload))


class CampaignInputRoleV180R12R3(str, Enum):
    TERMINAL = "TERMINAL"
    VERIFICATION = "VERIFICATION"


class VisibilityStateV180R12R3(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class SemanticOperationKindV180R12R3(str, Enum):
    SEMANTIC_HASH = "SEMANTIC_HASH"
    INTEGRITY_CHECK = "INTEGRITY_CHECK"
    PROTOCOL_CHECK = "PROTOCOL_CHECK"


@dataclass(frozen=True, slots=True)
class MeasuredImportClosureV180R12R3:
    """Pure before/after guard for the preloaded measured-child import set."""

    preregistered_module_names: tuple[str, ...]
    attempt_open_module_names: tuple[str, ...]
    window_close_module_names: tuple[str, ...]

    def __post_init__(self) -> None:
        snapshots = (
            self.preregistered_module_names,
            self.attempt_open_module_names,
            self.window_close_module_names,
        )
        if any(
            type(snapshot) is not tuple
            or not snapshot
            or snapshot != tuple(sorted(set(snapshot)))
            or any(
                type(name) is not str or _MODULE_NAME.fullmatch(name) is None
                for name in snapshot
            )
            for snapshot in snapshots
        ):
            _fail("measured import-closure snapshots are not sorted exact module sets")
        if not (
            self.preregistered_module_names
            == self.attempt_open_module_names
            == self.window_close_module_names
        ):
            _fail("late or unregistered import appeared in the measured window")
        if any(
            name.endswith(suffix)
            for name in self.preregistered_module_names
            for suffix in _FORBIDDEN_PRELOADED_MODULE_SUFFIXES
        ):
            _fail("V180r12r2 producer-free predecessor executor was preloaded")


@dataclass(frozen=True, slots=True)
class StableCampaignInputFactV180R12R3:
    role: CampaignInputRoleV180R12R3
    relative_path: str
    schema: str
    identity_field: str
    content_id: str
    byte_count: int
    sha256: str

    def __post_init__(self) -> None:
        if type(self.role) is not CampaignInputRoleV180R12R3:
            _fail("stable input role is mistyped")
        if (
            type(self.relative_path) is not str
            or not self.relative_path
            or self.relative_path.startswith("/")
            or ".." in self.relative_path.split("/")
        ):
            _fail("stable input path must be one normalized relative path")
        if type(self.schema) is not str or not self.schema.startswith("acfqp."):
            _fail("stable input schema is malformed")
        if (
            type(self.identity_field) is not str
            or _AUXILIARY_NAME.fullmatch(self.identity_field) is None
        ):
            _fail("stable input identity field is malformed")
        _cid(self.content_id, "stable input content ID")
        _positive(self.byte_count, "stable input byte count")
        _cid(self.sha256, "stable input SHA-256")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_stable_input_fact.v180r12r3",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "role": self.role.value,
            "relative_path": self.relative_path,
            "document_schema": self.schema,
            "identity_field": self.identity_field,
            "content_id": self.content_id,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "fresh_replay_input": True,
            "retroactive_v180r12r2_cost_claimed": False,
        }

    @property
    def fact_id(self) -> str:
        return _identity(
            domains.CONSTRUCTION_K7_STABLE_INPUT_SNAPSHOT_V180R12R3E_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stable_input_fact_id": self.fact_id}


FROZEN_INPUT_FACTS_V180R12R3 = (
    StableCampaignInputFactV180R12R3(
        CampaignInputRoleV180R12R3.TERMINAL,
        TERMINAL_RELATIVE_PATH,
        TERMINAL_SCHEMA,
        TERMINAL_ID_FIELD,
        TERMINAL_CONTENT_ID,
        TERMINAL_BYTE_COUNT,
        TERMINAL_SHA256,
    ),
    StableCampaignInputFactV180R12R3(
        CampaignInputRoleV180R12R3.VERIFICATION,
        VERIFICATION_RELATIVE_PATH,
        VERIFICATION_SCHEMA,
        VERIFICATION_ID_FIELD,
        VERIFICATION_CONTENT_ID,
        VERIFICATION_BYTE_COUNT,
        VERIFICATION_SHA256,
    ),
)


def frozen_campaign_input_facts_v180r12r3(
) -> tuple[StableCampaignInputFactV180R12R3, ...]:
    """Return the exact two preregistered V180r12r2 input facts."""

    return FROZEN_INPUT_FACTS_V180R12R3


@dataclass(frozen=True, slots=True)
class StableInputSnapshotReceiptV180R12R3:
    fact: StableCampaignInputFactV180R12R3
    canonical_bytes: bytes = field(repr=False, compare=False)
    document: Mapping[str, Any] = field(init=False, repr=False, compare=False)
    snapshot_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.fact) is not StableCampaignInputFactV180R12R3:
            _fail("stable input snapshot fact is mistyped")
        document = _canonical_object(
            self.canonical_bytes, f"{self.fact.role.value} input snapshot"
        )
        if (
            len(self.canonical_bytes) != self.fact.byte_count
            or hashlib.sha256(self.canonical_bytes).hexdigest() != self.fact.sha256
            or document.get("schema") != self.fact.schema
            or document.get(self.fact.identity_field) != self.fact.content_id
        ):
            _fail("stable input snapshot drifted from its exact frozen fact")
        payload = {
            "schema": "acfqp.campaign_stable_input_snapshot.v180r12r3",
            "schema_version": SCHEMA_VERSION,
            "stable_input_fact_id": self.fact.fact_id,
            "role": self.fact.role.value,
            "observed_byte_count": len(self.canonical_bytes),
            "observed_sha256": hashlib.sha256(self.canonical_bytes).hexdigest(),
            "observed_content_id": document[self.fact.identity_field],
            "canonical_json_replayed": True,
            "read_from_frozen_input_only": True,
        }
        object.__setattr__(self, "document", document)
        object.__setattr__(
            self,
            "snapshot_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_STABLE_INPUT_SNAPSHOT_V180R12R3E_DOMAIN,
                payload,
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_stable_input_snapshot.v180r12r3",
            "schema_version": SCHEMA_VERSION,
            "stable_input_fact_id": self.fact.fact_id,
            "role": self.fact.role.value,
            "observed_byte_count": len(self.canonical_bytes),
            "observed_sha256": hashlib.sha256(self.canonical_bytes).hexdigest(),
            "observed_content_id": self.document[self.fact.identity_field],
            "canonical_json_replayed": True,
            "read_from_frozen_input_only": True,
            "stable_input_snapshot_id": self.snapshot_receipt_id,
        }


def read_exact_campaign_input_v180r12r3(
    fact: StableCampaignInputFactV180R12R3,
    *,
    stable_reader: Callable[[str], bytes],
) -> StableInputSnapshotReceiptV180R12R3:
    """Read one exact input through an injected symlink-safe stable reader."""

    if fact not in FROZEN_INPUT_FACTS_V180R12R3:
        _fail("campaign input fact is outside the frozen two-input domain")
    if not callable(stable_reader):
        _fail("stable input reader must be callable")
    raw = stable_reader(fact.relative_path)
    return StableInputSnapshotReceiptV180R12R3(fact, raw)


@dataclass(frozen=True, slots=True)
class MemfdStageReceiptV180R12R3:
    input_snapshot_id: str
    role: CampaignInputRoleV180R12R3
    supervisor_fd: int
    worker_fd: int
    device: int
    inode: int
    byte_count: int
    sha256: str
    observed_seals: tuple[str, ...]
    supervisor_cloexec: bool
    worker_read_only: bool
    anonymous_inode: bool
    link_count: int
    write_probe_errno: int
    stage_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        _cid(self.input_snapshot_id, "stage input snapshot ID")
        if type(self.role) is not CampaignInputRoleV180R12R3:
            _fail("stage role is mistyped")
        for value, label in (
            (self.supervisor_fd, "supervisor stage FD"),
            (self.worker_fd, "worker stage FD"),
            (self.device, "stage device"),
            (self.inode, "stage inode"),
        ):
            _nonnegative(value, label)
        _positive(self.byte_count, "stage byte count")
        _cid(self.sha256, "stage SHA-256")
        if (
            type(self.observed_seals) is not tuple
            or self.observed_seals != REQUIRED_MEMFD_SEALS
            or self.supervisor_cloexec is not True
            or self.worker_read_only is not True
            or self.anonymous_inode is not True
            or self.link_count != 0
            or type(self.write_probe_errno) is not int
            or self.write_probe_errno <= 0
            or self.supervisor_fd == self.worker_fd
        ):
            _fail("memfd stage did not prove the exact sealed read-only boundary")
        object.__setattr__(
            self,
            "stage_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_MEMFD_STAGE_RECEIPT_V180R12R3E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_memfd_stage_receipt.v180r12r3",
            "schema_version": SCHEMA_VERSION,
            "input_snapshot_id": self.input_snapshot_id,
            "role": self.role.value,
            "supervisor_fd": self.supervisor_fd,
            "worker_fd": self.worker_fd,
            "device": self.device,
            "inode": self.inode,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "observed_seals": list(self.observed_seals),
            "supervisor_cloexec": self.supervisor_cloexec,
            "worker_read_only": self.worker_read_only,
            "anonymous_inode": self.anonymous_inode,
            "link_count": self.link_count,
            "write_probe_errno": self.write_probe_errno,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "memfd_stage_receipt_id": self.stage_receipt_id}


@dataclass(frozen=True, slots=True)
class FDVisibilityReceiptV180R12R3:
    attempt_id: str
    operation_id: str
    stage_receipt_id: str
    holder_process_birth_receipt_id: str
    holder_role: str
    role: CampaignInputRoleV180R12R3
    state: VisibilityStateV180R12R3
    designated_worker_fd: int
    expected_device: int
    expected_inode: int
    observed_device: int | None
    observed_inode: int | None
    visible: bool
    read_only: bool
    unexpected_stage_fds: tuple[int, ...]
    visibility_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        _cid(self.attempt_id, "visibility attempt ID")
        _cid(self.operation_id, "visibility operation ID")
        _cid(self.stage_receipt_id, "visibility stage receipt ID")
        _cid(
            self.holder_process_birth_receipt_id,
            "visibility holder process birth receipt ID",
        )
        if (
            self.holder_role != "SUPERVISOR"
            or
            type(self.role) is not CampaignInputRoleV180R12R3
            or type(self.state) is not VisibilityStateV180R12R3
        ):
            _fail("FD visibility holder, input role, or state is mistyped")
        expected_ordinal = (
            0 if self.role is CampaignInputRoleV180R12R3.TERMINAL else 1
        )
        expected_operation_id = _identity(
            domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R3E_DOMAIN,
            {
                "schema": "acfqp.campaign_operation_identity.v180r12r3",
                "schema_version": SCHEMA_VERSION,
                "attempt_id": self.attempt_id,
                "slot": "MOUNT",
                "family": "SEALED_MEMFD",
                "ordinal": expected_ordinal,
            },
        )
        if self.operation_id != expected_operation_id:
            _fail("FD visibility receipt operation ID is foreign or role-permuted")
        for value, label in (
            (self.designated_worker_fd, "visibility designated worker FD"),
            (self.expected_device, "visibility expected device"),
            (self.expected_inode, "visibility expected inode"),
        ):
            _nonnegative(value, label)
        if (
            type(self.unexpected_stage_fds) is not tuple
            or tuple(sorted(set(self.unexpected_stage_fds)))
            != self.unexpected_stage_fds
            or any(type(value) is not int or value < 0 for value in self.unexpected_stage_fds)
        ):
            _fail("unexpected stage FD inventory is not sorted and unique")
        if self.state is VisibilityStateV180R12R3.OPEN:
            if not (
                self.visible is True
                and self.read_only is True
                and self.observed_device == self.expected_device
                and self.observed_inode == self.expected_inode
                and not self.unexpected_stage_fds
            ):
                _fail("open FD visibility did not match the staged memfd")
        elif not (
            self.visible is False
            and self.read_only is False
            and self.observed_device is None
            and self.observed_inode is None
            and not self.unexpected_stage_fds
        ):
            _fail("closed FD visibility did not prove descriptor absence")
        object.__setattr__(
            self,
            "visibility_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_FD_VISIBILITY_RECEIPT_V180R12R3E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_fd_visibility_receipt.v180r12r3",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": self.attempt_id,
            "operation_id": self.operation_id,
            "stage_receipt_id": self.stage_receipt_id,
            "holder_process_birth_receipt_id": (
                self.holder_process_birth_receipt_id
            ),
            "holder_role": self.holder_role,
            "role": self.role.value,
            "state": self.state.value,
            "designated_worker_fd": self.designated_worker_fd,
            "expected_device": self.expected_device,
            "expected_inode": self.expected_inode,
            "observed_device": self.observed_device,
            "observed_inode": self.observed_inode,
            "visible": self.visible,
            "read_only": self.read_only,
            "unexpected_stage_fds": list(self.unexpected_stage_fds),
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "fd_visibility_receipt_id": self.visibility_receipt_id,
        }


@dataclass(frozen=True, slots=True)
class SemanticOperationReceiptV180R12R3:
    attempt_id: str
    operation_id: str
    kind: SemanticOperationKindV180R12R3
    label: str
    family: str
    family_ordinal: int
    ordinal: int
    operation_manifest_id: str
    native_zero_source_manifest_id: str
    native_zero_import_inventory_id: str
    evidence_subject_id: str
    outcome_code: str
    measured_value: int
    auxiliary_values: tuple[tuple[str, str | int | bool], ...]
    semantic_operation_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        _cid(self.attempt_id, "semantic attempt ID")
        _cid(self.operation_id, "semantic operation ID")
        _cid(self.operation_manifest_id, "semantic operation manifest ID")
        _cid(self.native_zero_source_manifest_id, "semantic source manifest ID")
        _cid(self.native_zero_import_inventory_id, "semantic import inventory ID")
        _cid(self.evidence_subject_id, "semantic evidence subject ID")
        if type(self.kind) is not SemanticOperationKindV180R12R3:
            _fail("semantic operation kind is mistyped")
        limit = {
            SemanticOperationKindV180R12R3.SEMANTIC_HASH: (
                SEMANTIC_HASH_OPERATION_COUNT
            ),
            SemanticOperationKindV180R12R3.INTEGRITY_CHECK: (
                INTEGRITY_CHECK_OPERATION_COUNT
            ),
            SemanticOperationKindV180R12R3.PROTOCOL_CHECK: (
                PROTOCOL_CHECK_OPERATION_COUNT
            ),
        }[self.kind]
        if type(self.ordinal) is not int or self.ordinal not in range(limit):
            _fail("semantic operation ordinal is outside its frozen count")
        expected_family, expected_family_ordinal, expected_ordinal, _, _ = (
            _operation_coordinates(self.kind, self.label)
        )
        if (
            self.family != expected_family
            or self.family_ordinal != expected_family_ordinal
            or self.ordinal != expected_ordinal
        ):
            _fail("semantic operation label/family/ordinal binding changed")
        expected_operation_id = _identity(
            domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R3E_DOMAIN,
            {
                "schema": "acfqp.campaign_operation_identity.v180r12r3",
                "schema_version": SCHEMA_VERSION,
                "attempt_id": self.attempt_id,
                "slot": self.kind.value,
                "family": self.family,
                "ordinal": self.family_ordinal,
            },
        )
        if self.operation_id != expected_operation_id:
            _fail("semantic receipt operation ID is foreign or permuted")
        expected_outcome = (
            "SUCCESS"
            if self.kind is SemanticOperationKindV180R12R3.SEMANTIC_HASH
            else "PASS"
        )
        if _token(self.outcome_code, "semantic outcome code") != expected_outcome:
            _fail("successful semantic operation outcome changed")
        if self.measured_value != 1:
            _fail("successful semantic operation must measure exactly one")
        _validate_auxiliary_values(self.auxiliary_values)
        object.__setattr__(
            self,
            "semantic_operation_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_SEMANTIC_OPERATION_RECEIPT_V180R12R3E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_semantic_operation_receipt.v180r12r3",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": self.attempt_id,
            "operation_id": self.operation_id,
            "kind": self.kind.value,
            "label": self.label,
            "family": self.family,
            "family_ordinal": self.family_ordinal,
            "ordinal": self.ordinal,
            "operation_manifest_id": self.operation_manifest_id,
            "native_zero_source_manifest_id": self.native_zero_source_manifest_id,
            "native_zero_import_inventory_id": self.native_zero_import_inventory_id,
            "evidence_subject_id": self.evidence_subject_id,
            "outcome_code": self.outcome_code,
            "measured_value": self.measured_value,
            "auxiliary_values": [
                {"name": name, "value": value}
                for name, value in self.auxiliary_values
            ],
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "semantic_operation_receipt_id": self.semantic_operation_receipt_id,
        }


def _validate_auxiliary_values(
    values: Any,
) -> tuple[tuple[str, str | int | bool], ...]:
    if type(values) is not tuple:
        _fail("auxiliary values must be one exact tuple")
    names: list[str] = []
    for item in values:
        if type(item) is not tuple or len(item) != 2:
            _fail("each auxiliary value must be one name/value tuple")
        name, value = item
        if type(name) is not str or _AUXILIARY_NAME.fullmatch(name) is None:
            _fail("auxiliary value name is malformed")
        if type(value) not in {str, int, bool}:
            _fail("auxiliary value must be a canonical scalar")
        names.append(name)
    if names != sorted(set(names)):
        _fail("auxiliary values must be sorted and name-unique")
    return values


@dataclass(frozen=True, slots=True)
class ProducerFreeReplaySubjectReceiptV180R12R3:
    subject_result_id: str
    campaign_attempt_record_id: str
    operation_manifest_id: str
    native_zero_source_manifest_id: str
    native_zero_import_inventory_id: str
    terminal_snapshot_id: str
    verification_snapshot_id: str
    open_visibility_receipt_ids: tuple[str, str]
    semantic_operation_receipts: tuple[SemanticOperationReceiptV180R12R3, ...]
    subject_bytes: bytes = field(repr=False, compare=False)
    producer_module_imported: bool
    producer_entrypoint_called: bool
    exact_v180r12r2_verification_replayed: bool
    route_component_counter_closure_status: str
    replay_subject_receipt_id: str = field(init=False)

    def __post_init__(self) -> None:
        _cid(self.subject_result_id, "replay subject-result ID")
        _cid(self.campaign_attempt_record_id, "replay campaign attempt-record ID")
        _cid(self.operation_manifest_id, "replay operation manifest ID")
        _cid(self.native_zero_source_manifest_id, "replay source manifest ID")
        _cid(self.native_zero_import_inventory_id, "replay import inventory ID")
        _cid(self.terminal_snapshot_id, "terminal snapshot ID")
        _cid(self.verification_snapshot_id, "verification snapshot ID")
        if (
            type(self.open_visibility_receipt_ids) is not tuple
            or len(self.open_visibility_receipt_ids) != 2
            or len(set(self.open_visibility_receipt_ids)) != 2
        ):
            _fail("replay subject requires two distinct open visibility receipts")
        for value in self.open_visibility_receipt_ids:
            _cid(value, "open visibility receipt ID")
        if type(self.semantic_operation_receipts) is not tuple:
            _fail("semantic operation receipts must be one exact tuple")
        counts = {kind: 0 for kind in SemanticOperationKindV180R12R3}
        ordinals = {kind: set() for kind in SemanticOperationKindV180R12R3}
        operation_ids: set[str] = set()
        for receipt in self.semantic_operation_receipts:
            if type(receipt) is not SemanticOperationReceiptV180R12R3:
                _fail("semantic operation receipt is mistyped")
            if receipt.operation_id in operation_ids:
                _fail("semantic operation IDs must be globally unique")
            operation_ids.add(receipt.operation_id)
            counts[receipt.kind] += 1
            ordinals[receipt.kind].add(receipt.ordinal)
            if (
                receipt.operation_manifest_id != self.operation_manifest_id
                or receipt.native_zero_source_manifest_id
                != self.native_zero_source_manifest_id
                or receipt.native_zero_import_inventory_id
                != self.native_zero_import_inventory_id
                or receipt.evidence_subject_id != self.campaign_attempt_record_id
            ):
                _fail("semantic receipt crossed its attempt/manifest closure")
        expected = {
            SemanticOperationKindV180R12R3.SEMANTIC_HASH: (
                SEMANTIC_HASH_OPERATION_COUNT
            ),
            SemanticOperationKindV180R12R3.INTEGRITY_CHECK: (
                INTEGRITY_CHECK_OPERATION_COUNT
            ),
            SemanticOperationKindV180R12R3.PROTOCOL_CHECK: (
                PROTOCOL_CHECK_OPERATION_COUNT
            ),
        }
        if any(
            counts[kind] != limit or ordinals[kind] != set(range(limit))
            for kind, limit in expected.items()
        ):
            _fail("semantic operation receipts do not close the 137/145/15 schedule")
        expected_sequence = tuple(
            (SemanticOperationKindV180R12R3.SEMANTIC_HASH, ordinal)
            for ordinal in range(SEMANTIC_HASH_OPERATION_COUNT)
        ) + tuple(
            (SemanticOperationKindV180R12R3.INTEGRITY_CHECK, ordinal)
            for ordinal in range(INTEGRITY_CHECK_OPERATION_COUNT)
        ) + tuple(
            (SemanticOperationKindV180R12R3.PROTOCOL_CHECK, ordinal)
            for ordinal in range(PROTOCOL_CHECK_OPERATION_COUNT)
        )
        if tuple(
            (receipt.kind, receipt.ordinal)
            for receipt in self.semantic_operation_receipts
        ) != expected_sequence:
            _fail("semantic operation receipts changed exact kind/ordinal order")
        subject = _canonical_object(self.subject_bytes, "producer-free replay subject")
        subject_payload = dict(subject)
        supplied_subject_id = subject_payload.pop("subject_result_id", None)
        subject_domain = getattr(
            domains, "CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3E_DOMAIN", None
        )
        if not (
            type(subject_domain) is str
            and supplied_subject_id == self.subject_result_id
            and _identity(subject_domain, subject_payload) == self.subject_result_id
            and subject.get("campaign_attempt_record_id")
            == self.campaign_attempt_record_id
            and self.producer_module_imported is False
            and self.producer_entrypoint_called is False
            and self.exact_v180r12r2_verification_replayed is True
            and self.route_component_counter_closure_status == "PASS"
            and subject.get("producer_module_imported") is False
            and subject.get("producer_entrypoint_called") is False
            and subject.get("exact_v180r12r2_verification_replayed") is True
            and subject.get("route_component_counter_closure_status") == "PASS"
        ):
            _fail("replay subject is not a successful producer-free exact replay")
        object.__setattr__(
            self,
            "replay_subject_receipt_id",
            _identity(
                domains.CONSTRUCTION_K7_REPLAY_SUBJECT_RECEIPT_V180R12R3E_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_replay_subject_receipt.v180r12r3",
            "schema_version": SCHEMA_VERSION,
            "subject_result_id": self.subject_result_id,
            "campaign_attempt_record_id": self.campaign_attempt_record_id,
            "operation_manifest_id": self.operation_manifest_id,
            "native_zero_source_manifest_id": self.native_zero_source_manifest_id,
            "native_zero_import_inventory_id": self.native_zero_import_inventory_id,
            "terminal_snapshot_id": self.terminal_snapshot_id,
            "verification_snapshot_id": self.verification_snapshot_id,
            "open_visibility_receipt_ids": list(self.open_visibility_receipt_ids),
            "semantic_operation_receipt_ids": [
                receipt.semantic_operation_receipt_id
                for receipt in self.semantic_operation_receipts
            ],
            "subject_byte_count": len(self.subject_bytes),
            "subject_sha256": hashlib.sha256(self.subject_bytes).hexdigest(),
            "producer_module_imported": self.producer_module_imported,
            "producer_entrypoint_called": self.producer_entrypoint_called,
            "exact_v180r12r2_verification_replayed": (
                self.exact_v180r12r2_verification_replayed
            ),
            "route_component_counter_closure_status": (
                self.route_component_counter_closure_status
            ),
            "fresh_replay_cost_only": True,
            "retroactive_v180r12r2_cost_claimed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "replay_subject_receipt_id": self.replay_subject_receipt_id,
        }


@dataclass(frozen=True, slots=True)
class ProducerFreeReplayContractV180R12R3:
    terminal_fact: StableCampaignInputFactV180R12R3
    verification_fact: StableCampaignInputFactV180R12R3
    aggregation_protocol_id: str
    execution_authorization_id: str
    terminal_keyset: frozenset[str]
    verification_keyset: frozenset[str]
    source_kinds: tuple[str, ...]
    terminal_codes: tuple[str, ...]
    route_components: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not (
            type(self.terminal_fact) is StableCampaignInputFactV180R12R3
            and type(self.verification_fact) is StableCampaignInputFactV180R12R3
            and self.terminal_fact.role is CampaignInputRoleV180R12R3.TERMINAL
            and self.verification_fact.role
            is CampaignInputRoleV180R12R3.VERIFICATION
        ):
            _fail("producer-free replay contract input facts are malformed")
        _cid(self.aggregation_protocol_id, "replay contract protocol ID")
        _cid(self.execution_authorization_id, "replay contract authorization ID")
        if (
            type(self.terminal_keyset) is not frozenset
            or type(self.verification_keyset) is not frozenset
            or type(self.source_kinds) is not tuple
            or type(self.terminal_codes) is not tuple
            or type(self.route_components) is not tuple
            or len(self.source_kinds) != 5
            or len(self.terminal_codes) != 10
            or len(self.route_components) != 12
            or len(set(self.source_kinds)) != 5
            or len(set(self.terminal_codes)) != 10
            or len(set(self.route_components)) != 12
        ):
            _fail("producer-free replay contract populations are malformed")


EXACT_REPLAY_CONTRACT_V180R12R3 = ProducerFreeReplayContractV180R12R3(
    FROZEN_INPUT_FACTS_V180R12R3[0],
    FROZEN_INPUT_FACTS_V180R12R3[1],
    "d15ec6d29ffbb4908e20cabfbbc98f3aa53ec4ad38d1d4681930c3306737c965",
    "4a1424a1d27e97139acd10a50cac79ab012b8459be79b884d9adc3fd4b39e3a9",
    TERMINAL_KEYSET,
    VERIFICATION_KEYSET,
    EXPECTED_SOURCE_KINDS,
    EXPECTED_TERMINAL_CODES,
    EXPECTED_ROUTE_COMPONENTS,
)


@dataclass(frozen=True, slots=True)
class SubjectReadbackObservationV180R12R3:
    returned_bytes: bytes = field(repr=False, compare=False)
    mode: int
    link_count: int

    def __post_init__(self) -> None:
        if (
            type(self.returned_bytes) is not bytes
            or not self.returned_bytes
            or self.mode != 0o400
            or self.link_count != 1
        ):
            _fail("subject readback observation is not stable mode-0400 nlink-1 bytes")


@dataclass(frozen=True, slots=True)
class ReplayOperationResultV180R12R3:
    kind: SemanticOperationKindV180R12R3
    label: str
    family: str
    family_ordinal: int
    global_ordinal: int
    phase: str
    actor_role: str
    outcome_code: str
    measured_value: int
    observed_value: str | bool

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not SemanticOperationKindV180R12R3
            or type(self.label) is not str
            or _IDENTIFIER.fullmatch(self.label) is None
            or type(self.family) is not str
            or _TOKEN.fullmatch(self.family) is None
            or type(self.family_ordinal) is not int
            or self.family_ordinal < 0
            or type(self.global_ordinal) is not int
            or self.global_ordinal < 0
            or self.phase not in {"STAGE", "WORKER", "COMMIT"}
            or self.actor_role not in {"SUPERVISOR", "WORKER"}
            or self.measured_value != 1
            or type(self.observed_value) not in {str, bool}
        ):
            _fail("producer-free replay operation result is malformed")
        expected = (
            "SUCCESS"
            if self.kind is SemanticOperationKindV180R12R3.SEMANTIC_HASH
            else "PASS"
        )
        if self.outcome_code != expected:
            _fail("producer-free replay operation result outcome changed")


def semantic_operation_receipt_v180r12r3(
    *,
    attempt_id: str,
    operation_manifest_id: str,
    native_zero_source_manifest_id: str,
    native_zero_import_inventory_id: str,
    evidence_subject_id: str,
    result: ReplayOperationResultV180R12R3,
) -> SemanticOperationReceiptV180R12R3:
    """Materialize one receipt only from an actually evaluated replay result."""

    if type(result) is not ReplayOperationResultV180R12R3:
        _fail("semantic receipt factory requires one evaluated operation result")
    operation_id = _identity(
        domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_V180R12R3E_DOMAIN,
        {
            "schema": "acfqp.campaign_operation_identity.v180r12r3",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": _cid(attempt_id, "semantic receipt attempt ID"),
            "slot": result.kind.value,
            "family": result.family,
            "ordinal": result.family_ordinal,
        },
    )
    auxiliary_values: tuple[tuple[str, str | int | bool], ...] = (
        (("observed_sha256", result.observed_value),)
        if result.kind is SemanticOperationKindV180R12R3.SEMANTIC_HASH
        else (("check_passed", True),)
    )
    return SemanticOperationReceiptV180R12R3(
        attempt_id,
        operation_id,
        result.kind,
        result.label,
        result.family,
        result.family_ordinal,
        result.global_ordinal,
        _cid(operation_manifest_id, "semantic receipt operation manifest ID"),
        _cid(native_zero_source_manifest_id, "semantic receipt source manifest ID"),
        _cid(native_zero_import_inventory_id, "semantic receipt import inventory ID"),
        _cid(evidence_subject_id, "semantic receipt evidence subject ID"),
        result.outcome_code,
        result.measured_value,
        auxiliary_values,
    )


def materialize_semantic_operation_receipts_v180r12r3(
    computation: "ProducerFreeReplayComputationV180R12R3",
    *,
    execution_context: "ReplayExecutionContextV180R12R3",
    evidence_subject_id_by_label: Mapping[str, str],
) -> tuple[SemanticOperationReceiptV180R12R3, ...]:
    """Materialize the exact ordered 137+145+15 receipt bundle."""

    if (
        type(computation) is not ProducerFreeReplayComputationV180R12R3
        or type(execution_context) is not ReplayExecutionContextV180R12R3
    ):
        _fail("semantic receipt bundle requires one complete replay computation")
    results = (
        computation.hash_results
        + computation.integrity_results
        + computation.protocol_results
    )
    labels = tuple(result.label for result in results)
    if (
        type(evidence_subject_id_by_label) is not dict
        or set(evidence_subject_id_by_label) != set(labels)
        or set(evidence_subject_id_by_label.values())
        != {execution_context.campaign_attempt_record_id}
    ):
        _fail("semantic receipts must all bind the exact durable attempt record")
    receipts = tuple(
        semantic_operation_receipt_v180r12r3(
            attempt_id=execution_context.attempt_id,
            operation_manifest_id=execution_context.operation_manifest_id,
            native_zero_source_manifest_id=(
                execution_context.native_zero_source_manifest_id
            ),
            native_zero_import_inventory_id=(
                execution_context.native_zero_import_inventory_id
            ),
            evidence_subject_id=evidence_subject_id_by_label[result.label],
            result=result,
        )
        for result in results
    )
    if len(receipts) != 297 or len({row.operation_id for row in receipts}) != 297:
        _fail("semantic receipt bundle did not close the exact 297 operations")
    return receipts


@dataclass(frozen=True, slots=True)
class ProducerFreeReplayComputationV180R12R3:
    subject_bytes: bytes = field(repr=False, compare=False)
    subject_id: str
    inner_content_ids: tuple[tuple[str, str], ...]
    hash_results: tuple[ReplayOperationResultV180R12R3, ...]
    integrity_results: tuple[ReplayOperationResultV180R12R3, ...]
    protocol_results: tuple[ReplayOperationResultV180R12R3, ...]

    def __post_init__(self) -> None:
        subject = _canonical_object(self.subject_bytes, "producer-free replay subject")
        _cid(self.subject_id, "producer-free replay subject ID")
        if subject.get("subject_result_id") != self.subject_id:
            _fail("producer-free replay subject ID join changed")
        if (
            type(self.inner_content_ids) is not tuple
            or tuple(label for label, _ in self.inner_content_ids)
            != INNER_CONTENT_ID_OPERATION_SUFFIXES
            or len({value for _, value in self.inner_content_ids}) != 129
        ):
            _fail("producer-free replay inner content-ID set changed")
        for _, value in self.inner_content_ids:
            _cid(value, "producer-free replay inner content ID")
        expected = (
            (self.hash_results, SemanticOperationKindV180R12R3.SEMANTIC_HASH,
             SEMANTIC_HASH_OPERATION_LABELS),
            (self.integrity_results, SemanticOperationKindV180R12R3.INTEGRITY_CHECK,
             INTEGRITY_CHECK_OPERATION_LABELS),
            (self.protocol_results, SemanticOperationKindV180R12R3.PROTOCOL_CHECK,
             PROTOCOL_CHECK_OPERATION_LABELS),
        )
        for rows, kind, labels in expected:
            if (
                type(rows) is not tuple
                or tuple(row.label for row in rows) != labels
                or any(type(row) is not ReplayOperationResultV180R12R3 for row in rows)
                or any(row.kind is not kind for row in rows)
            ):
                _fail("producer-free replay operation result manifest changed")


OperationObserverV180R12R3 = Any


def _operation_coordinates(
    kind: SemanticOperationKindV180R12R3,
    label: str,
) -> tuple[str, int, int, str, str]:
    if kind is SemanticOperationKindV180R12R3.SEMANTIC_HASH:
        labels = SEMANTIC_HASH_OPERATION_LABELS
        families = (
            ("SOURCE_SHA256", 2, "STAGE", "SUPERVISOR"),
            ("STAGED_SHA256", 2, "WORKER", "WORKER"),
            ("TOP_CONTENT_ID", 2, "WORKER", "WORKER"),
            ("INNER_CONTENT_ID", 129, "WORKER", "WORKER"),
            ("SUBJECT_CONTENT_ID", 1, "WORKER", "WORKER"),
            ("SUBJECT_READBACK_SHA256", 1, "COMMIT", "SUPERVISOR"),
        )
    elif kind is SemanticOperationKindV180R12R3.INTEGRITY_CHECK:
        labels = INTEGRITY_CHECK_OPERATION_LABELS
        prefix_family = (
            ("integrity.stage_source.", "STAGE", "SUPERVISOR"),
            ("integrity.worker_staged.", "WORKER", "WORKER"),
            ("integrity.worker_inner_content_id.", "WORKER", "WORKER"),
            ("integrity.worker_subject.", "WORKER", "WORKER"),
            ("integrity.commit_subject.", "COMMIT", "SUPERVISOR"),
        )
        global_ordinal = labels.index(label)
        if label.endswith(".stable_read"):
            family = "STAGE_STABLE_INPUT"
        elif label.startswith("integrity.stage_source.") and label.endswith(".sha256"):
            family = "STAGE_SHA_MATCH"
        elif label.endswith(".memfd_seals"):
            family = "STAGE_SEAL_SET"
        elif label.startswith("integrity.worker_staged.") and label.endswith(".sha256"):
            family = "WORKER_STAGED_SHA"
        elif label.endswith(".canonical_json"):
            family = "WORKER_CANONICAL_JSON"
        elif label.endswith(".top_content_id"):
            family = "WORKER_TOP_ID_MATCH"
        elif label.startswith("integrity.worker_inner_content_id.") and not label.endswith(
            ".denominator_and_uniqueness"
        ):
            family = "WORKER_INNER_ID_MATCH"
        elif label.endswith(".denominator_and_uniqueness"):
            family = "WORKER_INNER_COUNT_AND_UNIQUENESS"
        elif label.startswith("integrity.worker_subject."):
            family = "WORKER_SUBJECT_CANONICAL_AND_ID"
        elif label.endswith(".readback_size_and_sha256"):
            family = "COMMIT_READBACK_SIZE_AND_SHA"
        else:
            family = "COMMIT_STABLE_MODE_AND_NLINK"
        same_family = [
            candidate
            for candidate in labels[: global_ordinal + 1]
            if _operation_coordinates_integrity_family(candidate) == family
        ]
        phase, actor = next(
            (candidate_phase, candidate_actor)
            for prefix, candidate_phase, candidate_actor in prefix_family
            if label.startswith(prefix)
        )
        return family, len(same_family) - 1, global_ordinal, phase, actor
    else:
        labels = PROTOCOL_CHECK_OPERATION_LABELS
        global_ordinal = labels.index(label)
        return (
            PROTOCOL_CHECK_FAMILIES[global_ordinal],
            0,
            global_ordinal,
            "WORKER",
            "WORKER",
        )
    global_ordinal = labels.index(label)
    start = 0
    for family, count, phase, actor in families:
        if global_ordinal < start + count:
            return family, global_ordinal - start, global_ordinal, phase, actor
        start += count
    raise AssertionError("semantic hash operation label escaped its manifest")


def _operation_coordinates_integrity_family(label: str) -> str:
    if label.endswith(".stable_read"):
        return "STAGE_STABLE_INPUT"
    if label.startswith("integrity.stage_source.") and label.endswith(".sha256"):
        return "STAGE_SHA_MATCH"
    if label.endswith(".memfd_seals"):
        return "STAGE_SEAL_SET"
    if label.startswith("integrity.worker_staged.") and label.endswith(".sha256"):
        return "WORKER_STAGED_SHA"
    if label.endswith(".canonical_json"):
        return "WORKER_CANONICAL_JSON"
    if label.endswith(".top_content_id"):
        return "WORKER_TOP_ID_MATCH"
    if label.startswith("integrity.worker_inner_content_id.") and not label.endswith(
        ".denominator_and_uniqueness"
    ):
        return "WORKER_INNER_ID_MATCH"
    if label.endswith(".denominator_and_uniqueness"):
        return "WORKER_INNER_COUNT_AND_UNIQUENESS"
    if label.startswith("integrity.worker_subject."):
        return "WORKER_SUBJECT_CANONICAL_AND_ID"
    if label.endswith(".readback_size_and_sha256"):
        return "COMMIT_READBACK_SIZE_AND_SHA"
    return "COMMIT_STABLE_MODE_AND_NLINK"


class _ReplayOperationRecorderV180R12R3:
    def __init__(self, observer: OperationObserverV180R12R3 | None) -> None:
        before = None if observer is None else getattr(observer, "before_operation", None)
        after = None if observer is None else getattr(observer, "after_operation", None)
        structured = callable(before) and callable(after) and not callable(observer)
        legacy = callable(observer) and before is None and after is None
        if observer is not None and not (structured or legacy):
            _fail("producer-free replay operation observer hooks are malformed")
        self.observer = observer
        self.structured_observer = structured
        self.hash_results: list[ReplayOperationResultV180R12R3] = []
        self.integrity_results: list[ReplayOperationResultV180R12R3] = []
        self.protocol_results: list[ReplayOperationResultV180R12R3] = []

    def _record(
        self,
        kind: SemanticOperationKindV180R12R3,
        label: str,
        evaluate: Callable[[], str | bool],
    ) -> str | bool:
        family, family_ordinal, global_ordinal, phase, actor = (
            _operation_coordinates(kind, label)
        )
        if self.observer is not None:
            if self.structured_observer:
                self.observer.before_operation(kind, label, phase, actor)
            else:
                self.observer("INTENT", label, None)
        value = evaluate()
        if kind is not SemanticOperationKindV180R12R3.SEMANTIC_HASH and value is not True:
            _fail(f"producer-free replay check failed at {label}")
        result = ReplayOperationResultV180R12R3(
            kind,
            label,
            family,
            family_ordinal,
            global_ordinal,
            phase,
            actor,
            "SUCCESS" if kind is SemanticOperationKindV180R12R3.SEMANTIC_HASH else "PASS",
            1,
            value,
        )
        if self.observer is not None:
            if self.structured_observer:
                self.observer.after_operation(result)
            else:
                self.observer("OUTCOME", label, result)
        target = {
            SemanticOperationKindV180R12R3.SEMANTIC_HASH: self.hash_results,
            SemanticOperationKindV180R12R3.INTEGRITY_CHECK: self.integrity_results,
            SemanticOperationKindV180R12R3.PROTOCOL_CHECK: self.protocol_results,
        }[kind]
        target.append(result)
        return value

    def hash_bytes(self, label: str, raw: bytes) -> str:
        value = self._record(
            SemanticOperationKindV180R12R3.SEMANTIC_HASH,
            label,
            lambda: hashlib.sha256(raw).hexdigest(),
        )
        assert type(value) is str
        return value

    def integrity(self, label: str, evaluate: Callable[[], bool]) -> None:
        self._record(SemanticOperationKindV180R12R3.INTEGRITY_CHECK, label, evaluate)

    def protocol(self, label: str, evaluate: Callable[[], bool]) -> None:
        self._record(SemanticOperationKindV180R12R3.PROTOCOL_CHECK, label, evaluate)


_COMMON_DENOMINATORS = {
    "source_group_count": 5,
    "source_verification_receipt_count": 5,
    "terminal_code_count": 10,
    "terminal_receipt_count": 10,
    "route_component_chain_receipt_count": 12,
    "ten_terminal_representative_counter_record_count": 2_690,
    "route_component_counter_record_count": 3_228,
    "v180r7r1_additional_counter_record_count": 538,
    "occurrence_shared_resource_receipt_count": 90,
    "campaign_scope_structural_obligation_count": 9,
    "campaign_scope_actual_counter_record_count": 0,
    "campaign_scope_actual_shared_resource_receipt_count": 0,
    "campaign_scope_actual_work_vector_count": 0,
    "campaign_scope_actual_comparison_vector_count": 0,
    "campaign_scope_actual_projection_proof_count": 0,
    "campaign_scope_actual_native_zero_attestation_count": 0,
    "campaign_scope_authoritative_receipt_count": 0,
    "total_authoritative_shared_resource_receipt_count": 90,
    "v180r7r1_construction_axis_receipt_count": 1,
}
_SHARED_RESOURCE_PATHS = (
    "common.hash_invocations", "common.integrity_checks",
    "common.protocol_checks", "io.mounted_bytes_peak", "io.output_bytes",
    "io.read_bytes", "io.staged_bytes", "memory.working_bytes_peak",
    "process.launches",
)


def _domain_hash(
    recorder: _ReplayOperationRecorderV180R12R3,
    label: str,
    domain: str,
    document: Mapping[str, Any],
    identity_field: str,
) -> tuple[str, bool]:
    payload = dict(document)
    claimed = payload.pop(identity_field, None)
    digest = recorder.hash_bytes(
        label, domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    )
    return digest, claimed == digest


def _contains_key(value: Any, key: str) -> bool:
    if type(value) is dict:
        return key in value or any(_contains_key(row, key) for row in value.values())
    if type(value) is list:
        return any(_contains_key(row, key) for row in value)
    return False


def _producer_free_replay_core_v180r12r3(
    terminal_bytes: bytes,
    verification_bytes: bytes,
    *,
    contract: ProducerFreeReplayContractV180R12R3,
    terminal_stage_receipt: MemfdStageReceiptV180R12R3,
    verification_stage_receipt: MemfdStageReceiptV180R12R3,
    subject_readback: Callable[[bytes], SubjectReadbackObservationV180R12R3],
    operation_observer: OperationObserverV180R12R3 | None = None,
) -> ProducerFreeReplayComputationV180R12R3:
    """Pure semantic replay used by the exact wrapper and synthetic tests."""

    if type(contract) is not ProducerFreeReplayContractV180R12R3:
        _fail("producer-free replay contract is mistyped")
    if (
        type(terminal_stage_receipt) is not MemfdStageReceiptV180R12R3
        or type(verification_stage_receipt) is not MemfdStageReceiptV180R12R3
        or terminal_stage_receipt.role is not CampaignInputRoleV180R12R3.TERMINAL
        or verification_stage_receipt.role
        is not CampaignInputRoleV180R12R3.VERIFICATION
        or not callable(subject_readback)
    ):
        _fail("producer-free replay stage or readback interface is malformed")
    recorder = _ReplayOperationRecorderV180R12R3(operation_observer)
    source_terminal_sha = recorder.hash_bytes(
        SEMANTIC_HASH_OPERATION_LABELS[0], terminal_bytes
    )
    source_verification_sha = recorder.hash_bytes(
        SEMANTIC_HASH_OPERATION_LABELS[1], verification_bytes
    )
    terminal_document = _canonical_object(terminal_bytes, "staged terminal")
    verification_document = _canonical_object(
        verification_bytes, "staged verification"
    )
    stage_pairs = (
        (
            "terminal", terminal_bytes, terminal_document, contract.terminal_fact,
            terminal_stage_receipt, source_terminal_sha,
        ),
        (
            "verification", verification_bytes, verification_document,
            contract.verification_fact, verification_stage_receipt,
            source_verification_sha,
        ),
    )
    for name, raw, document, fact, receipt, observed_sha in stage_pairs:
        recorder.integrity(
            f"integrity.stage_source.{name}.stable_read",
            lambda raw=raw, document=document, fact=fact: (
                len(raw) == fact.byte_count
                and document.get("schema") == fact.schema
                and document.get(fact.identity_field) == fact.content_id
            ),
        )
        recorder.integrity(
            f"integrity.stage_source.{name}.sha256",
            lambda fact=fact, receipt=receipt, observed_sha=observed_sha: (
                observed_sha == fact.sha256
                and receipt.sha256 == observed_sha
                and receipt.byte_count == fact.byte_count
            ),
        )
        recorder.integrity(
            f"integrity.stage_source.{name}.memfd_seals",
            lambda receipt=receipt: receipt.observed_seals == REQUIRED_MEMFD_SEALS,
        )
    staged_terminal_sha = recorder.hash_bytes(
        SEMANTIC_HASH_OPERATION_LABELS[2], terminal_bytes
    )
    staged_verification_sha = recorder.hash_bytes(
        SEMANTIC_HASH_OPERATION_LABELS[3], verification_bytes
    )
    recorder.integrity(
        "integrity.worker_staged.terminal.sha256",
        lambda: staged_terminal_sha == source_terminal_sha,
    )
    recorder.integrity(
        "integrity.worker_staged.verification.sha256",
        lambda: staged_verification_sha == source_verification_sha,
    )
    recorder.integrity(
        "integrity.worker_staged.terminal.canonical_json",
        lambda: canonical_json_bytes(terminal_document) == terminal_bytes,
    )
    recorder.integrity(
        "integrity.worker_staged.verification.canonical_json",
        lambda: canonical_json_bytes(verification_document) == verification_bytes,
    )
    terminal_id, terminal_id_valid = _domain_hash(
        recorder,
        SEMANTIC_HASH_OPERATION_LABELS[4],
        V180R12R2_TERMINAL_DOMAIN,
        terminal_document,
        contract.terminal_fact.identity_field,
    )
    verification_id, verification_id_valid = _domain_hash(
        recorder,
        SEMANTIC_HASH_OPERATION_LABELS[5],
        V180R12R2_VERIFICATION_DOMAIN,
        verification_document,
        contract.verification_fact.identity_field,
    )
    recorder.integrity(
        "integrity.worker_staged.terminal.top_content_id",
        lambda: terminal_id_valid and terminal_id == contract.terminal_fact.content_id,
    )
    recorder.integrity(
        "integrity.worker_staged.verification.top_content_id",
        lambda: verification_id_valid
        and verification_id == contract.verification_fact.content_id,
    )

    inner_documents: dict[str, tuple[dict[str, Any], str, str]] = {}
    for index, row in enumerate(terminal_document.get("source_verification_receipts", ())):
        inner_documents[f"source_receipt.{index:02d}"] = (
            row, "source_receipt_id", V180R12R2_INNER_DOMAINS["source_receipt"]
        )
    for index, row in enumerate(terminal_document.get("route_component_chain_receipts", ())):
        inner_documents[f"route_component_chain_receipt.{index:02d}"] = (
            row,
            "route_component_chain_receipt_id",
            V180R12R2_INNER_DOMAINS["route_component_chain_receipt"],
        )
    for index, row in enumerate(terminal_document.get("terminal_receipts", ())):
        inner_documents[f"terminal_receipt.{index:02d}"] = (
            row, "terminal_chain_receipt_id", V180R12R2_INNER_DOMAINS["terminal_receipt"]
        )
    shared_sets = terminal_document.get("terminal_shared_resource_receipt_sets", ())
    shared_index = 0
    for set_index, receipt_set in enumerate(shared_sets):
        if type(receipt_set) is not dict:
            _fail("terminal shared-resource receipt set is mistyped")
        for receipt in receipt_set.get("receipts", ()):
            inner_documents[
                f"terminal_shared_resource_receipt.{shared_index:03d}"
            ] = (
                receipt,
                "terminal_shared_resource_receipt_id",
                V180R12R2_INNER_DOMAINS["terminal_shared_resource_receipt"],
            )
            shared_index += 1
        inner_documents[
            f"terminal_shared_resource_receipt_set.{set_index:02d}"
        ] = (
            receipt_set,
            "terminal_shared_resource_receipt_set_id",
            V180R12R2_INNER_DOMAINS[
                "terminal_shared_resource_receipt_set"
            ],
        )
    inner_documents["v180r7r1_construction_axis_receipt"] = (
        terminal_document.get("v180r7r1_construction_axis_receipt"),
        "v180r7r1_construction_axis_receipt_id",
        V180R12R2_INNER_DOMAINS["v180r7r1_construction_axis_receipt"],
    )
    inner_documents["campaign_scope_structural_boundary"] = (
        terminal_document.get("campaign_scope_structural_boundary"),
        "campaign_scope_structural_boundary_id",
        V180R12R2_INNER_DOMAINS["campaign_scope_structural_boundary"],
    )
    if set(inner_documents) != set(INNER_CONTENT_ID_OPERATION_SUFFIXES):
        _fail("inner content-ID population changed before hashing")
    inner_results: list[tuple[str, str]] = []
    inner_validity: list[bool] = []
    for offset, suffix in enumerate(INNER_CONTENT_ID_OPERATION_SUFFIXES, start=6):
        document, identity_field, domain = inner_documents[suffix]
        if type(document) is not dict:
            _fail("inner content-ID document is mistyped")
        digest, valid = _domain_hash(
            recorder,
            SEMANTIC_HASH_OPERATION_LABELS[offset],
            domain,
            document,
            identity_field,
        )
        inner_results.append((suffix, digest))
        inner_validity.append(valid)
    for suffix, valid in zip(INNER_CONTENT_ID_OPERATION_SUFFIXES, inner_validity):
        recorder.integrity(
            f"integrity.worker_inner_content_id.{suffix}",
            lambda valid=valid: valid,
        )
    recorder.integrity(
        "integrity.worker_inner_content_id.denominator_and_uniqueness",
        lambda: len(inner_results) == 129
        and len({value for _, value in inner_results}) == 129,
    )

    subject_payload = {
        "schema": "acfqp.campaign_measurement_subject_result.v180r12r3",
        "schema_version": SCHEMA_VERSION,
        "scope": "FRESH_PRODUCER_FREE_POST_OUTCOME_EVIDENCE_REPLAY_SUCCESSOR",
        "terminal_content_id": terminal_id,
        "terminal_byte_count": len(terminal_bytes),
        "terminal_sha256": staged_terminal_sha,
        "verification_content_id": verification_id,
        "verification_byte_count": len(verification_bytes),
        "verification_sha256": staged_verification_sha,
        "inner_content_ids": [
            {"label": label, "content_id": value}
            for label, value in inner_results
        ],
        "inner_content_id_count": 129,
        "semantic_hash_operation_count": SEMANTIC_HASH_OPERATION_COUNT,
        "integrity_check_operation_count": INTEGRITY_CHECK_OPERATION_COUNT,
        "protocol_check_operation_count": PROTOCOL_CHECK_OPERATION_COUNT,
        "route_component_counter_closure_status": "PASS",
        "exact_v180r12r2_verification_replayed": True,
        "producer_module_imported": False,
        "producer_entrypoint_called": False,
        "v180r12r2_verifier_imported": False,
        "v180r12r2_verifier_called": False,
        "retroactive_v180r12r2_cost_claimed": False,
        "counter_completeness_gate": "PENDING_INDEPENDENT_REPLAY",
        "workload_economics_gate": "NOT_RUN",
        "scalar_calibration_gate": "NOT_RUN",
        "break_even_gate": "NOT_RUN",
        "official_execution_gate": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    # The subject byte denominator is part of the subject evidence but does not
    # create a hash cycle: the content ID has a fixed 64-byte representation,
    # so canonical-size stabilization is computed with a fixed-width placeholder
    # before the single registered SUBJECT_CONTENT_ID hash operation.
    subject_payload["subject_byte_count"] = 0
    for _ in range(4):
        projected = {
            **subject_payload,
            "subject_result_id": "0" * 64,
        }
        projected_size = len(canonical_json_bytes(projected))
        if subject_payload["subject_byte_count"] == projected_size:
            break
        subject_payload["subject_byte_count"] = projected_size
    else:
        _fail("WORKER subject byte-count fixed point did not stabilize")
    subject_id = recorder.hash_bytes(
        "hash.subject_result_id",
        domains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3E_DOMAIN.encode(
            "utf-8"
        )
        + b"\x00"
        + canonical_json_bytes(subject_payload),
    )
    subject_document = {**subject_payload, "subject_result_id": subject_id}
    subject_bytes = canonical_json_bytes(subject_document)
    recorder.integrity(
        "integrity.worker_subject.canonical_json_and_content_id",
        lambda: canonical_json_bytes(subject_document) == subject_bytes
        and subject_document["subject_result_id"] == subject_id
        and len(subject_bytes) == subject_document["subject_byte_count"],
    )

    source_rows = terminal_document.get("source_verification_receipts")
    route_rows = terminal_document.get("route_component_chain_receipts")
    terminal_rows = terminal_document.get("terminal_receipts")
    shared_rows = terminal_document.get("terminal_shared_resource_receipt_sets")
    construction = terminal_document.get("v180r7r1_construction_axis_receipt")
    structural = terminal_document.get("campaign_scope_structural_boundary")
    protocol_conditions = (
        set(terminal_document) == set(contract.terminal_keyset),
        set(verification_document) == set(contract.verification_keyset),
        terminal_document.get("aggregation_protocol_id")
        == verification_document.get("aggregation_protocol_id")
        == contract.aggregation_protocol_id
        and terminal_document.get("execution_authorization_id")
        == verification_document.get("execution_authorization_id")
        == contract.execution_authorization_id
        and verification_document.get("production_aggregation_bundle_id")
        == terminal_id,
        type(source_rows) is list
        and tuple(row.get("source_kind") for row in source_rows)
        == contract.source_kinds,
        terminal_document.get("ordered_route_components")
        == [
            {"route_kind": route, "terminal_code": code}
            for code, route in contract.route_components
        ]
        and type(route_rows) is list
        and tuple((row.get("terminal_code"), row.get("route_kind")) for row in route_rows)
        == contract.route_components,
        terminal_document.get("ordered_terminal_codes") == list(contract.terminal_codes)
        and type(terminal_rows) is list
        and tuple(row.get("terminal_code") for row in terminal_rows)
        == contract.terminal_codes,
        type(shared_rows) is list
        and tuple(row.get("terminal_code") for row in shared_rows)
        == contract.terminal_codes
        and all(
            type(row.get("receipts")) is list
            and tuple(receipt.get("path") for receipt in row["receipts"])
            == _SHARED_RESOURCE_PATHS
            and row.get("terminal_shared_resource_receipt_ids")
            == [
                receipt.get("terminal_shared_resource_receipt_id")
                for receipt in row["receipts"]
            ]
            for row in shared_rows
        ),
        type(construction) is dict
        and construction.get("one_time_construction_axis") is True
        and construction.get("construction_axis_replayed_separately") is True
        and construction.get("charged_to_any_route_component") is False
        and construction.get("occurrence_route_counter_record_count") == 0,
        type(structural) is dict
        and structural.get("structural_declaration_count") == 9
        and structural.get("actual_counter_record_count") == 0
        and structural.get("actual_work_vector_present") is False
        and structural.get("actual_comparison_vector_present") is False
        and structural.get("actual_projection_proof_present") is False
        and structural.get("actual_native_zero_attestation_present") is False
        and structural.get("structural_boundary_only") is True
        and structural.get("scientific_success_claimed") is False
        and not _contains_key(structural, "route_kind"),
        verification_document.get("aggregation_byte_count") == len(terminal_bytes)
        and verification_document.get("aggregation_sha256") == staged_terminal_sha,
        all(
            terminal_document.get(key) == value
            and verification_document.get(key) == value
            for key, value in _COMMON_DENOMINATORS.items()
        ),
        terminal_document.get("route_component_counter_closure_status")
        == "PENDING_INDEPENDENT_REPLAY"
        and verification_document.get("route_component_counter_closure_status")
        == "PASS",
        all(
            terminal_document.get(gate) == "NOT_RUN"
            and verification_document.get(gate) == "NOT_RUN"
            for gate in (
                "COUNTER_COMPLETENESS_GATE", "WORKLOAD_ECONOMICS_GATE",
                "SCALAR_CALIBRATION_GATE", "BREAK_EVEN_GATE",
            )
        )
        and terminal_document.get("COUNTER_COMPLETENESS_BLOCKER")
        == verification_document.get("COUNTER_COMPLETENESS_BLOCKER")
        == "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
        and terminal_document.get("official_execution_allowed") is False
        and verification_document.get("official_execution_allowed") is False,
        verification_document.get("producer_module_imported") is False
        and verification_document.get("v180r12r3_actual_campaign_measurement_ledger_required")
        is True
        and subject_document.get("retroactive_v180r12r2_cost_claimed") is False
        and subject_document.get("producer_module_imported") is False
        and subject_document.get("v180r12r2_verifier_imported") is False,
        set(subject_document)
        == {
            "schema", "schema_version", "scope", "terminal_content_id",
            "terminal_byte_count", "terminal_sha256", "verification_content_id",
            "verification_byte_count", "verification_sha256", "inner_content_ids",
            "inner_content_id_count", "semantic_hash_operation_count",
            "integrity_check_operation_count", "protocol_check_operation_count",
            "route_component_counter_closure_status", "producer_module_imported",
            "exact_v180r12r2_verification_replayed",
            "producer_entrypoint_called", "v180r12r2_verifier_imported",
            "v180r12r2_verifier_called", "retroactive_v180r12r2_cost_claimed",
            "counter_completeness_gate", "workload_economics_gate",
            "scalar_calibration_gate", "break_even_gate",
            "official_execution_gate",
            "official_scalar_cost", "official_N_break_even",
            "official_execution_allowed", "subject_result_id",
            "subject_byte_count",
        }
        and subject_document.get("counter_completeness_gate")
        == "PENDING_INDEPENDENT_REPLAY"
        and subject_document.get("workload_economics_gate") == "NOT_RUN"
        and subject_document.get("scalar_calibration_gate") == "NOT_RUN"
        and subject_document.get("break_even_gate") == "NOT_RUN"
        and subject_document.get("official_execution_gate") == "NOT_RUN"
        and subject_document.get("official_scalar_cost") is None
        and subject_document.get("official_N_break_even") is None
        and subject_document.get("official_execution_allowed") is False,
    )
    for label, condition in zip(PROTOCOL_CHECK_OPERATION_LABELS, protocol_conditions):
        recorder.protocol(label, lambda condition=condition: condition)

    observation = subject_readback(subject_bytes)
    if type(observation) is not SubjectReadbackObservationV180R12R3:
        _fail("subject readback callback returned a foreign observation")
    readback_sha = recorder.hash_bytes(
        "hash.subject_readback_sha256", observation.returned_bytes
    )
    recorder.integrity(
        "integrity.commit_subject.readback_size_and_sha256",
        lambda: len(observation.returned_bytes) == len(subject_bytes)
        and type(readback_sha) is str
        and observation.returned_bytes == subject_bytes,
    )
    recorder.integrity(
        "integrity.commit_subject.stable_mode_and_nlink",
        lambda: observation.mode == 0o400 and observation.link_count == 1,
    )
    return ProducerFreeReplayComputationV180R12R3(
        subject_bytes,
        subject_id,
        tuple(inner_results),
        tuple(recorder.hash_results),
        tuple(recorder.integrity_results),
        tuple(recorder.protocol_results),
    )


def replay_exact_v180r12r2_evidence_successor_v180r12r3(
    terminal_bytes: bytes,
    verification_bytes: bytes,
    *,
    terminal_stage_receipt: MemfdStageReceiptV180R12R3,
    verification_stage_receipt: MemfdStageReceiptV180R12R3,
    subject_readback: Callable[[bytes], SubjectReadbackObservationV180R12R3],
    operation_observer: OperationObserverV180R12R3 | None = None,
) -> ProducerFreeReplayComputationV180R12R3:
    """Reject the obsolete monolithic call surface.

    Stage, worker, and commit operations have different process owners.  A
    monolithic call would make their phase/actor labels untrue, so production
    must use the three split functions and the explicit join below.
    """

    del (
        terminal_bytes,
        verification_bytes,
        terminal_stage_receipt,
        verification_stage_receipt,
        subject_readback,
        operation_observer,
    )
    _fail(
        "monolithic replay is forbidden; use STAGE, WORKER, COMMIT, then join"
    )


@dataclass(frozen=True, slots=True)
class StageMeasurementResultV180R12R3:
    contract: ProducerFreeReplayContractV180R12R3
    terminal_bytes: bytes = field(repr=False, compare=False)
    verification_bytes: bytes = field(repr=False, compare=False)
    terminal_document: Mapping[str, Any] = field(repr=False, compare=False)
    verification_document: Mapping[str, Any] = field(repr=False, compare=False)
    terminal_source_sha256: str
    verification_source_sha256: str
    terminal_stage_receipt: MemfdStageReceiptV180R12R3
    verification_stage_receipt: MemfdStageReceiptV180R12R3
    hash_results: tuple[ReplayOperationResultV180R12R3, ...]
    integrity_results: tuple[ReplayOperationResultV180R12R3, ...]

    def __post_init__(self) -> None:
        if (
            type(self.contract) is not ProducerFreeReplayContractV180R12R3
            or type(self.terminal_bytes) is not bytes
            or type(self.verification_bytes) is not bytes
            or type(self.terminal_document) is not dict
            or type(self.verification_document) is not dict
            or type(self.terminal_stage_receipt) is not MemfdStageReceiptV180R12R3
            or type(self.verification_stage_receipt) is not MemfdStageReceiptV180R12R3
            or tuple(row.label for row in self.hash_results)
            != SEMANTIC_HASH_OPERATION_LABELS[:2]
            or tuple(row.label for row in self.integrity_results)
            != INTEGRITY_CHECK_OPERATION_LABELS[:6]
        ):
            _fail("STAGE measurement result is malformed")
        _cid(self.terminal_source_sha256, "STAGE terminal source SHA-256")
        _cid(self.verification_source_sha256, "STAGE verification source SHA-256")


@dataclass(frozen=True, slots=True)
class ReplayExecutionContextV180R12R3:
    protocol_id: str
    authorization_id: str
    authorization_evidence_id: str
    attempt_id: str
    campaign_attempt_record_id: str
    execution_slot_id: str
    execution_nonce: str
    logical_occurrence_id: str
    prelaunch_materialization_terminal_id: str
    prelaunch_launch_manifest_sha256: str
    prelaunch_launch_rule_id: str
    measurement_launch_attempt_id: str
    terminal_snapshot_id: str
    verification_snapshot_id: str
    open_visibility_receipt_ids: tuple[str, str]
    worker_birth_receipt_id: str
    operation_manifest_id: str
    native_zero_source_manifest_id: str
    native_zero_import_inventory_id: str

    def __post_init__(self) -> None:
        values = (
            self.protocol_id,
            self.authorization_id,
            self.authorization_evidence_id,
            self.attempt_id,
            self.campaign_attempt_record_id,
            self.execution_slot_id,
            self.execution_nonce,
            self.logical_occurrence_id,
            self.prelaunch_materialization_terminal_id,
            self.prelaunch_launch_manifest_sha256,
            self.prelaunch_launch_rule_id,
            self.measurement_launch_attempt_id,
            self.terminal_snapshot_id,
            self.verification_snapshot_id,
            *self.open_visibility_receipt_ids,
            self.worker_birth_receipt_id,
            self.operation_manifest_id,
            self.native_zero_source_manifest_id,
            self.native_zero_import_inventory_id,
        )
        if (
            type(self.open_visibility_receipt_ids) is not tuple
            or len(self.open_visibility_receipt_ids) != 2
            or len(set(self.open_visibility_receipt_ids)) != 2
        ):
            _fail("replay execution context requires two distinct visibility IDs")
        for value in values:
            _cid(value, "replay execution context ID")


@dataclass(frozen=True, slots=True)
class WorkerReplayResultV180R12R3:
    stage_result: StageMeasurementResultV180R12R3 = field(repr=False)
    subject_bytes: bytes = field(repr=False, compare=False)
    subject_id: str
    inner_content_ids: tuple[tuple[str, str], ...]
    hash_results: tuple[ReplayOperationResultV180R12R3, ...]
    integrity_results: tuple[ReplayOperationResultV180R12R3, ...]
    protocol_results: tuple[ReplayOperationResultV180R12R3, ...]

    def __post_init__(self) -> None:
        if (
            type(self.stage_result) is not StageMeasurementResultV180R12R3
            or tuple(row.label for row in self.hash_results)
            != SEMANTIC_HASH_OPERATION_LABELS[2:-1]
            or tuple(row.label for row in self.integrity_results)
            != INTEGRITY_CHECK_OPERATION_LABELS[6:-2]
            or tuple(row.label for row in self.protocol_results)
            != PROTOCOL_CHECK_OPERATION_LABELS
        ):
            _fail("WORKER replay result operation manifest changed")
        subject = _canonical_object(self.subject_bytes, "WORKER subject result")
        if subject.get("subject_result_id") != self.subject_id:
            _fail("WORKER subject result ID join changed")
        _cid(self.subject_id, "WORKER subject result ID")
        if (
            tuple(label for label, _ in self.inner_content_ids)
            != INNER_CONTENT_ID_OPERATION_SUFFIXES
            or len({value for _, value in self.inner_content_ids}) != 129
        ):
            _fail("WORKER inner content-ID result changed")


@dataclass(frozen=True, slots=True)
class CommitMeasurementResultV180R12R3:
    worker_result: WorkerReplayResultV180R12R3 = field(repr=False)
    readback_observation: SubjectReadbackObservationV180R12R3 = field(
        repr=False, compare=False
    )
    hash_results: tuple[ReplayOperationResultV180R12R3, ...]
    integrity_results: tuple[ReplayOperationResultV180R12R3, ...]

    def __post_init__(self) -> None:
        if (
            type(self.worker_result) is not WorkerReplayResultV180R12R3
            or type(self.readback_observation)
            is not SubjectReadbackObservationV180R12R3
            or tuple(row.label for row in self.hash_results)
            != SEMANTIC_HASH_OPERATION_LABELS[-1:]
            or tuple(row.label for row in self.integrity_results)
            != INTEGRITY_CHECK_OPERATION_LABELS[-2:]
        ):
            _fail("COMMIT measurement result operation manifest changed")


def measure_campaign_inputs_stage_v180r12r3(
    terminal_bytes: bytes,
    verification_bytes: bytes,
    *,
    terminal_stage_receipt: MemfdStageReceiptV180R12R3,
    verification_stage_receipt: MemfdStageReceiptV180R12R3,
    contract: ProducerFreeReplayContractV180R12R3 = (
        EXACT_REPLAY_CONTRACT_V180R12R3
    ),
    operation_observer: OperationObserverV180R12R3 | None = None,
) -> StageMeasurementResultV180R12R3:
    """Perform exactly the two hashes and six checks owned by SUPERVISOR/STAGE."""

    if type(contract) is not ProducerFreeReplayContractV180R12R3:
        _fail("STAGE replay contract is mistyped")
    if (
        type(terminal_stage_receipt) is not MemfdStageReceiptV180R12R3
        or type(verification_stage_receipt) is not MemfdStageReceiptV180R12R3
        or terminal_stage_receipt.role is not CampaignInputRoleV180R12R3.TERMINAL
        or verification_stage_receipt.role
        is not CampaignInputRoleV180R12R3.VERIFICATION
    ):
        _fail("STAGE receipts are mistyped or role-crossed")
    recorder = _ReplayOperationRecorderV180R12R3(operation_observer)
    terminal_sha = recorder.hash_bytes(
        SEMANTIC_HASH_OPERATION_LABELS[0], terminal_bytes
    )
    verification_sha = recorder.hash_bytes(
        SEMANTIC_HASH_OPERATION_LABELS[1], verification_bytes
    )
    terminal_document = _canonical_object(terminal_bytes, "STAGE terminal")
    verification_document = _canonical_object(
        verification_bytes, "STAGE verification"
    )
    inputs = (
        (
            "terminal", terminal_bytes, terminal_document, contract.terminal_fact,
            terminal_stage_receipt, terminal_sha,
        ),
        (
            "verification", verification_bytes, verification_document,
            contract.verification_fact, verification_stage_receipt,
            verification_sha,
        ),
    )
    # The canonical event schedule is family-major.  Record both role ordinals
    # for one integrity family before advancing to the next family.
    for name, raw, document, fact, _receipt, _observed_sha in inputs:
        recorder.integrity(
            f"integrity.stage_source.{name}.stable_read",
            lambda raw=raw, document=document, fact=fact: (
                len(raw) == fact.byte_count
                and document.get("schema") == fact.schema
                and document.get(fact.identity_field) == fact.content_id
            ),
        )
    for name, _raw, _document, fact, receipt, observed_sha in inputs:
        recorder.integrity(
            f"integrity.stage_source.{name}.sha256",
            lambda fact=fact, receipt=receipt, observed_sha=observed_sha: (
                observed_sha == fact.sha256
                and receipt.sha256 == observed_sha
                and receipt.byte_count == fact.byte_count
            ),
        )
    for name, _raw, _document, _fact, receipt, _observed_sha in inputs:
        recorder.integrity(
            f"integrity.stage_source.{name}.memfd_seals",
            lambda receipt=receipt: receipt.observed_seals == REQUIRED_MEMFD_SEALS,
        )
    return StageMeasurementResultV180R12R3(
        contract,
        terminal_bytes,
        verification_bytes,
        terminal_document,
        verification_document,
        terminal_sha,
        verification_sha,
        terminal_stage_receipt,
        verification_stage_receipt,
        tuple(recorder.hash_results),
        tuple(recorder.integrity_results),
    )


def replay_campaign_subject_worker_v180r12r3(
    stage_result: StageMeasurementResultV180R12R3,
    *,
    execution_context: ReplayExecutionContextV180R12R3,
    operation_observer: OperationObserverV180R12R3 | None = None,
) -> WorkerReplayResultV180R12R3:
    """Perform only the 134/137/15 operations owned by the WORKER process."""

    if (
        type(stage_result) is not StageMeasurementResultV180R12R3
        or type(execution_context) is not ReplayExecutionContextV180R12R3
    ):
        _fail("WORKER requires exact STAGE and execution-context inputs")
    contract = stage_result.contract
    terminal_bytes = stage_result.terminal_bytes
    verification_bytes = stage_result.verification_bytes
    terminal_document = dict(stage_result.terminal_document)
    verification_document = dict(stage_result.verification_document)
    recorder = _ReplayOperationRecorderV180R12R3(operation_observer)
    staged_terminal_sha = recorder.hash_bytes(
        SEMANTIC_HASH_OPERATION_LABELS[2], terminal_bytes
    )
    staged_verification_sha = recorder.hash_bytes(
        SEMANTIC_HASH_OPERATION_LABELS[3], verification_bytes
    )
    terminal_id, terminal_id_valid = _domain_hash(
        recorder,
        SEMANTIC_HASH_OPERATION_LABELS[4],
        V180R12R2_TERMINAL_DOMAIN,
        terminal_document,
        contract.terminal_fact.identity_field,
    )
    verification_id, verification_id_valid = _domain_hash(
        recorder,
        SEMANTIC_HASH_OPERATION_LABELS[5],
        V180R12R2_VERIFICATION_DOMAIN,
        verification_document,
        contract.verification_fact.identity_field,
    )
    inner_documents: dict[str, tuple[dict[str, Any], str, str]] = {}
    source_rows = terminal_document.get("source_verification_receipts")
    route_rows = terminal_document.get("route_component_chain_receipts")
    terminal_rows = terminal_document.get("terminal_receipts")
    shared_rows = terminal_document.get("terminal_shared_resource_receipt_sets")
    if not all(type(rows) is list for rows in (source_rows, route_rows, terminal_rows, shared_rows)):
        _fail("WORKER retained populations are not exact lists")
    for index, row in enumerate(source_rows):
        inner_documents[f"source_receipt.{index:02d}"] = (
            row, "source_receipt_id", V180R12R2_INNER_DOMAINS["source_receipt"]
        )
    for index, row in enumerate(route_rows):
        inner_documents[f"route_component_chain_receipt.{index:02d}"] = (
            row,
            "route_component_chain_receipt_id",
            V180R12R2_INNER_DOMAINS["route_component_chain_receipt"],
        )
    for index, row in enumerate(terminal_rows):
        inner_documents[f"terminal_receipt.{index:02d}"] = (
            row, "terminal_chain_receipt_id", V180R12R2_INNER_DOMAINS["terminal_receipt"]
        )
    shared_index = 0
    for set_index, receipt_set in enumerate(shared_rows):
        if type(receipt_set) is not dict or type(receipt_set.get("receipts")) is not list:
            _fail("WORKER shared-resource receipt set is malformed")
        for receipt in receipt_set["receipts"]:
            inner_documents[
                f"terminal_shared_resource_receipt.{shared_index:03d}"
            ] = (
                receipt,
                "terminal_shared_resource_receipt_id",
                V180R12R2_INNER_DOMAINS["terminal_shared_resource_receipt"],
            )
            shared_index += 1
        inner_documents[f"terminal_shared_resource_receipt_set.{set_index:02d}"] = (
            receipt_set,
            "terminal_shared_resource_receipt_set_id",
            V180R12R2_INNER_DOMAINS["terminal_shared_resource_receipt_set"],
        )
    construction = terminal_document.get("v180r7r1_construction_axis_receipt")
    structural = terminal_document.get("campaign_scope_structural_boundary")
    inner_documents["v180r7r1_construction_axis_receipt"] = (
        construction,
        "v180r7r1_construction_axis_receipt_id",
        V180R12R2_INNER_DOMAINS["v180r7r1_construction_axis_receipt"],
    )
    inner_documents["campaign_scope_structural_boundary"] = (
        structural,
        "campaign_scope_structural_boundary_id",
        V180R12R2_INNER_DOMAINS["campaign_scope_structural_boundary"],
    )
    if set(inner_documents) != set(INNER_CONTENT_ID_OPERATION_SUFFIXES):
        _fail("WORKER inner content-ID denominator changed before hashing")
    inner_results: list[tuple[str, str]] = []
    inner_validity: list[bool] = []
    for offset, suffix in enumerate(INNER_CONTENT_ID_OPERATION_SUFFIXES, start=6):
        document, identity_field, domain = inner_documents[suffix]
        if type(document) is not dict:
            _fail("WORKER inner content-ID document is mistyped")
        digest, valid = _domain_hash(
            recorder,
            SEMANTIC_HASH_OPERATION_LABELS[offset],
            domain,
            document,
            identity_field,
        )
        inner_results.append((suffix, digest))
        inner_validity.append(valid)
    subject_payload = {
        "schema": "acfqp.campaign_measurement_subject_result.v180r12r3",
        "schema_version": SCHEMA_VERSION,
        "scope": "FRESH_PRODUCER_FREE_POST_OUTCOME_EVIDENCE_REPLAY_SUCCESSOR",
        "protocol_id": execution_context.protocol_id,
        "authorization_id": execution_context.authorization_id,
        "authorization_evidence_id": execution_context.authorization_evidence_id,
        "attempt_id": execution_context.attempt_id,
        "campaign_attempt_record_id": execution_context.campaign_attempt_record_id,
        "execution_slot_id": execution_context.execution_slot_id,
        "execution_nonce": execution_context.execution_nonce,
        "logical_occurrence_id": execution_context.logical_occurrence_id,
        "prelaunch_materialization_terminal_id": (
            execution_context.prelaunch_materialization_terminal_id
        ),
        "prelaunch_launch_manifest_sha256": (
            execution_context.prelaunch_launch_manifest_sha256
        ),
        "prelaunch_launch_rule_id": execution_context.prelaunch_launch_rule_id,
        "measurement_launch_attempt_id": (
            execution_context.measurement_launch_attempt_id
        ),
        "terminal_content_id": terminal_id,
        "terminal_byte_count": len(terminal_bytes),
        "terminal_sha256": staged_terminal_sha,
        "verification_content_id": verification_id,
        "verification_byte_count": len(verification_bytes),
        "verification_sha256": staged_verification_sha,
        "terminal_snapshot_id": execution_context.terminal_snapshot_id,
        "verification_snapshot_id": execution_context.verification_snapshot_id,
        "memfd_stage_receipt_ids": [
            stage_result.terminal_stage_receipt.stage_receipt_id,
            stage_result.verification_stage_receipt.stage_receipt_id,
        ],
        "open_visibility_receipt_ids": list(
            execution_context.open_visibility_receipt_ids
        ),
        "worker_birth_receipt_id": execution_context.worker_birth_receipt_id,
        "operation_manifest_id": execution_context.operation_manifest_id,
        "inner_content_ids": [
            {"label": label, "content_id": value}
            for label, value in inner_results
        ],
        "inner_content_id_count": 129,
        "semantic_hash_operation_count": SEMANTIC_HASH_OPERATION_COUNT,
        "integrity_check_operation_count": INTEGRITY_CHECK_OPERATION_COUNT,
        "protocol_check_operation_count": PROTOCOL_CHECK_OPERATION_COUNT,
        "route_component_counter_closure_status": "PASS",
        "exact_v180r12r2_verification_replayed": True,
        "producer_module_imported": False,
        "producer_entrypoint_called": False,
        "v180r12r2_verifier_imported": False,
        "v180r12r2_verifier_called": False,
        "retroactive_v180r12r2_cost_claimed": False,
        "counter_completeness_gate": "PENDING_INDEPENDENT_REPLAY",
        "workload_economics_gate": "NOT_RUN",
        "scalar_calibration_gate": "NOT_RUN",
        "break_even_gate": "NOT_RUN",
        "official_execution_gate": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    subject_payload["subject_byte_count"] = 0
    for _ in range(4):
        projected_size = len(
            canonical_json_bytes(
                {**subject_payload, "subject_result_id": "0" * 64}
            )
        )
        if subject_payload["subject_byte_count"] == projected_size:
            break
        subject_payload["subject_byte_count"] = projected_size
    else:
        _fail("WORKER subject byte-count fixed point did not stabilize")
    subject_domain = getattr(
        domains, "CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R3E_DOMAIN", None
    )
    if type(subject_domain) is not str:
        _fail("campaign subject-result domain is not registered")
    subject_id = recorder.hash_bytes(
        "hash.subject_result_id",
        subject_domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(subject_payload),
    )
    subject_document = {**subject_payload, "subject_result_id": subject_id}
    subject_bytes = canonical_json_bytes(subject_document)

    # The shared expanded authority groups all 134 WORKER hashes before the
    # 137 integrity checks.  Conditions are retained as immutable local facts
    # and only recorded after the last registered hash operation.
    recorder.integrity(
        "integrity.worker_staged.terminal.sha256",
        lambda: staged_terminal_sha == stage_result.terminal_source_sha256,
    )
    recorder.integrity(
        "integrity.worker_staged.verification.sha256",
        lambda: staged_verification_sha
        == stage_result.verification_source_sha256,
    )
    recorder.integrity(
        "integrity.worker_staged.terminal.canonical_json",
        lambda: canonical_json_bytes(terminal_document) == terminal_bytes,
    )
    recorder.integrity(
        "integrity.worker_staged.verification.canonical_json",
        lambda: canonical_json_bytes(verification_document) == verification_bytes,
    )
    recorder.integrity(
        "integrity.worker_staged.terminal.top_content_id",
        lambda: terminal_id_valid and terminal_id == contract.terminal_fact.content_id,
    )
    recorder.integrity(
        "integrity.worker_staged.verification.top_content_id",
        lambda: verification_id_valid
        and verification_id == contract.verification_fact.content_id,
    )
    for suffix, valid in zip(INNER_CONTENT_ID_OPERATION_SUFFIXES, inner_validity):
        recorder.integrity(
            f"integrity.worker_inner_content_id.{suffix}",
            lambda valid=valid: valid,
        )
    recorder.integrity(
        "integrity.worker_inner_content_id.denominator_and_uniqueness",
        lambda: len(inner_results) == 129
        and len({value for _, value in inner_results}) == 129,
    )
    recorder.integrity(
        "integrity.worker_subject.canonical_json_and_content_id",
        lambda: canonical_json_bytes(subject_document) == subject_bytes
        and subject_document["subject_result_id"] == subject_id
        and len(subject_bytes) == subject_document["subject_byte_count"],
    )

    terminal_true_fields = (
        "all_five_source_independent_verifiers_replayed",
        "all_ten_occurrence_shared_resource_receipt_sets_present",
        "all_twelve_route_component_chains_present",
    )
    protocol_conditions = (
        terminal_document.get("schema") == TERMINAL_SCHEMA
        and set(terminal_document) == set(contract.terminal_keyset),
        verification_document.get("schema") == VERIFICATION_SCHEMA
        and set(verification_document) == set(contract.verification_keyset),
        terminal_document.get("aggregation_protocol_id")
        == verification_document.get("aggregation_protocol_id")
        == contract.aggregation_protocol_id
        and terminal_document.get("execution_authorization_id")
        == verification_document.get("execution_authorization_id")
        == contract.execution_authorization_id
        and execution_context.protocol_id != contract.aggregation_protocol_id
        and execution_context.authorization_id
        != contract.execution_authorization_id
        and terminal_document.get("production_aggregation_bundle_id") == terminal_id
        and verification_document.get("production_aggregation_bundle_id") == terminal_id
        and verification_document.get("verification_id") == verification_id
        and stage_result.terminal_stage_receipt.input_snapshot_id
        == execution_context.terminal_snapshot_id
        and stage_result.verification_stage_receipt.input_snapshot_id
        == execution_context.verification_snapshot_id,
        tuple(row.get("source_kind") for row in source_rows) == contract.source_kinds
        and len({row.get("source_receipt_id") for row in source_rows}) == 5,
        terminal_document.get("ordered_route_components")
        == [
            {"route_kind": route, "terminal_code": code}
            for code, route in contract.route_components
        ]
        and tuple((row.get("terminal_code"), row.get("route_kind")) for row in route_rows)
        == contract.route_components
        and all(
            row.get("counter_record_count") == 269
            and row.get("counter_record_to_work_vector_to_comparison_vector_replayed")
            is True
            and row.get("independent_route_component") is True
            for row in route_rows
        ),
        terminal_document.get("ordered_terminal_codes") == list(contract.terminal_codes)
        and tuple(row.get("terminal_code") for row in terminal_rows)
        == contract.terminal_codes,
        tuple(row.get("terminal_code") for row in shared_rows)
        == contract.terminal_codes
        and all(
            row.get("receipt_count") == 9
            and row.get("all_nine_paths_present") is True
            and row.get("missing_path_inferred_zero") is False
            and tuple(receipt.get("path") for receipt in row["receipts"])
            == _SHARED_RESOURCE_PATHS
            and row.get("terminal_shared_resource_receipt_ids")
            == [
                receipt.get("terminal_shared_resource_receipt_id")
                for receipt in row["receipts"]
            ]
            for row in shared_rows
        ),
        type(construction) is dict
        and construction.get("one_time_construction_axis") is True
        and construction.get("construction_axis_replayed_separately") is True
        and construction.get("charged_to_any_route_component") is False
        and construction.get("occurrence_route_counter_record_count") == 0,
        type(structural) is dict
        and structural.get("structural_declaration_count") == 9
        and structural.get("actual_counter_record_count") == 0
        and structural.get("actual_work_vector_present") is False
        and structural.get("actual_comparison_vector_present") is False
        and structural.get("actual_projection_proof_present") is False
        and structural.get("actual_native_zero_attestation_present") is False
        and structural.get("authoritative_receipt_total") == 90
        and structural.get("campaign_scope_authoritative_receipt_count") == 0
        and structural.get("structural_boundary_only") is True
        and structural.get("scientific_success_claimed") is False
        and not _contains_key(structural, "route_kind"),
        verification_document.get("aggregation_byte_count") == len(terminal_bytes)
        and verification_document.get("aggregation_sha256") == staged_terminal_sha,
        all(
            terminal_document.get(key) == value
            and verification_document.get(key) == value
            for key, value in _COMMON_DENOMINATORS.items()
        ),
        terminal_document.get("route_component_counter_closure_status")
        == "PENDING_INDEPENDENT_REPLAY"
        and verification_document.get("route_component_counter_closure_status")
        == "PASS"
        and all(
            verification_document.get(key) is True
            for key in VERIFICATION_REQUIRED_TRUE_FIELDS
        ),
        all(
            terminal_document.get(gate) == "NOT_RUN"
            and verification_document.get(gate) == "NOT_RUN"
            for gate in (
                "COUNTER_COMPLETENESS_GATE", "WORKLOAD_ECONOMICS_GATE",
                "SCALAR_CALIBRATION_GATE", "BREAK_EVEN_GATE",
            )
        )
        and terminal_document.get("COUNTER_COMPLETENESS_BLOCKER")
        == verification_document.get("COUNTER_COMPLETENESS_BLOCKER")
        == "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
        and all(
            terminal_document.get(key) is None
            and verification_document.get(key) is None
            for key in ("official_scalar_cost", "official_N_break_even")
        )
        and terminal_document.get("official_execution_allowed") is False
        and verification_document.get("official_execution_allowed") is False,
        verification_document.get("producer_module_imported") is False
        and verification_document.get("v180r12r3_actual_campaign_measurement_ledger_required")
        is True
        and terminal_document.get("historical_summary_translation_used") is False
        and verification_document.get("historical_summary_translation_used") is False
        and terminal_document.get("v180r7r1_construction_work_charged_to_route_components")
        is False
        and verification_document.get("v180r7r1_construction_work_charged_to_route_components")
        is False
        and all(terminal_document.get(key) is True for key in terminal_true_fields)
        and terminal_document.get("producer_bundle_independently_replayed") is False
        and subject_document.get("retroactive_v180r12r2_cost_claimed") is False
        and subject_document.get("producer_module_imported") is False
        and subject_document.get("producer_entrypoint_called") is False
        and subject_document.get("v180r12r2_verifier_imported") is False
        and subject_document.get("v180r12r2_verifier_called") is False,
        set(subject_document) == CAMPAIGN_SUBJECT_RESULT_FIELD_KEYSET
        and subject_document.get("campaign_attempt_record_id")
        == execution_context.campaign_attempt_record_id
        and subject_document.get("counter_completeness_gate")
        == "PENDING_INDEPENDENT_REPLAY"
        and subject_document.get("workload_economics_gate") == "NOT_RUN"
        and subject_document.get("scalar_calibration_gate") == "NOT_RUN"
        and subject_document.get("break_even_gate") == "NOT_RUN"
        and subject_document.get("official_execution_gate") == "NOT_RUN"
        and subject_document.get("official_scalar_cost") is None
        and subject_document.get("official_N_break_even") is None
        and subject_document.get("official_execution_allowed") is False,
    )
    for label, condition in zip(PROTOCOL_CHECK_OPERATION_LABELS, protocol_conditions):
        recorder.protocol(label, lambda condition=condition: condition)
    return WorkerReplayResultV180R12R3(
        stage_result,
        subject_bytes,
        subject_id,
        tuple(inner_results),
        tuple(recorder.hash_results),
        tuple(recorder.integrity_results),
        tuple(recorder.protocol_results),
    )


def measure_subject_commit_v180r12r3(
    worker_result: WorkerReplayResultV180R12R3,
    *,
    subject_readback: Callable[[bytes], SubjectReadbackObservationV180R12R3],
    operation_observer: OperationObserverV180R12R3 | None = None,
) -> CommitMeasurementResultV180R12R3:
    """Perform exactly the one hash and two checks owned by SUPERVISOR/COMMIT."""

    if type(worker_result) is not WorkerReplayResultV180R12R3 or not callable(
        subject_readback
    ):
        _fail("COMMIT requires one WORKER result and one readback callback")
    observation = subject_readback(worker_result.subject_bytes)
    if type(observation) is not SubjectReadbackObservationV180R12R3:
        _fail("COMMIT readback callback returned a foreign observation")
    recorder = _ReplayOperationRecorderV180R12R3(operation_observer)
    readback_sha = recorder.hash_bytes(
        "hash.subject_readback_sha256", observation.returned_bytes
    )
    recorder.integrity(
        "integrity.commit_subject.readback_size_and_sha256",
        lambda: len(observation.returned_bytes) == len(worker_result.subject_bytes)
        and type(readback_sha) is str
        and observation.returned_bytes == worker_result.subject_bytes,
    )
    recorder.integrity(
        "integrity.commit_subject.stable_mode_and_nlink",
        lambda: observation.mode == 0o400 and observation.link_count == 1,
    )
    return CommitMeasurementResultV180R12R3(
        worker_result,
        observation,
        tuple(recorder.hash_results),
        tuple(recorder.integrity_results),
    )


def join_campaign_replay_measurements_v180r12r3(
    stage_result: StageMeasurementResultV180R12R3,
    worker_result: WorkerReplayResultV180R12R3,
    commit_result: CommitMeasurementResultV180R12R3,
) -> ProducerFreeReplayComputationV180R12R3:
    """Join three role-native results without running another semantic operation."""

    if not (
        type(stage_result) is StageMeasurementResultV180R12R3
        and type(worker_result) is WorkerReplayResultV180R12R3
        and type(commit_result) is CommitMeasurementResultV180R12R3
        and worker_result.stage_result is stage_result
        and commit_result.worker_result is worker_result
    ):
        _fail("STAGE/WORKER/COMMIT replay result join crossed attempts")
    hash_results = (
        stage_result.hash_results
        + worker_result.hash_results
        + commit_result.hash_results
    )
    integrity_results = (
        stage_result.integrity_results
        + worker_result.integrity_results
        + commit_result.integrity_results
    )
    return ProducerFreeReplayComputationV180R12R3(
        worker_result.subject_bytes,
        worker_result.subject_id,
        worker_result.inner_content_ids,
        hash_results,
        integrity_results,
        worker_result.protocol_results,
    )


def worker_contract_v180r12r3() -> dict[str, Any]:
    """Return the outcome-free worker contract for protocol preregistration."""

    return {
        "schema": "acfqp.campaign_measurement_worker_contract.v180r12r3",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_input_facts": [
            fact.to_document() for fact in FROZEN_INPUT_FACTS_V180R12R3
        ],
        "input_count": 2,
        "input_total_byte_count": EXPECTED_TOTAL_INPUT_BYTES,
        "memfd_stage_count": 2,
        "required_memfd_seals": list(REQUIRED_MEMFD_SEALS),
        "open_visibility_receipt_count": 2,
        "closed_visibility_receipt_count": 2,
        "semantic_hash_operation_count": SEMANTIC_HASH_OPERATION_COUNT,
        "integrity_check_operation_count": INTEGRITY_CHECK_OPERATION_COUNT,
        "protocol_check_operation_count": PROTOCOL_CHECK_OPERATION_COUNT,
        "semantic_hash_operation_labels": list(SEMANTIC_HASH_OPERATION_LABELS),
        "integrity_check_operation_labels": list(INTEGRITY_CHECK_OPERATION_LABELS),
        "protocol_check_families": list(PROTOCOL_CHECK_FAMILIES),
        "protocol_check_operation_labels": list(PROTOCOL_CHECK_OPERATION_LABELS),
        "producer_module_import_allowed": False,
        "producer_entrypoint_call_allowed": False,
        "v180r12r2_verifier_execution_allowed": False,
        "preloaded_import_inventory_required": True,
        "attempt_open_and_window_close_import_sets_must_equal": True,
        "late_or_dynamic_import_allowed": False,
        "fresh_producer_free_replay_required": True,
        "retroactive_v180r12r2_cost_claim_allowed": False,
        "filesystem_opener_present": False,
        "process_launcher_present": False,
        "cgroup_mutator_present": False,
        "output_committer_present": False,
    }


__all__ = (
    "CampaignInputRoleV180R12R3",
    "CommitMeasurementResultV180R12R3",
    "ConstructionK7CampaignMeasurementWorkerV180R12R3Error",
    "CAMPAIGN_SUBJECT_RESULT_FIELD_KEYSET",
    "EVIDENCE_DOCUMENT_CONTRACT_ROWS",
    "EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS",
    "EXACT_REPLAY_CONTRACT_V180R12R3",
    "EXPECTED_TOTAL_INPUT_BYTES",
    "FDVisibilityReceiptV180R12R3",
    "FROZEN_INPUT_FACTS_V180R12R3",
    "INTEGRITY_CHECK_OPERATION_COUNT",
    "INTEGRITY_CHECK_OPERATION_LABELS",
    "INNER_CONTENT_ID_OPERATION_SUFFIXES",
    "MemfdStageReceiptV180R12R3",
    "MeasuredImportClosureV180R12R3",
    "OperationObserverV180R12R3",
    "PROTOCOL_CHECK_OPERATION_COUNT",
    "PROTOCOL_CHECK_FAMILIES",
    "PROTOCOL_CHECK_OPERATION_LABELS",
    "ProducerFreeReplayComputationV180R12R3",
    "ProducerFreeReplayContractV180R12R3",
    "ProducerFreeReplaySubjectReceiptV180R12R3",
    "REQUIRED_MEMFD_SEALS",
    "ReplayExecutionContextV180R12R3",
    "ReplayOperationResultV180R12R3",
    "SEMANTIC_HASH_OPERATION_COUNT",
    "SEMANTIC_HASH_OPERATION_LABELS",
    "SemanticOperationKindV180R12R3",
    "SemanticOperationReceiptV180R12R3",
    "StageMeasurementResultV180R12R3",
    "StableCampaignInputFactV180R12R3",
    "StableInputSnapshotReceiptV180R12R3",
    "SubjectReadbackObservationV180R12R3",
    "VisibilityStateV180R12R3",
    "VERIFICATION_REQUIRED_TRUE_FIELDS",
    "WorkerReplayResultV180R12R3",
    "frozen_campaign_input_facts_v180r12r3",
    "join_campaign_replay_measurements_v180r12r3",
    "materialize_semantic_operation_receipts_v180r12r3",
    "measure_campaign_inputs_stage_v180r12r3",
    "measure_subject_commit_v180r12r3",
    "read_exact_campaign_input_v180r12r3",
    "replay_campaign_subject_worker_v180r12r3",
    "replay_exact_v180r12r2_evidence_successor_v180r12r3",
    "semantic_operation_receipt_v180r12r3",
    "worker_contract_v180r12r3",
)
