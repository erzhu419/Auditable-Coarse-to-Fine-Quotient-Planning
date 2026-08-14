"""Failure-successor native-accounting registration for the V35 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_CAMPAIGN_V36_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_COUNTER_BUNDLE_V36_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_MEASUREMENT_V36_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V36_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_VERIFICATION_V36_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "36.3.0"
PROPOSED_CONTRACT_VERSION = "2.0.198"
PROFILE_KEY = "construction_k7_standard_2048_adaptive_expression_actual_accounting_v36r3"
PREREGISTRATION_ID = "8559184bc2729b7b5c7867bafde5180642e39016ebff3bd7ad02d07300a7159a"
EXPECTED_CANONICAL_BYTE_COUNT = 220_047
EXPECTED_CANONICAL_SHA256 = "83bc43b7584f06f3e8241fb7ead7565d1eb8973ec6bd03cf233b04030729265a"
FAILED_V36R2_PREREGISTRATION_ID = (
    "9bece9cfa434fd854705b796006125f3b913a25986a07c6c3db64aa7c8edf86f"
)
FAILED_V36R1_PREREGISTRATION_ID = (
    "b74c33f607b3a6523a1ec341a0bd059f94edc251bab35f003233e63488815dde"
)
SUPERSEDED_V36_PREREGISTRATION_ID = (
    "b6d209f4a0e285653349a66293c21597b39dcd1f74c95fbd69d9e3e439accb65"
)
V34R1_PREREGISTRATION_ID = (
    "4546af82f1f4e6429c83148b0f37f9a3995b80e9a0bb4abc2971ada13b115920"
)
V35_PREREGISTRATION_ID = (
    "d2705f1b310b2f88f41799376a69f55b3355b53a54a2a103ba11e5dbf00491a9"
)
V34R1_ACCOUNTED_CAMPAIGN_ID = (
    "f5e83e7cb6eaee01d35b325e83e6b50676843a32af40c21aae237144b5784f05"
)
V34R1_ACCOUNTING_VERIFICATION_ID = (
    "40baaf3c66d42ebc53e686f9dc91ae96ee92ebda442a176ac4db32c75cbc421a"
)
V35_ADAPTIVE_EXPRESSION_CAMPAIGN_ID = (
    "c33002f8bac5415d94c5185876ce104ac859243e7b50ee5922c1be9b4a812d25"
)
V35_ADAPTIVE_EXPRESSION_VERIFICATION_ID = (
    "0591b03140cb3e807b68ee4e90129c93863a45ef29ed44896df49c7d4caea348"
)
MAXIMUM_WORKER_PROCESSES = 2
MAXIMUM_TASKS_PER_WORKER_PROCESS = 1
MAXIMUM_EPISODES = 4
MAXIMUM_DECISIONS_PER_EPISODE = 128
MAXIMUM_TARGET_PROBABILITY_LABELS = 12
MAXIMUM_COLD_CHECKPOINTS = 12
WORKER_WORKING_BYTES_PEAK_UPPER = 24 * 1024 * 1024 * 1024
PARENT_WORKING_BYTES_PEAK_UPPER = 4 * 1024 * 1024 * 1024
MAXIMUM_ACCOUNTING_OUTPUT_BYTES = 2 * 1024 * 1024 * 1024

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V36_DOMAIN,
    "measurement": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_MEASUREMENT_V36_DOMAIN,
    "counter_bundle": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_COUNTER_BUNDLE_V36_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_CAMPAIGN_V36_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_VERIFICATION_V36_DOMAIN,
}

MODEL_OPERATIONAL_PATHS = (
    "model.active_query_partition_evaluations",
    "model.candidate_label_consistency_checks",
    "model.exact_program_proof_rows_evaluated",
    "model.expression_candidates_materialized",
    "model.structural_context_rows_frozen",
    "model.structural_expression_value_evaluations",
    "model.target_probability_labels_acquired",
    "model.world_model_freezes",
)
PLANNING_OPERATIONAL_PATHS = (
    "common.abstract_bellman_backups",
    "common.abstract_support_outcome_evaluations",
    "common.abstract_subproof_cache_lookups",
    "common.abstract_subproof_cache_hits",
    "common.abstract_subproof_cache_misses",
    "target.execution_ground_steps",
    "target.execution_outcome_rows",
    "target.transition_observations",
)
EVALUATION_PATHS = (
    "evaluation.active_query_partition_evaluations",
    "evaluation.candidate_label_consistency_checks",
    "evaluation.exact_actions_evaluated",
    "evaluation.exact_bellman_backups",
    "evaluation.exact_ground_steps",
    "evaluation.exact_outcome_rows",
    "evaluation.exact_program_proof_rows_evaluated",
    "evaluation.exact_states_expanded",
    "evaluation.exact_subproof_cache_hits",
    "evaluation.exact_subproof_cache_lookups",
    "evaluation.exact_subproof_cache_misses",
    "evaluation.expression_candidates_materialized",
    "evaluation.structural_context_rows_frozen",
    "evaluation.structural_expression_value_evaluations",
    "evaluation.target_probability_labels_acquired",
    "evaluation.world_model_freezes",
)
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


class ConstructionK7Standard2048AdaptiveAccountingPreregistrationV36Error(
    ValueError
):
    """The adaptive-accounting protocol, predecessor, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveAccountingPreregistrationV36Error(
        message
    )


def _stage_plan() -> list[dict[str, Any]]:
    return [
        {
            "stage": "CERTIFICATE_FAILURE_FRONTIER_FREEZE",
            "lane": "OPERATIONAL",
            "cardinality": 1,
            "counter_paths": ["model.structural_context_rows_frozen"],
            "target_probability_access_allowed": False,
        },
        {
            "stage": "ADAPTIVE_LABEL_ACQUISITION_AND_CANDIDATE_ELIMINATION",
            "lane": "OPERATIONAL",
            "cardinality": {
                "kind": "POST_V35_EXACT_COUNT_AT_MOST",
                "upper": MAXIMUM_TARGET_PROBABILITY_LABELS,
            },
            "counter_paths": list(MODEL_OPERATIONAL_PATHS),
            "query_must_reference_previously_failed_frontier": True,
        },
        {
            "stage": "EXPRESSION_PROPOSAL_FREEZE",
            "lane": "OPERATIONAL",
            "cardinality": 1,
            "counter_paths": [],
            "proposal_must_precede_target_semantics_reveal": True,
        },
        {
            "stage": "EXACT_PROGRAM_PROOF",
            "lane": "OPERATIONAL",
            "cardinality": 1,
            "counter_paths": ["model.exact_program_proof_rows_evaluated"],
            "proposal_must_precede_target_semantics_reveal": True,
        },
        {
            "stage": "PROVED_OVERLAY_FREEZE",
            "lane": "OPERATIONAL",
            "cardinality": 1,
            "counter_paths": ["model.world_model_freezes"],
            "proof_must_precede_overlay_authority": True,
        },
        {
            "stage": "EPISODE_ABSTRACT_PLANNING_AND_CERTIFICATION",
            "lane": "OPERATIONAL",
            "cardinality": MAXIMUM_EPISODES,
            "counter_paths": [
                path
                for path in PLANNING_OPERATIONAL_PATHS
                if not path.startswith("target.")
            ],
            "one_occurrence_per_worker_process": True,
        },
        {
            "stage": "EPISODE_SELECTED_TARGET_EXECUTION",
            "lane": "OPERATIONAL",
            "cardinality": MAXIMUM_EPISODES,
            "counter_paths": [
                path
                for path in PLANNING_OPERATIONAL_PATHS
                if path.startswith("target.")
            ],
            "certificate_must_freeze_before_target_execution": True,
        },
        {
            "stage": "MATCHED_FIRST_FRONTIER_NO_PRIOR_CONTROL",
            "lane": "EVALUATION",
            "cardinality": 1,
            "counter_paths": [
                "evaluation.target_probability_labels_acquired",
                "evaluation.semantic_integrity_checks",
                "evaluation.semantic_protocol_checks",
            ],
            "may_modify_operational_overlay": False,
        },
        {
            "stage": "COLD_EXACT_GROUND_CHECKPOINT_REPLAY",
            "lane": "EVALUATION",
            "cardinality": {
                "kind": "POST_V35_EXACT_COUNT_AT_MOST",
                "upper": MAXIMUM_COLD_CHECKPOINTS,
            },
            "counter_paths": list(EVALUATION_PATHS),
            "may_enter_operational_comparison": False,
        },
        {
            "stage": "PROCESS_AND_IO_SUPERVISION",
            "lane": "OPERATIONAL_AND_EVALUATION_SEPARATED",
            "cardinality": {
                "kind": "DERIVED_FROM_EXACT_STAGE_INVENTORY",
                "upper": 32,
            },
            "counter_paths": list(SHARED_RESOURCE_PATHS),
            "fixed_point_output_bytes_required": True,
        },
    ]


def _document() -> dict[str, Any]:
    profiles = registry_v9.freeze_construction_accounting_registry_v9()
    registry = registry_v9.official_counter_registry_v9()
    registered_paths = {
        *MODEL_OPERATIONAL_PATHS,
        *PLANNING_OPERATIONAL_PATHS,
        *EVALUATION_PATHS,
        *SHARED_RESOURCE_PATHS,
    }
    if not registered_paths.issubset(registry.by_path):
        _fail("V36 accounting path is absent from CounterRegistryV9")
    payload = {
        "schema": "acfqp.standard_2048_adaptive_accounting_preregistration.v36",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "stage_separation_contract_correction": {
            "superseded_v36_preregistration_id": (
                SUPERSEDED_V36_PREREGISTRATION_ID
            ),
            "superseded_preregistration_executed": False,
            "outcomes_known_when_corrected": False,
            "scientific_target_or_workload_changed": False,
            "correction": (
                "SEPARATE_FAILURE_ACQUISITION_PROPOSAL_PROOF_OVERLAY_"
                "PLANNING_AND_EXECUTION_NATIVE_WINDOWS"
            ),
            "partial_superseded_bundles_may_be_reused": False,
        },
        "canonical_worker_task_failure_successor": {
            "failed_v36r1_preregistration_id": FAILED_V36R1_PREREGISTRATION_ID,
            "failed_execution_performed": True,
            "failure_phase": "PARENT_WORKER_TASK_CANONICALIZATION_BEFORE_EXECUTOR_CONSTRUCTION",
            "failure_class": "UNSUPPORTED_CANONICAL_JSON_TYPE",
            "failure_detail": "PYTHON_TUPLE_AT_CANONICAL_ROOT",
            "episode_worker_reply_count": 0,
            "accounted_campaign_issued": False,
            "independent_verification_issued": False,
            "partial_model_bundle_count": 6,
            "partial_model_bundles_may_be_reused": False,
            "partial_model_bundle_inventory": [
                {
                    "path": "model/evaluation-no-prior-control.json",
                    "byte_count": 575317,
                    "sha256": "8ec06a5b554880cd97bc464ac37e44725d9dc0239a663426807c2998f789db1c",
                    "counter_bundle_id": "5dc859105fad8efdcfcdab4148bbae59797dcc9a9ec5e20fbe8ebba4afa06488",
                },
                {
                    "path": "model/operational-acquisition.json",
                    "byte_count": 215272,
                    "sha256": "f401612c2b10f670793f6a91d4a70a4642b9a793b3ab75e9a85155333e9e89a8",
                    "counter_bundle_id": "d66c880b969a34e71db66b19079af4631c90addd1c7194fb7991dd9fbe6b56ed",
                },
                {
                    "path": "model/operational-failure-frontier.json",
                    "byte_count": 799895,
                    "sha256": "7f2174e3da9a3b4ffc421d3b9c5773c2f888c2eb8c6ce69e9a1f8412ac0975a0",
                    "counter_bundle_id": "933527d0e7fb203953d0530b3bb9e09ddd8123c0f7cd53cdb28ddbfeee898379",
                },
                {
                    "path": "model/operational-overlay.json",
                    "byte_count": 211795,
                    "sha256": "78fab44a18164e3a931cdc4f4c45e50d0eb6ef6ca9b30eadb670a55c2f159ef0",
                    "counter_bundle_id": "bf6673f4ec9183e1fa01c4486dc8519e0590366efc18d3ee23bcf1ffafe4a7f8",
                },
                {
                    "path": "model/operational-proof.json",
                    "byte_count": 210868,
                    "sha256": "c1b08618e4066aa8f2c530dfc4227fbc2f67165cd1d73d3b02bf95df95b475fa",
                    "counter_bundle_id": "ff6dfe782433fd927fa28cba23a620dd191b8649bea299f0e9c172fa8de96cec",
                },
                {
                    "path": "model/operational-proposal.json",
                    "byte_count": 225159,
                    "sha256": "5d2640d642776fd8fa76eeee262e251eaf056dd6075332b8c03c1824b970b664",
                    "counter_bundle_id": "290552dc927d8591f0662406adcbe7be5f7f80cad436613c164d2e94c2806fff",
                },
            ],
            "scientific_workload_changed": False,
            "planning_or_target_semantics_changed": False,
            "accounting_counter_semantics_changed": False,
            "correction": "REPLACE_UNTYPED_TUPLE_WITH_EXACT_CANONICAL_WORKER_TASK_OBJECT",
        },
        "worker_board_rehydration_failure_successor": {
            "failed_v36r2_preregistration_id": FAILED_V36R2_PREREGISTRATION_ID,
            "failed_execution_performed": True,
            "failure_phase": "FIRST_EPISODE_WORKER_BOARD_REHYDRATION_BEFORE_STATE_CREATION",
            "failure_class": "SWIPE_2048_INVARIANT_VIOLATION",
            "failure_detail": "CANONICAL_JSON_LIST_NOT_REHYDRATED_TO_DOMAIN_TUPLE",
            "episode_worker_process_launched": True,
            "episode_worker_reply_count": 0,
            "planning_session_created": False,
            "target_transition_accessed": False,
            "accounted_campaign_issued": False,
            "independent_verification_issued": False,
            "partial_model_bundle_count": 6,
            "partial_model_bundles_may_be_reused": False,
            "partial_model_bundle_inventory": [
                {
                    "path": "model/evaluation-no-prior-control.json",
                    "byte_count": 575317,
                    "sha256": "c8e7d9b68ffbc0815c6b931b56bf80023e10da71a78649b236ecc6a9cbe12df6",
                    "counter_bundle_id": "9bee01ae10616595f8cdca4678de44e3d122058a2289654acec1e3e22d550ee4",
                },
                {
                    "path": "model/operational-acquisition.json",
                    "byte_count": 215272,
                    "sha256": "2a34d9db0a86f99301e6e9bf78e496ebf428093a98967571b07260ecb5f07275",
                    "counter_bundle_id": "3b6bec4502652f789e32c19b7dc387df21340c84c873426e7cafb49026ae5524",
                },
                {
                    "path": "model/operational-failure-frontier.json",
                    "byte_count": 799895,
                    "sha256": "db8d23dae81df9650e67c7cab02758c86fb6fe712d30329499d81d5da5859c5e",
                    "counter_bundle_id": "f47bbaa941f5b3ee222f61c0debbf38c3bb98254686132f8fbff8210e659f217",
                },
                {
                    "path": "model/operational-overlay.json",
                    "byte_count": 211795,
                    "sha256": "ca7143e19f85abd32c84c60b8a74cb254e0c7c2ec7571d6f3beb136195b16a77",
                    "counter_bundle_id": "6526ccc6b09d1a4247639d274fc0c3779b334fc2b73c98712db74172fa2fb308",
                },
                {
                    "path": "model/operational-proof.json",
                    "byte_count": 210868,
                    "sha256": "f9d6e7a0adc913571b4c62e16327aeaf9c7f52f56eb387913fdc3b70db3aa094",
                    "counter_bundle_id": "561c95ecd18f736ae9b89274adab3f8c6be78123753182e4e56c6ebb710c74aa",
                },
                {
                    "path": "model/operational-proposal.json",
                    "byte_count": 225159,
                    "sha256": "307383a073b48699cea24dc7375e915385dd9b13fa7089bae380fc9ffc137522",
                    "counter_bundle_id": "a19160fd6edf8d81eda1c3e89674c370ac9106b4d18cce5754c79ca91f7c6bea",
                },
            ],
            "scientific_workload_changed": False,
            "planning_or_target_semantics_changed": False,
            "accounting_counter_semantics_changed": False,
            "correction": "REHYDRATE_16_ELEMENT_JSON_LIST_TO_IMMUTABLE_DOMAIN_TUPLE",
        },
        "frozen_predecessors": {
            "v34r1_accounting_preregistration_id": V34R1_PREREGISTRATION_ID,
            "v34r1_accounted_campaign_id": V34R1_ACCOUNTED_CAMPAIGN_ID,
            "v34r1_accounting_verification_id": V34R1_ACCOUNTING_VERIFICATION_ID,
            "v35_adaptive_expression_preregistration_id": V35_PREREGISTRATION_ID,
            "v35_adaptive_expression_campaign_id": V35_ADAPTIVE_EXPRESSION_CAMPAIGN_ID,
            "v35_adaptive_expression_verification_id": V35_ADAPTIVE_EXPRESSION_VERIFICATION_ID,
            "V35_execution_may_start_only_after_verified_V34r1": True,
            "V36_accounting_may_start_only_after_verified_V35": True,
        },
        "registered_workload": {
            "logical_occurrence_count": MAXIMUM_EPISODES,
            "planning_horizon": 3,
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "maximum_total_decisions": (
                MAXIMUM_EPISODES * MAXIMUM_DECISIONS_PER_EPISODE
            ),
            "maximum_target_probability_labels": MAXIMUM_TARGET_PROBABILITY_LABELS,
            "maximum_cold_evaluation_checkpoints": MAXIMUM_COLD_CHECKPOINTS,
            "early_terminal_closure_allowed": True,
            "all_terminal_occurrences_remain_in_denominator": True,
            "scientific_workload_must_equal_verified_V35_bytes": True,
        },
        "frozen_registry_profiles": profiles,
        "registered_stage_plan": _stage_plan(),
        "actual_accounting_protocol": {
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": profiles["stage_profile"]["stage_profile_id"],
            "comparison_profile_id": profiles["comparison_profile"][
                "comparison_profile_id"
            ],
            "actual_projection_profile_id": profiles[
                "actual_projection_profile"
            ]["actual_projection_profile_id"],
            "model_operational_paths": list(MODEL_OPERATIONAL_PATHS),
            "planning_operational_paths": list(PLANNING_OPERATIONAL_PATHS),
            "evaluation_paths": list(EVALUATION_PATHS),
            "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
            "fresh_native_counter_window_required_for_every_stage": True,
            "all_required_leaves_emit_native_zero": True,
            "output_bytes_use_fixed_point_materialization": True,
            "evaluation_lane_excluded_from_operational_comparison": True,
            "summary_to_counter_translation_allowed": False,
            "maximum_worker_processes": MAXIMUM_WORKER_PROCESSES,
            "maximum_tasks_per_worker_process": MAXIMUM_TASKS_PER_WORKER_PROCESS,
            "worker_working_bytes_peak_upper": WORKER_WORKING_BYTES_PEAK_UPPER,
            "parent_working_bytes_peak_upper": PARENT_WORKING_BYTES_PEAK_UPPER,
            "maximum_accounting_output_bytes": MAXIMUM_ACCOUNTING_OUTPUT_BYTES,
            "resource_caps_frozen_before_execution": True,
            "worker_task_schema": {
                "schema": "acfqp.standard_2048_adaptive_accounting_worker_task.v36",
                "schema_version": SCHEMA_VERSION,
                "exact_fields": [
                    "adaptive_accounting_preregistration_id",
                    "candidate",
                    "episode_index",
                    "execution_seed",
                    "initial_board_ranks",
                    "overlay",
                    "schema",
                    "schema_version",
                ],
                "canonical_root_type": "OBJECT",
                "domain_board_rehydration": "JSON_LIST_TO_EXACT_16_RANK_TUPLE",
            },
        },
        "required_positive_conditions": [
            "V34R1_ACCOUNTING_AND_V35_SEMANTICS_VERIFY_BEFORE_ACCOUNTING",
            "FAILURE_ACQUISITION_PROPOSAL_PROOF_OVERLAY_AND_EXECUTION_ARE_SEPARATE",
            "EVERY_OPERATIONAL_LEAF_PROJECTS_EXACTLY_ONCE",
            "ALL_NINE_SHARED_RESOURCE_PATHS_HAVE_NATIVE_MEASUREMENT_RECEIPTS",
            "EVERY_WORKER_PROCESS_EXECUTES_EXACTLY_ONE_OCCURRENCE",
            "EVALUATION_CONTROL_AND_COLD_REPLAY_NEVER_ENTER_OPERATIONAL_COMPARISON",
            "COUNTER_RECORD_WORK_VECTOR_COMPARISON_VECTOR_CHAIN_REPLAYS",
        ],
        "outcome_fields_present": False,
        "failed_predecessor_evidence_present": True,
        "accounting_execution_performed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "automatic_reusable_world_model_goal_completed": False,
        "broad_iid_or_cross_domain_sample_efficiency_claimed": False,
        "total_operational_work_saving_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "adaptive_accounting_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveAccountingPreregistrationV36:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("adaptive-accounting preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("adaptive-accounting preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_accounting_preregistration_id"
        }
        if (
            document.get("adaptive_accounting_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("adaptive-accounting preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("adaptive-accounting preregistration is not an object")
        return document


def freeze_standard_2048_adaptive_accounting_preregistration_v36(
) -> Standard2048AdaptiveAccountingPreregistrationV36:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["adaptive_accounting_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen adaptive-accounting preregistration changed")
    return Standard2048AdaptiveAccountingPreregistrationV36(
        _ISSUER, raw, identity
    )


def verify_standard_2048_adaptive_accounting_preregistration_v36(
    value: Standard2048AdaptiveAccountingPreregistrationV36,
) -> Standard2048AdaptiveAccountingPreregistrationV36:
    if type(value) is not Standard2048AdaptiveAccountingPreregistrationV36:
        _fail("adaptive-accounting preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("adaptive-accounting preregistration semantics changed")
    return value


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "MODEL_OPERATIONAL_PATHS",
    "PLANNING_OPERATIONAL_PATHS",
    "PREREGISTRATION_ID",
    "SHARED_RESOURCE_PATHS",
    "SUPERSEDED_V36_PREREGISTRATION_ID",
    "Standard2048AdaptiveAccountingPreregistrationV36",
    "freeze_standard_2048_adaptive_accounting_preregistration_v36",
    "verify_standard_2048_adaptive_accounting_preregistration_v36",
)
