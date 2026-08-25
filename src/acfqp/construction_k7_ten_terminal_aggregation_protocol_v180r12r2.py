"""Fresh outcome-free V180r12r2 ten-terminal aggregation protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import (
    construction_k7_ten_terminal_aggregation_stale_predecessor_freeze_v180r12r2
    as stale_predecessor,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


EXPECTED_PROTOCOL_ID = "d15ec6d29ffbb4908e20cabfbbc98f3aa53ec4ad38d1d4681930c3306737c965"
EXPECTED_CANONICAL_BYTE_COUNT = 25_521
EXPECTED_CANONICAL_SHA256 = (
    "7b07940cec679bdd96cc95ed8e7dd92231596f0b1645bdca2acd59404fe6835e"
)
EXPECTED_AGGREGATION_EXECUTION_SLOT_ID = "98d5ba0a9b04cd444a2d5c159cd719f8e7803934f7cbb8ee9b0ce8947a41e46e"

FORMALIZATION_CONTRACT_ID = (
    "f392e9178e8c9c69150567ce210ad146ab96d61aa5925c34b133415fa86737fd"
)
LOGICAL_OCCURRENCE_ID = (
    "8e4abd9ea574f2184a33863989a31b8794fc14424fadbec6f7c4b0d1098b6458"
)
EXECUTION_NONCE = (
    "81c59b1a53762b2430b24fe3880cbc70dff2d85d7c6b7705c40a01345b368d74"
)

SOURCE_GROUP_COUNT = 5
TERMINAL_CODE_COUNT = 10
ROUTE_COMPONENT_CHAIN_COUNT = 12
COUNTER_RECORDS_PER_ROUTE_COMPONENT = 269
LOGICAL_TERMINAL_REPRESENTATIVE_RECORD_COUNT = 2_690
UNIQUE_ROUTE_COMPONENT_RECORD_COUNT = 3_228
EXTRA_NONREPRESENTATIVE_V180R7R1_RECORD_COUNT = 538
SHARED_RESOURCE_RECEIPTS_PER_TERMINAL = 9
TERMINAL_SHARED_RESOURCE_RECEIPT_COUNT = 90
CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT = 9
CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT = 0
CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT = 0
CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT = 0
TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT = 90
COUNTER_COMPLETENESS_BLOCKER = (
    "CAMPAIGN_SCOPE_ACTUAL_MEASUREMENT_LEDGER_ABSENT"
)

# Compatibility aliases retain old import surfaces while carrying the corrected
# actual/authoritative denominators.  They never denote the nine declarations.
CAMPAIGN_SHARED_RESOURCE_RECEIPT_COUNT = (
    CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT
)
TOTAL_SHARED_RESOURCE_RECEIPT_COUNT = (
    TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
)
RETAINED_SOURCE_TOTAL_BYTE_COUNT = 15_496_039
ADDRESS_SPACE_HARD_CAP_BYTES = 16 * 1024 * 1024 * 1024
REJECTED_PREFLIGHT_ADDRESS_SPACE_CAP_BYTES = 6 * 1024 * 1024 * 1024
REJECTED_PREFLIGHT_MAX_RSS_KIB = 6_216_640
REJECTED_PREFLIGHT_ELAPSED_SECONDS = "1908.72"
FINALIZER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT = 7
INDEPENDENT_VERIFIER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT_PER_REPLAY = 10
PRODUCER_RUNNER_PRECAP_HEAP_RELEASE_PHASE_COUNT = 1
PRODUCER_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT = (
    FINALIZER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT
    + PRODUCER_RUNNER_PRECAP_HEAP_RELEASE_PHASE_COUNT
)
VERIFICATION_RUNNER_EXTERNAL_HEAP_RELEASE_PHASE_COUNT = 2
VERIFICATION_REPLAY_COUNT = 2
VERIFICATION_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT = (
    VERIFICATION_REPLAY_COUNT
    * INDEPENDENT_VERIFIER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT_PER_REPLAY
    + VERIFICATION_RUNNER_EXTERNAL_HEAP_RELEASE_PHASE_COUNT
)
TRANSIENT_HEAP_RELEASE_AUTHORITY_CLASS = (
    "PREAUTHORIZATION_MEMORY_LIFECYCLE_STRUCTURAL_OBLIGATION"
)
TRANSIENT_HEAP_RELEASE_ALLOWED_RETURN_STATUSES = (0, 1)
FAILURE_EMERGENCY_RESERVE_BYTES = 4 * 1024 * 1024
FAILURE_MESSAGE_BYTE_CAP = 4_096
FAILURE_TYPE_BYTE_CAP = 128
FAILURE_OBSERVATION_STREAM_BUFFER_BYTES = 1024 * 1024
VERIFICATION_TERMINAL_INPUT_BYTE_CAP = 1024 * 1024 * 1024
PRODUCER_PROGRESS_PATH_COUNT = 6

PRELAUNCH_SOURCE_CLOSURE_RULE_ID = (
    "fe5036863176827c036ab5aef487b8e920896455dc684e44ae7791438dbb408c"
)
PRELAUNCH_MATERIALIZATION_RULE_ID = (
    "79513bd291443fa661c05bc1ff91b6c8f3b8f51dda9aac01073ffec5376abf3d"
)
PRELAUNCH_LAUNCH_RULE_ID = (
    "57e88919b379a3fc2150dcefea46d30488b128832601e31269d225c4de37480b"
)
PRELAUNCH_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r2_ten_terminal_aggregation_prelaunch"
)
PRELAUNCH_EXTERNAL_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_prelaunch_external_root.json"
)
PRELAUNCH_BOOTSTRAP_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/bootstrap.py"
PRELAUNCH_MANIFEST_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/launch_manifest.json"
)
PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MATERIALIZATION_TERMINAL.json"
)
PRELAUNCH_MATERIALIZATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_prelaunch_failure.json"
)
PRELAUNCH_PRODUCTION_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/PRODUCTION_LAUNCH_RECEIPT.json"
)
PRELAUNCH_PRODUCTION_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/PRODUCTION_LAUNCH_ATTEMPT.json"
)
PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_RECEIPT.json"
)
PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_ATTEMPT.json"
)
PRELAUNCH_PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_prelaunch_production_launch_failure.json"
)
PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r2_ten_terminal_aggregation_prelaunch_verification_launch_failure.json"
)


def prelaunch_contract_v180r12r2() -> dict[str, Any]:
    """Return the preregistered prelaunch rules, never an outcome instance."""

    return {
        "schema": "acfqp.v180r12r2_prelaunch_contract.v1",
        "external_root_schema": "acfqp.v180r12r2_prelaunch_external_root.v1",
        "launch_manifest_schema": (
            "acfqp.v180r12r2_source_bound_launch_manifest.v1"
        ),
        "materialization_terminal_schema": (
            "acfqp.v180r12r2_prelaunch_materialization_terminal.v1"
        ),
        "materialization_failure_schema": (
            "acfqp.v180r12r2_prelaunch_materialization_failure.v1"
        ),
        "launch_receipt_schema": "acfqp.v180r12r2_prelaunch_launch_receipt.v1",
        "launch_failure_schema": "acfqp.v180r12r2_prelaunch_launch_failure.v1",
        "launch_rule_schema": "acfqp.v180r12r2_prelaunch_launch_rule.v1",
        "launch_attempt_schema": "acfqp.v180r12r2_prelaunch_launch_attempt.v1",
        "source_closure_rule_id": PRELAUNCH_SOURCE_CLOSURE_RULE_ID,
        "materialization_rule_id": PRELAUNCH_MATERIALIZATION_RULE_ID,
        "launch_rule_id": PRELAUNCH_LAUNCH_RULE_ID,
        "materializer_relative_path": (
            "scripts/materialize_v180r12r2_ten_terminal_aggregation_prelaunch.py"
        ),
        "source_bootstrap_relative_path": (
            "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py"
        ),
        "source_launcher_relative_path": (
            "scripts/launch_v180r12r2_ten_terminal_aggregation_prelaunch.py"
        ),
        "output_root_relative_path": PRELAUNCH_ROOT_RELATIVE_PATH,
        "external_root_relative_path": PRELAUNCH_EXTERNAL_ROOT_RELATIVE_PATH,
        "bootstrap_relative_path": PRELAUNCH_BOOTSTRAP_RELATIVE_PATH,
        "launcher_relative_path": f"{PRELAUNCH_ROOT_RELATIVE_PATH}/launcher.py",
        "launch_manifest_relative_path": PRELAUNCH_MANIFEST_RELATIVE_PATH,
        "materialization_terminal_relative_path": (
            PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH
        ),
        "materialization_failure_relative_path": (
            PRELAUNCH_MATERIALIZATION_FAILURE_RELATIVE_PATH
        ),
        "production_launch_receipt_relative_path": (
            PRELAUNCH_PRODUCTION_LAUNCH_RECEIPT_RELATIVE_PATH
        ),
        "production_launch_attempt_relative_path": (
            PRELAUNCH_PRODUCTION_LAUNCH_ATTEMPT_RELATIVE_PATH
        ),
        "production_launch_failure_relative_path": (
            PRELAUNCH_PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH
        ),
        "verification_launch_receipt_relative_path": (
            PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH
        ),
        "verification_launch_attempt_relative_path": (
            PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH
        ),
        "verification_launch_failure_relative_path": (
            PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH
        ),
        "external_root_sha256_environment_variable": (
            "ACFQP_V180R12R2_EXTERNAL_ROOT_SHA256"
        ),
        "launch_manifest_sha256_environment_variable": (
            "ACFQP_V180R12R2_LAUNCH_MANIFEST_SHA256"
        ),
        "materialization_terminal_sha256_environment_variable": (
            "ACFQP_V180R12R2_MATERIALIZATION_TERMINAL_SHA256"
        ),
        "prereg_commit_environment_variable": (
            "ACFQP_V180R12R2_PREREG_COMMIT"
        ),
        "python_executable": "/usr/bin/python3",
        "git_executable": "/usr/bin/git",
        "pycache_prefix": "/dev/null/v180r12r2",
        "isolated_python_argv_prefix": [
            "/usr/bin/python3",
            "-I",
            "-S",
            "-B",
            "-X",
            "pycache_prefix=/dev/null/v180r12r2",
        ],
        "outer_launcher_byte_caps": {
            "external_root": 1 * 1024 * 1024,
            "bootstrap": 1 * 1024 * 1024,
            "materializer": 2 * 1024 * 1024,
            "launcher": 1 * 1024 * 1024,
            "launch_manifest": 16 * 1024 * 1024,
            "runner": 4 * 1024 * 1024,
            "source_file": 8 * 1024 * 1024,
            "source_closure_file_count": 4_096,
            "source_closure_total_bytes": 128 * 1024 * 1024,
            "executable": 64 * 1024 * 1024,
            "git_archive": 256 * 1024 * 1024,
            "failure_message": 4_096,
            "child_stdout_or_stderr": 16 * 1024 * 1024,
            "child_stream_retained_prefix": 4_096,
            "stream_buffer": 1 * 1024 * 1024,
            "launch_artifact": 16 * 1024 * 1024,
            "scientific_artifact_observation": 1024 * 1024 * 1024,
        },
        "git_command_timeout_seconds": 120,
        "git_process_schedule_count": 6,
        "launch_wall_timeout_seconds": 14_400,
        "launch_termination_grace_seconds": 10,
        "whole_child_address_space_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "whole_child_address_space_cap_mechanism": (
            "RLIMIT_AS_IN_CHILD_PREEXEC_BEFORE_BOOTSTRAP_EXEC"
        ),
        "whole_child_wall_timeout_mechanism": (
            "OUTER_MONOTONIC_WATCHDOG_PROCESS_GROUP"
        ),
        "source_chain_rule": (
            "EXTERNAL_ROOT_EXACT_C_PRE_TO_EMPTY_SAME_TREE_BRIDGE_TO_"
            "WRAPPER_ONLY_EIGHT_LITERAL_HEAD"
        ),
        "bootstrap_materializer_and_launcher_are_distinct_raw_c_pre_git_blob_"
        "facts": True,
        "authorization_source_closure_includes_bootstrap_and_materializer": True,
        "normalized_wrapper_binding_kind": (
            "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
        ),
        "normalized_wrapper_redacted_literal_count": 8,
        "launch_manifest_generated_externally_after_source_and_wrapper_freeze": (
            True
        ),
        "actual_manifest_digest_preregistered": False,
        "actual_manifest_digest_is_runtime_transport_receipt": True,
        "actual_manifest_digest_is_scientific_identity": False,
        "trusted_computing_base": [
            "EXACT_USR_BIN_PYTHON3_FACT",
            "EXACT_USR_BIN_GIT_FACT_AND_VERSION",
            "EXACT_C_PRE_BOOTSTRAP_RAW_FACT",
            "EXACT_C_PRE_MATERIALIZER_RAW_FACT",
            "EXACT_C_PRE_LAUNCHER_RAW_FACT",
            "CANONICAL_LAUNCH_MANIFEST_GENERATION_RULE",
            "STDLIB_ONLY_ISOLATED_STARTUP",
            "EXACT_AUTHORIZATION_SOURCE_CLOSURE",
            "MANIFEST_BOUND_PACKAGING_AND_TOMLI_SOURCE_CLOSURE",
            "IN_MEMORY_ALLOWLIST_ONLY_ACFQP_LOADER",
            "SIX_PROCESS_GIT_AUDIT_SCHEDULE",
        ],
        "unlisted_repo_local_or_binary_module_origin_rejected": True,
        "materialization_is_preauthorization_structural_obligation": True,
        "created_before_v180r12r2_authorized_production_execution": True,
        "external_root_creation_required_before_authorization_issuance": False,
        "materialization_is_campaign_actual_measurement": False,
        "materialization_terminal_is_typed_structural_receipt": True,
        "materialization_failure_forbids_same_identity_rerun": True,
        "materialization_failure_means_v180r12r2_execution_attempted": False,
        "materialization_failure_means_scientific_output_created": False,
        "production_and_verification_launch_receipts_required": True,
        "launch_attempt_record_written_o_excl_before_child_exec": True,
        "launch_attempt_record_is_concurrency_and_replay_lock": True,
        "launch_terminal_receipt_or_failure_cannot_replace_attempt_lock": True,
        "launch_freshness_matrix_includes_attempt_receipt_failure_and_"
        "scientific_output_progress": True,
        "materialization_failure_sibling_forbids_any_launch": True,
        "production_success_requires_runtime_cas_absent": True,
        "verification_start_requires_runtime_cas_absent": True,
        "runtime_cas_absence_matches_production_and_verification_runner_"
        "freshness": True,
        "verification_launch_requires_typed_successful_production_attempt_"
        "and_receipt_join": True,
        "launcher_work_is_preauthorization_supervision": True,
        "launcher_work_is_campaign_actual_measurement": False,
        "launch_receipts_are_preauthorization_structural_receipts": True,
        "launch_receipts_are_campaign_actual_measurements": False,
        "launch_failure_forbids_same_launch_identity_rerun": True,
        "authorization_evidence_verification_first_action_scope": (
            "FIRST_ACTION_INSIDE_RUNNER_MAIN_AFTER_PRELAUNCH_DISPATCH_"
            "BEFORE_ANY_SCIENTIFIC_OUTPUT_INSPECTION_OR_CREATION"
        ),
        "authorization_evidence_verification_is_process_first_action": False,
        "prelaunch_materialization_and_dispatch_precede_runner_main": True,
        "post_snapshot_working_tree_mutation_out_of_scope": True,
    }

SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)

# source kind, authorization id, covered terminal codes, terminal path, terminal
# id key/id/size/hash, verification path/id/size/hash
RETAINED_SOURCE_GROUP_SPECS = (
    (
        "V180R11_RETAINED_V34_FINISH_FORWARD",
        "0935d168087af5adcb6bc6c31f7958502092ee8381d2bea030d89e1725f6906a",
        (TerminalCode.ABSTRACT_CERTIFIED.value,),
        ".tmp/exact-freeze/v180r11_v34_retained_terminal.json",
        "v34_retained_terminal_id",
        "aaaed6c19b1c7061b409dfdd042a189b4e4ea94e269d1e7c0de6d748d0932f42",
        8_547_638,
        "b6d3e1e48bad2bcdf68594b87b801466479bf596e4758443014b067cf45659e4",
        ".tmp/exact-freeze/v180r11_v34_retained_verification.json",
        "caf0a523d3b7919d9a98460aab9faeed86eefd4dd6d7cc7bc28e9fc9dd4293c9",
        1_341,
        "7080e808e8e03127e2ddea832bb093ba54430abfc1b5ff0e73e2c87e3fe9e5da",
    ),
    (
        "V180R10R1_RETAINED_V36_FINISH_FORWARD",
        "e53492926bc900ccd64ed27456eca45e1c5b087c7995a122d47b80e432064ad3",
        (TerminalCode.LOCAL_GROUND_RECOVERY.value,),
        ".tmp/exact-freeze/v180r10r1_v36_retained_terminal.json",
        "v36_retained_terminal_id",
        "9f73d1e948ce31025188565fbb94cfb9d53281e8b2ef783e5251ec6b17b0c66c",
        3_134_599,
        "2f2bd742d11f2750d5be0a3e61614912bccf84258b36ab6b62cbe8b1617496b3",
        ".tmp/exact-freeze/v180r10r1_v36_retained_verification.json",
        "8946eb3158196b005f4a3ff92b22ce521378839ceeb969fec899a5776e8721ef",
        1_553,
        "e6c38d65dd0d7f2cfb5193dbf99b6d54c99e785f1081102925428c8338236501",
    ),
    (
        "V180R7R1_FRESH_FULL_GROUND_FALLBACK",
        "44c19c059e229b6d45b1a9cf4591bf5ee5a53a68ca33ba54b5f5b6ae1b115f6b",
        (TerminalCode.FULL_GROUND_FALLBACK.value,),
        ".tmp/exact-freeze/v180r7r1_full_ground_fallback_terminal_bundle.json",
        "production_terminal_bundle_id",
        "24f72f86b3c27ef47c8126335557e9f45cff84ac9a9737481a50575bbdeae4ef",
        1_921_872,
        "e44f26f95056d3815160c8c6bcc2b86a22326c356422c04cf36e8e7af79d3d5c",
        ".tmp/exact-freeze/v180r7r1_full_ground_fallback_verification.json",
        "552a8104201426f3a696a4ee846922eb42c9148c59c5ce7921f1a865b4c94921",
        2_187,
        "4a3e711e5c6fa14c873adbcc8023612e1a390db1336f8c3a6b75d51267c25c85",
    ),
    (
        "V180R8_FRESH_CACHED_EXACT",
        "977f86ccbcef45b6117479ac63866bed57671764f23e4c8c391415a4b15349e3",
        (TerminalCode.CACHED_EXACT_INFEASIBLE.value,),
        ".tmp/v180r8-cached-exact-production/TERMINAL.json",
        "production_terminal_bundle_id",
        "4a90d809119b470ee6feefcd7d6332bb0c9144612bf32fad72f608e99a08dae6",
        335_305,
        "3b39bec8f60c0f7115c35e898b06e82d87ef2efa386c2f39906b20124fee1052",
        ".tmp/v180r8-cached-exact-verification/VERIFICATION.json",
        "6d3aaefb90bc2c341c3a14a2d38bfc1345f7335d99fb94726df9821132a9f37f",
        1_406,
        "35715f6f295459157ddd30ef3f48a809ba31e9470e39fd0a6bf12fa77b9da0b8",
    ),
    (
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        "d855e8cd646537687fcde2485a3f7ee83e50ac1831ab01e0f1d0b923aca5703f",
        (
            TerminalCode.FULL_GROUND_EXACT_INFEASIBLE.value,
            TerminalCode.INTEGRITY_FAILURE.value,
            TerminalCode.PROTOCOL_FAILURE.value,
            TerminalCode.REBUILD_REQUIRED.value,
            TerminalCode.FALLBACK_CAP_EXHAUSTED.value,
            TerminalCode.ATTEMPT_BUDGET_EXHAUSTED.value,
        ),
        ".tmp/exact-freeze/v180r9_remaining_terminal_production/TERMINAL.json",
        "production_campaign_bundle_id",
        "dae4c77ee78da32ccb1fee25481fd6d201ba66282a00259ff4ca68ac51a9b622",
        1_548_968,
        "605f5448db54da8e193e062fe694e5c40badcd1ccbb277d8822cb17dcaf9bb42",
        ".tmp/exact-freeze/v180r9_remaining_terminal_production/VERIFICATION.json",
        "d17c2fdd948479a9bcd9aecd4de9b6f834f390da3f889ee8d83c15aae02ae735",
        1_170,
        "b0eb929d5da9630b2446a94668ca93e5d328116a19b4b176af247731866543cb",
    ),
)

# terminal code, route kind, source kind, representative logical-terminal chain
ORDERED_ROUTE_COMPONENT_SPECS = (
    (
        TerminalCode.ABSTRACT_CERTIFIED.value,
        "ABSTRACT_ONLY_CERTIFICATE",
        "V180R11_RETAINED_V34_FINISH_FORWARD",
        True,
    ),
    (
        TerminalCode.LOCAL_GROUND_RECOVERY.value,
        "LOCAL_ATTEMPT",
        "V180R10R1_RETAINED_V36_FINISH_FORWARD",
        True,
    ),
    (
        TerminalCode.FULL_GROUND_FALLBACK.value,
        "ABSTRACT_FAILED_PREFIX",
        "V180R7R1_FRESH_FULL_GROUND_FALLBACK",
        False,
    ),
    (
        TerminalCode.FULL_GROUND_FALLBACK.value,
        "LOCAL_ATTEMPT",
        "V180R7R1_FRESH_FULL_GROUND_FALLBACK",
        False,
    ),
    (
        TerminalCode.FULL_GROUND_FALLBACK.value,
        "DIRECT_FALLBACK",
        "V180R7R1_FRESH_FULL_GROUND_FALLBACK",
        True,
    ),
    (
        TerminalCode.CACHED_EXACT_INFEASIBLE.value,
        "ABSTRACT_FAILED_PREFIX",
        "V180R8_FRESH_CACHED_EXACT",
        True,
    ),
    (
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE.value,
        "DIRECT_FALLBACK",
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        True,
    ),
    (
        TerminalCode.INTEGRITY_FAILURE.value,
        "ABSTRACT_FAILED_PREFIX",
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        True,
    ),
    (
        TerminalCode.PROTOCOL_FAILURE.value,
        "ABSTRACT_FAILED_PREFIX",
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        True,
    ),
    (
        TerminalCode.REBUILD_REQUIRED.value,
        "REBUILD",
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        True,
    ),
    (
        TerminalCode.FALLBACK_CAP_EXHAUSTED.value,
        "DIRECT_FALLBACK",
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        True,
    ),
    (
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED.value,
        "ABSTRACT_FAILED_PREFIX",
        "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
        True,
    ),
)

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r2.py",
    (
        "src/acfqp/construction_k7_ten_terminal_aggregation_"
        "stale_predecessor_freeze_v180r12r2.py"
    ),
    "src/acfqp/construction_k7_all_path_formalization_contract_v180.py",
    "src/acfqp/construction_accounting_registry_v9.py",
    "src/acfqp/accounting_v1.py",
    "src/acfqp/actual_accounting_v1.py",
    "src/acfqp/routing_v1.py",
    "src/acfqp/phase3e_ids.py",
)


class TenTerminalAggregationProtocolV180R12R2Error(ValueError):
    """A predecessor, retained byte fact, or protocol denominator changed."""


def _fail(message: str) -> NoReturn:
    raise TenTerminalAggregationProtocolV180R12R2Error(message)


def _read_regular_symlink_free(path: Path) -> bytes:
    try:
        return source_runtime_v2._read_regular_symlink_free(path)  # noqa: SLF001
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise TenTerminalAggregationProtocolV180R12R2Error(
            "protocol-bound path is absent, linked, or nonregular"
        ) from error


def _file_fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = _read_regular_symlink_free(root / relative_path)
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _retained_source_group_documents(root: Path) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for (
        source_kind,
        source_authorization_id,
        covered_terminal_codes,
        terminal_path,
        terminal_id_key,
        terminal_id,
        terminal_byte_count,
        terminal_sha256,
        verification_path,
        verification_id,
        verification_byte_count,
        verification_sha256,
    ) in RETAINED_SOURCE_GROUP_SPECS:
        terminal_raw = _read_regular_symlink_free(root / terminal_path)
        verification_raw = _read_regular_symlink_free(root / verification_path)
        try:
            terminal_document = loads_canonical_json(terminal_raw)
            verification_document = loads_canonical_json(verification_raw)
        except ValueError as error:
            raise TenTerminalAggregationProtocolV180R12R2Error(
                "retained terminal or independent-verification bytes changed"
            ) from error
        if not (
            type(terminal_document) is dict
            and canonical_json_bytes(terminal_document) == terminal_raw
            and terminal_document.get(terminal_id_key) == terminal_id
            and len(terminal_raw) == terminal_byte_count
            and hashlib.sha256(terminal_raw).hexdigest() == terminal_sha256
            and type(verification_document) is dict
            and canonical_json_bytes(verification_document) == verification_raw
            and verification_document.get("verification_id") == verification_id
            and len(verification_raw) == verification_byte_count
            and hashlib.sha256(verification_raw).hexdigest() == verification_sha256
        ):
            _fail("retained terminal or independent-verification bytes changed")
        groups.append(
            {
                "source_kind": source_kind,
                "source_authorization_id": source_authorization_id,
                "covered_terminal_codes": list(covered_terminal_codes),
                "terminal_fact": {
                    "relative_path": terminal_path,
                    "content_id_key": terminal_id_key,
                    "content_id": terminal_id,
                    "byte_count": terminal_byte_count,
                    "sha256": terminal_sha256,
                },
                "verification_fact": {
                    "relative_path": verification_path,
                    "verification_id": verification_id,
                    "byte_count": verification_byte_count,
                    "sha256": verification_sha256,
                },
                "status_at_successor_freeze": (
                    "COMPLETED_AND_INDEPENDENTLY_VERIFIED"
                ),
            }
        )
    return groups


def _ordered_route_components() -> list[dict[str, Any]]:
    return [
        {
            "component_ordinal": ordinal,
            "terminal_code": terminal_code,
            "route_kind": route_kind,
            "source_kind": source_kind,
            "logical_terminal_representative": representative,
            "counter_record_count": COUNTER_RECORDS_PER_ROUTE_COMPONENT,
        }
        for ordinal, (
            terminal_code,
            route_kind,
            source_kind,
            representative,
        ) in enumerate(ORDERED_ROUTE_COMPONENT_SPECS)
    ]


def build_ten_terminal_aggregation_protocol_v180r12r2() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    preserved = (
        stale_predecessor.freeze_ten_terminal_aggregation_stale_predecessor_v180r12r2()
    )
    frozen_contract = contract.freeze_all_path_formalization_contract_v180()
    source_groups = _retained_source_group_documents(root)
    ordered_route_components = _ordered_route_components()
    terminal_codes = [row.value for row in TerminalCode]
    covered_codes = [
        code for group in source_groups for code in group["covered_terminal_codes"]
    ]
    representative_count = sum(
        int(row["logical_terminal_representative"])
        for row in ordered_route_components
    )
    retained_source_total_bytes = sum(
        group["terminal_fact"]["byte_count"]
        + group["verification_fact"]["byte_count"]
        for group in source_groups
    )
    retained_source_paths = [
        fact["relative_path"]
        for group in source_groups
        for fact in (group["terminal_fact"], group["verification_fact"])
    ]
    retained_source_set_sha256 = hashlib.sha256(
        canonical_json_bytes(source_groups)
    ).hexdigest()
    if not (
        frozen_contract.formalization_contract_id == FORMALIZATION_CONTRACT_ID
        and len(source_groups) == SOURCE_GROUP_COUNT
        and covered_codes == terminal_codes
        and len(set(covered_codes)) == TERMINAL_CODE_COUNT
        and len(ordered_route_components) == ROUTE_COMPONENT_CHAIN_COUNT
        and representative_count == TERMINAL_CODE_COUNT
        and retained_source_total_bytes == RETAINED_SOURCE_TOTAL_BYTE_COUNT
        and len(retained_source_paths) == 2 * SOURCE_GROUP_COUNT
        and len(set(retained_source_paths)) == len(retained_source_paths)
        and len(SHARED_RESOURCE_PATHS) == SHARED_RESOURCE_RECEIPTS_PER_TERMINAL
        and LOGICAL_TERMINAL_REPRESENTATIVE_RECORD_COUNT
        == TERMINAL_CODE_COUNT * COUNTER_RECORDS_PER_ROUTE_COMPONENT
        and UNIQUE_ROUTE_COMPONENT_RECORD_COUNT
        == ROUTE_COMPONENT_CHAIN_COUNT * COUNTER_RECORDS_PER_ROUTE_COMPONENT
        and EXTRA_NONREPRESENTATIVE_V180R7R1_RECORD_COUNT
        == UNIQUE_ROUTE_COMPONENT_RECORD_COUNT
        - LOGICAL_TERMINAL_REPRESENTATIVE_RECORD_COUNT
        and TERMINAL_SHARED_RESOURCE_RECEIPT_COUNT
        == TERMINAL_CODE_COUNT * SHARED_RESOURCE_RECEIPTS_PER_TERMINAL
        and CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        == len(SHARED_RESOURCE_PATHS)
        and CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT == 0
        and CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT == 0
        and CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT == 0
        and CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT == 0
        and CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT == 0
        and CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT == 0
        and CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT == 0
        and TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
        == TERMINAL_SHARED_RESOURCE_RECEIPT_COUNT
        and ADDRESS_SPACE_HARD_CAP_BYTES == 16 * 1024 * 1024 * 1024
        and REJECTED_PREFLIGHT_ADDRESS_SPACE_CAP_BYTES
        == 6 * 1024 * 1024 * 1024
        and REJECTED_PREFLIGHT_MAX_RSS_KIB == 6_216_640
        and REJECTED_PREFLIGHT_ELAPSED_SECONDS == "1908.72"
        and FINALIZER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT == 7
        and INDEPENDENT_VERIFIER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT_PER_REPLAY
        == 2 * SOURCE_GROUP_COUNT
        and PRODUCER_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT == 8
        and VERIFICATION_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT == 22
        and TRANSIENT_HEAP_RELEASE_ALLOWED_RETURN_STATUSES == (0, 1)
    ):
        _fail("V180r12r2 terminal or route-component denominator changed")

    slot_payload = {
        "schema": "acfqp.ten_terminal_aggregation_execution_slot.v180r12r2",
        "predecessor_stale_record_id": preserved.stale_predecessor_id,
        "predecessor_v180r12r1_authorization_id": (
            stale_predecessor.PRESERVED_V180R12R1_AUTHORIZATION_ID
        ),
        "predecessor_v180r12r1_logical_occurrence_id": (
            stale_predecessor.PRESERVED_V180R12R1_LOGICAL_OCCURRENCE_ID
        ),
        "execution_nonce": EXECUTION_NONCE,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "aggregation_ordinal": 1,
        "retained_source_set_sha256": retained_source_set_sha256,
        "source_group_count": SOURCE_GROUP_COUNT,
        "terminal_code_count": TERMINAL_CODE_COUNT,
        "route_component_chain_count": ROUTE_COMPONENT_CHAIN_COUNT,
    }
    slot = {
        **slot_payload,
        "aggregation_execution_slot_id": domains.extension_content_id_v180r12r2(
            domains.CONSTRUCTION_K7_AGGREGATION_EXECUTION_SLOT_V180R12R2_DOMAIN,
            slot_payload,
        ),
    }
    if (
        EXPECTED_AGGREGATION_EXECUTION_SLOT_ID != "0" * 64
        and slot["aggregation_execution_slot_id"]
        != EXPECTED_AGGREGATION_EXECUTION_SLOT_ID
    ):
        _fail("V180r12r2 aggregation execution slot identity changed")

    payload = {
        "schema": "acfqp.ten_terminal_aggregation_protocol.v180r12r2",
        "formalization_contract_id": FORMALIZATION_CONTRACT_ID,
        "formalization_contract_exact_frozen_identity_used": True,
        "predecessor_stale_record_id": preserved.stale_predecessor_id,
        "preserved_v180r12_protocol_id": (
            stale_predecessor.PRESERVED_V180R12_PROTOCOL_ID
        ),
        "preserved_v180r12_failure_id": (
            stale_predecessor.PRESERVED_V180R12_FAILURE_ID
        ),
        "preserved_v180r12r1_protocol_id": (
            stale_predecessor.PRESERVED_V180R12R1_PROTOCOL_ID
        ),
        "preserved_v180r12r1_authorization_id": (
            stale_predecessor.PRESERVED_V180R12R1_AUTHORIZATION_ID
        ),
        "v180r12r1_status": "STALE_UNEXECUTED",
        "v180r12r1_same_authorization_execution_forbidden": True,
        "aggregation_execution_slot": slot,
        "fresh_slot_count": 1,
        "old_authorization_or_logical_occurrence_reused": False,
        "retained_source_groups": source_groups,
        "retained_source_set_sha256": retained_source_set_sha256,
        "retained_source_total_byte_count": retained_source_total_bytes,
        "retained_source_file_count": 2 * SOURCE_GROUP_COUNT,
        "retained_terminal_file_count": SOURCE_GROUP_COUNT,
        "retained_independent_verification_file_count": SOURCE_GROUP_COUNT,
        "retained_source_paths_unique": True,
        "source_group_count": SOURCE_GROUP_COUNT,
        "ordered_terminal_codes": terminal_codes,
        "terminal_code_count": TERMINAL_CODE_COUNT,
        "ordered_route_components": ordered_route_components,
        "route_component_chain_count": ROUTE_COMPONENT_CHAIN_COUNT,
        "logical_terminal_representative_component_count": TERMINAL_CODE_COUNT,
        "nonrepresentative_v180r7r1_route_component_count": 2,
        "counter_records_per_route_component": (
            COUNTER_RECORDS_PER_ROUTE_COMPONENT
        ),
        "logical_terminal_representative_record_count": (
            LOGICAL_TERMINAL_REPRESENTATIVE_RECORD_COUNT
        ),
        "unique_route_component_record_count": (
            UNIQUE_ROUTE_COMPONENT_RECORD_COUNT
        ),
        "extra_nonrepresentative_v180r7r1_record_count": (
            EXTRA_NONREPRESENTATIVE_V180R7R1_RECORD_COUNT
        ),
        "source_verification_receipt_count": SOURCE_GROUP_COUNT,
        "logical_terminal_receipt_count": TERMINAL_CODE_COUNT,
        "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
        "shared_resource_receipts_per_terminal": (
            SHARED_RESOURCE_RECEIPTS_PER_TERMINAL
        ),
        "terminal_shared_resource_receipt_count": (
            TERMINAL_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "campaign_scope_structural_obligation_count": (
            CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        ),
        "campaign_scope_actual_counter_record_count": (
            CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT
        ),
        "campaign_scope_actual_shared_resource_receipt_count": (
            CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "campaign_scope_actual_work_vector_count": (
            CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT
        ),
        "campaign_scope_actual_comparison_vector_count": (
            CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT
        ),
        "campaign_scope_actual_projection_proof_count": (
            CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT
        ),
        "campaign_scope_actual_native_zero_attestation_count": (
            CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT
        ),
        "campaign_scope_authoritative_receipt_count": (
            CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "total_authoritative_shared_resource_receipt_count": (
            TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT
        ),
        "v180r7r1_construction_axis_separate": True,
        "v180r7r1_construction_axis_occurrence_counter_record_count": 0,
        "v180r7r1_construction_axis_work_vector_count": 0,
        "v180r7r1_construction_axis_comparison_vector_count": 0,
        "construction_axis_must_not_be_forged_into_route_records": True,
        "campaign_orchestration_uses_typed_campaign_scope": True,
        "campaign_orchestration_route_kind": None,
        "campaign_scope_structural_boundary_required": True,
        "campaign_scope_structural_declarations_are_not_counter_records": True,
        "campaign_scope_derived_denominators_are_not_actual_measurements": True,
        "campaign_scope_actual_measurement_ledger_present": False,
        "legacy_abstract_only_campaign_route_reuse_forbidden": True,
        "every_source_independent_verifier_must_replay": True,
        "every_route_component_requires_counter_record_work_vector_comparison_vector": (
            True
        ),
        "every_logical_terminal_requires_typed_receipt": True,
        "output_bytes_exact_fixed_point_required": True,
        "producer_free_aggregate_reconstruction_required": True,
        "retained_verification_replay_required": True,
        "historical_summary_translation_forbidden": True,
        "failure_prefix_work_must_be_retained": True,
        "completed_predecessor_outcome_bytes_accessed": True,
        "retained_source_files_are_predecessor_evidence_not_v180r12r2_outcome": (
            True
        ),
        "v180r12r2_outcome_bytes_accessed": False,
        "protocol_frozen_before_any_v180r12r2_outcome": True,
        "authorization_evidence_source_boundary_commit_required": True,
        "prelaunch_contract": prelaunch_contract_v180r12r2(),
        "source_boundary_empty_bridge_commit_required": True,
        "source_boundary_empty_bridge_must_preserve_entire_tree": True,
        "source_boundary_bridge_then_wrapper_eight_literal_commit_sequence_required": (
            True
        ),
        "source_boundary_candidate_build_may_relax_only_literal_commit_presence": (
            True
        ),
        "source_boundary_runtime_freeze_requires_committed_wrapper_literals": True,
        "source_boundary_candidate_and_runtime_payload_identity_must_match": True,
        "source_boundary_post_literal_bound_history_touch_forbidden": True,
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "rejected_preprereg_address_space_cap_bytes": (
            REJECTED_PREFLIGHT_ADDRESS_SPACE_CAP_BYTES
        ),
        "rejected_preprereg_max_rss_kib": REJECTED_PREFLIGHT_MAX_RSS_KIB,
        "rejected_preprereg_elapsed_seconds": (
            REJECTED_PREFLIGHT_ELAPSED_SECONDS
        ),
        "rejected_preprereg_failure_stage": (
            "V180R10R1_TO_V36_TO_V35_PLANNER_FROZENSET_CACHE"
        ),
        "rejected_preprereg_failure_type": "MemoryError",
        "rejected_preprereg_kind": (
            "PRE_PREREG_NONFROZEN_DEVELOPMENT_RESOURCE_PREFLIGHT"
        ),
        "rejected_preprereg_test": (
            "test_v180r12r2_loads_compact_real_groups_under_explicit_6gib_"
            "rlimit"
        ),
        "rejected_preprereg_dummy_aggregation_protocol_id": "a" * 64,
        "rejected_preprereg_dummy_execution_authorization_id": "b" * 64,
        "rejected_preprereg_scientific_output_created": False,
        "rejected_preprereg_production_artifact_written": False,
        "rejected_preprereg_failure_artifact_written": False,
        "rejected_preprereg_runtime_cas_created": False,
        "rejected_preprereg_authorized_production_aggregation_execution_"
        "attempted": False,
        "rejected_preprereg_development_resource_preflight_computation_"
        "attempted": True,
        "rejected_preprereg_development_resource_preflight_completed": False,
        "rejected_preprereg_scientific_authority": False,
        "rejected_preprereg_official_authority": False,
        "rejected_preprereg_cap_was_frozen_authorization": False,
        "address_space_cap_selected_before_v180r12r2_authorization": True,
        "glibc_malloc_trim_required_fail_closed": True,
        "glibc_malloc_trim_allowed_return_statuses": list(
            TRANSIENT_HEAP_RELEASE_ALLOWED_RETURN_STATUSES
        ),
        "linux_proc_self_statm_current_vms_proof_required_before_rlimit_as": (
            True
        ),
        "current_vms_must_not_exceed_address_space_cap_before_rlimit_as": True,
        "finalizer_transient_heap_release_phase_count": (
            FINALIZER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT
        ),
        "independent_verifier_transient_heap_release_phase_count_per_replay": (
            INDEPENDENT_VERIFIER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT_PER_REPLAY
        ),
        "producer_runner_precap_heap_release_phase_count": (
            PRODUCER_RUNNER_PRECAP_HEAP_RELEASE_PHASE_COUNT
        ),
        "producer_total_transient_heap_release_phase_count": (
            PRODUCER_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT
        ),
        "verification_runner_external_heap_release_phase_count": (
            VERIFICATION_RUNNER_EXTERNAL_HEAP_RELEASE_PHASE_COUNT
        ),
        "verification_replay_count": VERIFICATION_REPLAY_COUNT,
        "verification_total_transient_heap_release_phase_count": (
            VERIFICATION_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT
        ),
        "transient_heap_release_authority_class": (
            TRANSIENT_HEAP_RELEASE_AUTHORITY_CLASS
        ),
        "transient_heap_release_is_preauthorization_resource_schedule": True,
        "transient_heap_release_is_campaign_actual_measurement": False,
        "failure_emergency_reserve_bytes": FAILURE_EMERGENCY_RESERVE_BYTES,
        "failure_emergency_reserve_allocated_before_rlimit_as": True,
        "failure_emergency_reserve_counted_inside_address_space_cap": True,
        "failure_message_byte_cap": FAILURE_MESSAGE_BYTE_CAP,
        "failure_type_byte_cap": FAILURE_TYPE_BYTE_CAP,
        "failure_message_utf8_formatting_fail_safe": True,
        "failure_traceback_detach_and_child_frame_clear_required": True,
        "alarm_teardown_inside_protected_terminal_boundary": True,
        "alarm_cancel_or_ignore_before_primary_failure_formatting": True,
        "alarm_neutralization_precedes_failure_reserve_release": True,
        "alarm_previous_handler_restore_after_failure_reserve_release": True,
        "failure_reserve_release_precedes_failure_formatting": True,
        "alarm_teardown_failure_typed_observation_required": True,
        "failure_path_heap_release_best_effort": True,
        "failure_path_heap_release_is_not_fail_closed_phase": True,
        "failure_path_heap_release_is_campaign_actual_measurement": False,
        "failure_progress_observation_streaming_sha256_required": True,
        "failure_observation_stream_buffer_bytes": (
            FAILURE_OBSERVATION_STREAM_BUFFER_BYTES
        ),
        "producer_progress_path_count": PRODUCER_PROGRESS_PATH_COUNT,
        "producer_all_progress_paths_absent_before_execution_required": True,
        "verification_runtime_cas_absent_before_execution_required": True,
        "verification_terminal_input_byte_cap": (
            VERIFICATION_TERMINAL_INPUT_BYTE_CAP
        ),
        "verification_terminal_input_cap_checked_before_and_during_read": True,
        "aggregation_execution_authorization_issued": False,
        "aggregation_execution_started": False,
        "aggregation_execution_count": 0,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_BLOCKER": COUNTER_COMPLETENESS_BLOCKER,
        "fresh_v180r12r3_actual_measurement_ledger_required": True,
        "fresh_v180r12r3_authorization_and_execution_required": True,
        "v180r12r2_counter_completeness_claimed": False,
        "v180r12r2_workload_economics_claimed": False,
        "source_facts": [_file_fact(root, path) for path in _SOURCE_PATHS],
        "weight_agnostic_componentwise_economics_required_after_counter_completeness": (
            True
        ),
        "scalarization_in_this_protocol": False,
        "reference_machine_profile_present": False,
        "separate_fresh_calibration_successor_required_for_scalar_and_break_even": (
            True
        ),
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
    }
    return {
        **payload,
        "aggregation_protocol_id": domains.extension_content_id_v180r12r2(
            domains.CONSTRUCTION_K7_AGGREGATION_PROTOCOL_V180R12R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationProtocolV180R12R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    aggregation_protocol_id: str
    aggregation_execution_slot_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and document.get("aggregation_protocol_id")
            == self.aggregation_protocol_id
            and document.get("aggregation_execution_slot", {}).get(
                "aggregation_execution_slot_id"
            )
            == self.aggregation_execution_slot_id
        ):
            _fail("V180r12r2 aggregation protocol is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@lru_cache(maxsize=1)
def freeze_ten_terminal_aggregation_protocol_v180r12r2() -> (
    TenTerminalAggregationProtocolV180R12R2
):
    document = build_ten_terminal_aggregation_protocol_v180r12r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["aggregation_protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V180r12r2 frozen aggregation protocol identity changed")
    return TenTerminalAggregationProtocolV180R12R2(
        _ISSUER,
        raw,
        document["aggregation_protocol_id"],
        document["aggregation_execution_slot"]["aggregation_execution_slot_id"],
    )


__all__ = (
    "ADDRESS_SPACE_HARD_CAP_BYTES",
    "CAMPAIGN_SCOPE_ACTUAL_COMPARISON_VECTOR_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_COUNTER_RECORD_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_NATIVE_ZERO_ATTESTATION_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_PROJECTION_PROOF_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_SHARED_RESOURCE_RECEIPT_COUNT",
    "CAMPAIGN_SCOPE_ACTUAL_WORK_VECTOR_COUNT",
    "CAMPAIGN_SCOPE_AUTHORITATIVE_RECEIPT_COUNT",
    "CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT",
    "CAMPAIGN_SHARED_RESOURCE_RECEIPT_COUNT",
    "COUNTER_COMPLETENESS_BLOCKER",
    "COUNTER_RECORDS_PER_ROUTE_COMPONENT",
    "EXECUTION_NONCE",
    "EXPECTED_AGGREGATION_EXECUTION_SLOT_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_PROTOCOL_ID",
    "EXTRA_NONREPRESENTATIVE_V180R7R1_RECORD_COUNT",
    "FAILURE_EMERGENCY_RESERVE_BYTES",
    "FAILURE_MESSAGE_BYTE_CAP",
    "FAILURE_OBSERVATION_STREAM_BUFFER_BYTES",
    "FAILURE_TYPE_BYTE_CAP",
    "FINALIZER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT",
    "INDEPENDENT_VERIFIER_TRANSIENT_HEAP_RELEASE_PHASE_COUNT_PER_REPLAY",
    "LOGICAL_OCCURRENCE_ID",
    "LOGICAL_TERMINAL_REPRESENTATIVE_RECORD_COUNT",
    "ORDERED_ROUTE_COMPONENT_SPECS",
    "PRODUCER_RUNNER_PRECAP_HEAP_RELEASE_PHASE_COUNT",
    "PRODUCER_PROGRESS_PATH_COUNT",
    "PRODUCER_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT",
    "PRELAUNCH_BOOTSTRAP_RELATIVE_PATH",
    "PRELAUNCH_EXTERNAL_ROOT_RELATIVE_PATH",
    "PRELAUNCH_MANIFEST_RELATIVE_PATH",
    "PRELAUNCH_LAUNCH_RULE_ID",
    "PRELAUNCH_MATERIALIZATION_FAILURE_RELATIVE_PATH",
    "PRELAUNCH_MATERIALIZATION_RULE_ID",
    "PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH",
    "PRELAUNCH_PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH",
    "PRELAUNCH_PRODUCTION_LAUNCH_ATTEMPT_RELATIVE_PATH",
    "PRELAUNCH_PRODUCTION_LAUNCH_RECEIPT_RELATIVE_PATH",
    "PRELAUNCH_ROOT_RELATIVE_PATH",
    "PRELAUNCH_SOURCE_CLOSURE_RULE_ID",
    "PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH",
    "PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH",
    "PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH",
    "RETAINED_SOURCE_GROUP_SPECS",
    "RETAINED_SOURCE_TOTAL_BYTE_COUNT",
    "REJECTED_PREFLIGHT_ADDRESS_SPACE_CAP_BYTES",
    "REJECTED_PREFLIGHT_ELAPSED_SECONDS",
    "REJECTED_PREFLIGHT_MAX_RSS_KIB",
    "ROUTE_COMPONENT_CHAIN_COUNT",
    "SHARED_RESOURCE_PATHS",
    "SHARED_RESOURCE_RECEIPTS_PER_TERMINAL",
    "SOURCE_GROUP_COUNT",
    "TERMINAL_CODE_COUNT",
    "TERMINAL_SHARED_RESOURCE_RECEIPT_COUNT",
    "TOTAL_AUTHORITATIVE_SHARED_RESOURCE_RECEIPT_COUNT",
    "TOTAL_SHARED_RESOURCE_RECEIPT_COUNT",
    "TRANSIENT_HEAP_RELEASE_ALLOWED_RETURN_STATUSES",
    "TRANSIENT_HEAP_RELEASE_AUTHORITY_CLASS",
    "TenTerminalAggregationProtocolV180R12R2",
    "TenTerminalAggregationProtocolV180R12R2Error",
    "UNIQUE_ROUTE_COMPONENT_RECORD_COUNT",
    "VERIFICATION_REPLAY_COUNT",
    "VERIFICATION_TERMINAL_INPUT_BYTE_CAP",
    "VERIFICATION_RUNNER_EXTERNAL_HEAP_RELEASE_PHASE_COUNT",
    "VERIFICATION_TOTAL_TRANSIENT_HEAP_RELEASE_PHASE_COUNT",
    "build_ten_terminal_aggregation_protocol_v180r12r2",
    "freeze_ten_terminal_aggregation_protocol_v180r12r2",
    "prelaunch_contract_v180r12r2",
)
