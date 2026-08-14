"""Resource-successor registration of the second adaptive-model continuation.

The V35 expression model is already proved against its committed target and
V36 independently accounts its acquisition and 128-decision execution.  This
V37 extends all four episodes to decision 256 and independently replays every
certificate and transition.  This registration freezes those live checkpoints
before a 256-decision continuation.  The first four-worker V38 execution was
closed by a kernel OOM kill before any campaign artifact was issued.  V39 keeps
the scientific workload byte-for-byte but freezes two fresh two-worker waves.
No new target-probability label is permitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as v35
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V39_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V39_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V39_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V39_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V39_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "39.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.202"
PROFILE_KEY = "construction_k7_standard_2048_adaptive_checkpoint_resource_successor_v39"
PREREGISTRATION_ID = "bb81a2d6e5241778577d6ed792fed2684cfd391e01613fda0c5931890876ce57"
EXPECTED_CANONICAL_BYTE_COUNT = 7_143
EXPECTED_CANONICAL_SHA256 = "ce674e5cd3829fb4917f0f75d5e4d36827326814773b583a7d6e146770e2604d"

V35_PREREGISTRATION_ID = (
    "d2705f1b310b2f88f41799376a69f55b3355b53a54a2a103ba11e5dbf00491a9"
)
V35_CAMPAIGN_ID = (
    "c33002f8bac5415d94c5185876ce104ac859243e7b50ee5922c1be9b4a812d25"
)
V35_VERIFICATION_ID = (
    "0591b03140cb3e807b68ee4e90129c93863a45ef29ed44896df49c7d4caea348"
)
V36R4_PREREGISTRATION_ID = (
    "78494b3a611b198a99e00d324eb570ba3a6b6346e3c432c93a47d0456835de2a"
)
V36R4_CAMPAIGN_ID = (
    "758f01ac78789d25512b218ed16b8ca4bfaa95a08dc52e81fc15601b42662693"
)
V36R4_VERIFICATION_ID = (
    "ed3354625ab6c3e8928bdf0b0807ee7e7c47a2c5c84a0e364916fc1ac2e94c14"
)
V37_PREREGISTRATION_ID = (
    "21b57b71109fd4e562fbdbd1d3c124def39f951e86b6d810f3519e3154c7e6c1"
)
V37_CAMPAIGN_ID = (
    "1815a8b69f9ceb2998bf1adf3750149d38a870cd45fef341ac7ec9e8b7254647"
)
V37_VERIFICATION_ID = (
    "203637f5ae0523b73f324bc0ea745fef213b0038c4a584f40f41fa4915b1444d"
)
FAILED_V38_PREREGISTRATION_ID = (
    "c5ebad603186d90d17c635416b60a18f6d0159e76def4d86eac509a2d4fa1e3b"
)
FAILED_V38_RUNNER_SOURCE_BYTE_COUNT = 18_809
FAILED_V38_RUNNER_SOURCE_SHA256 = (
    "e28249a878d546a095b4e14ff2d254612aa3169da028691b52e024ae5cd1454b"
)
TARGET_KERNEL_ID = (
    "e542f25f3929b78c3dd622beaf632df1fee75a775de99bead1232a8a8a936236"
)
ADAPTIVE_EXPRESSION_OVERLAY_ID = (
    "36996bf7b4394e51c1d8a0ef74c50dc9ce5157d28c39ba75d92aae84c9b9f178"
)
ADAPTIVE_EXPRESSION_PROPOSAL_ID = (
    "48abfadba373a858c8261864f77878c65c0f13e3c6f57f94100a9be23023f2b9"
)
ADAPTIVE_EXPRESSION_PROOF_ID = (
    "24e04000e8aa600ba9186618fc2e9fefa37df33fed57e088fef3ed26c83496d5"
)
ADAPTIVE_EXPRESSION_CANDIDATE_ID = (
    "d296cdeb05cc1be50970c7e131d556118b22060ab95a075a67ad4d03e43af82b"
)

PLANNING_HORIZON = 3
SOURCE_DECISION_COUNT = 256
SEGMENT_DECISION_LIMIT = 256
GLOBAL_DECISION_START = 256
GLOBAL_DECISION_STOP_EXCLUSIVE = 512
LOCAL_COLD_CHECKPOINTS = (0, 127, 255)
GLOBAL_COLD_CHECKPOINTS = (256, 383, 511)
INHERITED_TARGET_PROBABILITY_LABEL_COUNT = 6
STRICT_NO_PRIOR_CONTEXT_LABEL_COUNT = 2400

CHECKPOINT_EPISODE_IDS = (
    "99405c26b3b45995b06c768d9d5f96b98a07e7443f8fe20a1f55947e0b7f3707",
    "734a6404e1e3f4c4f2b9bf1daf04b0af40fcaee6f9727c1e171610a313079f82",
    "3442ee469fb68535f04cf12e47f76b274090489022e034edb429256fa233a336",
    "a9b99bf73196356f0f55211e468a56b02206e1d490ae7341362c8899c3c824fa",
)
CHECKPOINT_BOARDS = (
    (0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 2, 2, 3, 9, 6, 4),
    (4, 9, 2, 2, 0, 6, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0),
    (0, 1, 0, 1, 0, 0, 2, 9, 0, 0, 6, 5, 0, 0, 2, 2),
    (0, 0, 0, 1, 1, 0, 4, 3, 0, 2, 9, 5, 1, 1, 2, 4),
)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V39_DOMAIN,
    "certificate": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V39_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V39_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V39_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V39_DOMAIN,
}


class ConstructionK7Standard2048AdaptiveCheckpointPreregistrationV39Error(
    ValueError
):
    """The checkpoint, learned model, continuation, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AdaptiveCheckpointPreregistrationV39Error(
        message
    )


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_adaptive_checkpoint_preregistration.v39",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v35_adaptive_expression_preregistration_id": V35_PREREGISTRATION_ID,
            "v35_adaptive_expression_campaign_id": V35_CAMPAIGN_ID,
            "v35_adaptive_expression_verification_id": V35_VERIFICATION_ID,
            "v36r4_accounting_preregistration_id": V36R4_PREREGISTRATION_ID,
            "v36r4_accounted_campaign_id": V36R4_CAMPAIGN_ID,
            "v36r4_accounting_verification_id": V36R4_VERIFICATION_ID,
            "v37_adaptive_checkpoint_preregistration_id": V37_PREREGISTRATION_ID,
            "v37_adaptive_checkpoint_campaign_id": V37_CAMPAIGN_ID,
            "v37_adaptive_checkpoint_verification_id": V37_VERIFICATION_ID,
            "failed_v38_adaptive_checkpoint_preregistration_id": (
                FAILED_V38_PREREGISTRATION_ID
            ),
            "all_predecessor_identities_frozen_before_v39_execution": True,
        },
        "failed_v38_resource_attempt": {
            "runner_relative_path": (
                "src/acfqp/construction_k7_standard_2048_"
                "adaptive_checkpoint_campaign_v38.py"
            ),
            "runner_source_byte_count": FAILED_V38_RUNNER_SOURCE_BYTE_COUNT,
            "runner_source_sha256": FAILED_V38_RUNNER_SOURCE_SHA256,
            "maximum_concurrent_worker_processes": 4,
            "registered_episode_task_count": 4,
            "failure_exception_type": "BrokenProcessPool",
            "failure_exception_message": (
                "A process in the process pool was terminated abruptly while "
                "the future was running or pending."
            ),
            "kernel_failure_class": "GLOBAL_OOM_KILL",
            "kernel_journal_timestamp_local": "2026-08-14T18:29:34+08:00",
            "killed_process_comm": "python3",
            "killed_process_total_vm_kib": 12_966_876,
            "killed_process_anon_rss_kib": 11_657_504,
            "campaign_artifact_byte_count": 0,
            "campaign_identity_issued": False,
            "durable_episode_artifact_count": 0,
            "partial_or_failed_output_may_be_reused": False,
            "scientific_workload_changed": False,
            "target_or_planning_semantics_changed": False,
        },
        "resource_successor_protocol": {
            "maximum_concurrent_worker_processes": 2,
            "execution_wave_count": 2,
            "episode_tasks_per_wave": 2,
            "maximum_tasks_per_worker_process": 1,
            "fresh_executor_required_for_each_wave": True,
            "all_v38_partial_memory_state_reused": False,
            "all_v38_partial_scientific_outputs_reused": False,
            "only_process_schedule_and_memory_concurrency_changed": True,
            "campaign_aggregation_waits_for_all_four_fresh_episode_results": True,
        },
        "proved_reusable_world_model": {
            "target_kernel_id": TARGET_KERNEL_ID,
            "adaptive_expression_overlay_id": ADAPTIVE_EXPRESSION_OVERLAY_ID,
            "adaptive_expression_proposal_id": ADAPTIVE_EXPRESSION_PROPOSAL_ID,
            "adaptive_expression_proof_id": ADAPTIVE_EXPRESSION_PROOF_ID,
            "adaptive_expression_candidate_id": ADAPTIVE_EXPRESSION_CANDIDATE_ID,
            "expression_ast": {
                "operator": "COUNT_EQ",
                "vector_source": "POST_SWIPE_BOARD_RANKS",
                "constant": 2,
            },
            "direction": "LE_OVERRIDE",
            "threshold": 1,
            "base_rank_two_probability": {"numerator": 1, "denominator": 10},
            "override_rank_two_probability": {"numerator": 1, "denominator": 4},
            "selected_only_after_certificate_triggered_local_acquisition": True,
            "semantically_proved_exact_before_checkpoint_registration": True,
            "serialized_target_probability_table_present": False,
        },
        "checkpoint_workload": {
            "source_episode_ids": list(CHECKPOINT_EPISODE_IDS),
            "checkpoint_boards": [list(board) for board in CHECKPOINT_BOARDS],
            "checkpoint_status": ["ACTIVE"] * len(CHECKPOINT_BOARDS),
            "episode_seeds": list(v35.EPISODE_SEEDS),
            "episode_count": len(CHECKPOINT_BOARDS),
            "source_decision_count": SOURCE_DECISION_COUNT,
            "global_decision_start_inclusive": GLOBAL_DECISION_START,
            "global_decision_stop_exclusive": GLOBAL_DECISION_STOP_EXCLUSIVE,
            "segment_decision_limit": SEGMENT_DECISION_LIMIT,
            "planning_horizon": PLANNING_HORIZON,
            "local_cold_checkpoint_indices": list(LOCAL_COLD_CHECKPOINTS),
            "global_cold_checkpoint_indices": list(GLOBAL_COLD_CHECKPOINTS),
            "early_terminal_closure_allowed": True,
        },
        "exact_checkpoint_protocol": {
            "one_empty_exact_subproof_cache_at_segment_start": True,
            "cache_reused_within_segment": True,
            "fraction_or_precision_approximation_allowed": False,
            "certificate_frozen_before_target_transition": True,
            "target_seed_decision_index_uses_global_offset": True,
            "execution_transition_may_modify_world_model": False,
            "new_frontier_disagreement_may_be_hidden": False,
            "certificate_failure_closes_segment_before_any_unregistered_query": True,
        },
        "sample_tax_contract": {
            "inherited_target_probability_label_count": INHERITED_TARGET_PROBABILITY_LABEL_COUNT,
            "additional_model_acquisition_label_budget": 0,
            "strict_no_prior_context_label_count": STRICT_NO_PRIOR_CONTEXT_LABEL_COUNT,
            "inherited_label_fraction_of_no_prior": {
                "numerator": 1,
                "denominator": 400,
            },
            "sample_count_and_planning_compute_remain_separate_axes": True,
            "positive_result_requires_all_certificates_and_transitions_to_replay": True,
        },
        "required_positive_conditions": [
            "ALL_SOURCE_CHECKPOINT_IDENTITIES_MATCH_VERIFIED_V37",
            "V36R4_ACCOUNTING_VERIFICATION_PRECEDES_V39_EXECUTION",
            "V37_PRODUCER_FREE_VERIFICATION_PRECEDES_V39_EXECUTION",
            "FAILED_V38_OOM_ATTEMPT_PRESERVED_AND_NOT_REUSED",
            "TWO_FRESH_TWO_WORKER_WAVES_REPLACE_FOUR_WORKER_CONCURRENCY",
            "ALL_SEGMENT_PLANS_USE_THE_PROVED_V35_EXPRESSION_MODEL",
            "ZERO_ADDITIONAL_TARGET_PROBABILITY_LABELS",
            "ALL_REGISTERED_COLD_CHECKPOINTS_MATCH_EXACT_GROUND",
            "ALL_SEEDED_TRANSITIONS_USE_GLOBAL_DECISION_INDICES",
        ],
        "outcome_fields_present": False,
        "checkpoint_execution_performed": False,
        "terminal_or_tile_2048_reached": False,
        "full_standard_2048_game_claimed": False,
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
        "adaptive_checkpoint_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048AdaptiveCheckpointPreregistrationV39:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("adaptive checkpoint preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
        ):
            _fail("adaptive checkpoint preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "adaptive_checkpoint_preregistration_id"
        }
        if (
            document.get("adaptive_checkpoint_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("adaptive checkpoint preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("adaptive checkpoint preregistration is not an object")
        return document


def freeze_standard_2048_adaptive_checkpoint_preregistration_v39(
) -> Standard2048AdaptiveCheckpointPreregistrationV39:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["adaptive_checkpoint_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen adaptive checkpoint preregistration changed")
    return Standard2048AdaptiveCheckpointPreregistrationV39(
        _ISSUER, raw, identity
    )


def verify_standard_2048_adaptive_checkpoint_preregistration_v39(
    value: Standard2048AdaptiveCheckpointPreregistrationV39,
) -> Standard2048AdaptiveCheckpointPreregistrationV39:
    if type(value) is not Standard2048AdaptiveCheckpointPreregistrationV39:
        _fail("adaptive checkpoint preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("adaptive checkpoint preregistration semantics changed")
    return value


__all__ = (
    "ADAPTIVE_EXPRESSION_CANDIDATE_ID",
    "ADAPTIVE_EXPRESSION_OVERLAY_ID",
    "ADAPTIVE_EXPRESSION_PROOF_ID",
    "ADAPTIVE_EXPRESSION_PROPOSAL_ID",
    "CHECKPOINT_BOARDS",
    "CHECKPOINT_EPISODE_IDS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "PREREGISTRATION_ID",
    "Standard2048AdaptiveCheckpointPreregistrationV39",
    "freeze_standard_2048_adaptive_checkpoint_preregistration_v39",
    "verify_standard_2048_adaptive_checkpoint_preregistration_v39",
)
