"""Measurement registration for the complete exact 2048 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v26 as v26
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v27 as v27
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v28 as v28
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v29 as v29
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v30 as v30
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v31 as v31
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v32 as v32
from acfqp import construction_k7_standard_2048_expression_checkpoint_preregistration_v33 as v33
from acfqp import construction_k7_standard_2048_expression_long_preregistration_v23 as v23
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_CAMPAIGN_V34_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_COUNTER_BUNDLE_V34_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_EPISODE_V34_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_MEASUREMENT_V34_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_PREREGISTRATION_V34_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_SEGMENT_V34_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_VERIFICATION_V34_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "34.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.194"
PROFILE_KEY = "construction_k7_standard_2048_expression_full_actual_accounting_v34r1"
PREREGISTRATION_ID = "4546af82f1f4e6429c83148b0f37f9a3995b80e9a0bb4abc2971ada13b115920"
EXPECTED_CANONICAL_BYTE_COUNT = 219225
EXPECTED_CANONICAL_SHA256 = "e29962aad3910c94bc1a3f09d11b8e57eac35266c4e750dbfa8683e4954dbc3b"
FAILED_V34_PREREGISTRATION_ID = (
    "9a02a999b32b3753c4cbfc9dde0baf7b783f661e696875d5bbf97d986bbc3fc5"
)
V33_PREREGISTRATION_ID = "00c9afa984008a065e31b955b3ff8802cb94b5c5e2998e78ced9827a9b83c66b"
V33_CAMPAIGN_ID = "9aface12cb25891de77588b4d25fe1526b0266515fd137b89478c162c1242bd5"
V33_VERIFICATION_ID = "bea5881b9b92f49e603d46160d29f88fbee3eea46f35300efe6c4b1782cbb6f4"
V24_ACCOUNTED_CAMPAIGN_ID = "3eba16cb6db6d0797991acbde6103d423741668730313385e404949b5907ab72"
V24_ACCOUNTING_VERIFICATION_ID = "79749d6a1d689ee4cb8740d2b20393d11403d29471f9a218e4a4a5b36720aca7"
V25_SEMANTIC_VERIFICATION_ID = "0c9957d0d5a7832ef0a9e2f9cfe0bb2ab1e2329b990f89c5d12e2498957fe258"
WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
EXPECTED_COMPLETE_DECISION_COUNT = 3187
EXPECTED_WON_OCCURRENCE_COUNT = 2
EXPECTED_LOST_OCCURRENCE_COUNT = 2
MAXIMUM_WORKER_PROCESSES = 2
MAXIMUM_TASKS_PER_WORKER_PROCESS = 1
FAILED_V31_OBSERVED_RSS_LOWER_BOUND_KIB = 18_170_916
WORKER_WORKING_BYTES_PEAK_UPPER = 24 * 1024 * 1024 * 1024
PARENT_WORKING_BYTES_PEAK_UPPER = 4 * 1024 * 1024 * 1024
MAXIMUM_ACCOUNTING_OUTPUT_BYTES = 2 * 1024 * 1024 * 1024

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_PREREGISTRATION_V34_DOMAIN,
    "measurement": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_MEASUREMENT_V34_DOMAIN,
    "counter_bundle": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_COUNTER_BUNDLE_V34_DOMAIN,
    "segment": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_SEGMENT_V34_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_EPISODE_V34_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_CAMPAIGN_V34_DOMAIN,
    "verification": CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_VERIFICATION_V34_DOMAIN,
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
MODEL_EVALUATION_PATHS = tuple(
    "evaluation." + path.removeprefix("model.") for path in MODEL_OPERATIONAL_PATHS
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


class ConstructionK7Standard2048ExpressionFullAccountingPreregistrationV34Error(
    ValueError
):
    """The complete campaign, measurement profile, or claim lock changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionFullAccountingPreregistrationV34Error(
        message
    )


def _segment(
    *,
    profile: str,
    preregistration_id: str,
    source_episode_ids: tuple[str, ...] | None,
    boards: tuple[tuple[int, ...], ...],
    statuses: tuple[str, ...],
    source_counts: tuple[int, ...],
    decision_limit: int,
    expected_decision_count: int,
) -> dict[str, Any]:
    return {
        "profile": profile,
        "source_preregistration_id": preregistration_id,
        "source_episode_ids": None if source_episode_ids is None else list(source_episode_ids),
        "checkpoint_boards": [list(board) for board in boards],
        "checkpoint_status": list(statuses),
        "source_decision_counts": list(source_counts),
        "decision_limit_per_active_occurrence": decision_limit,
        "expected_new_decision_count": expected_decision_count,
        "cache_is_fresh_at_segment_start": True,
        "only_active_occurrences_may_execute": True,
        "terminal_occurrences_emit_zero_decision_work": True,
    }


def _segment_plan() -> list[dict[str, Any]]:
    return [
        _segment(
            profile="V23_INITIAL_32",
            preregistration_id=v23.PREREGISTRATION_ID,
            source_episode_ids=None,
            boards=v23.INITIAL_BOARDS,
            statuses=("ACTIVE",) * 4,
            source_counts=(0, 0, 0, 0),
            decision_limit=v23.MAXIMUM_DECISIONS_PER_EPISODE,
            expected_decision_count=128,
        ),
        _segment(profile="V26", preregistration_id=v26.PREREGISTRATION_ID, source_episode_ids=v26.CHECKPOINT_EPISODE_IDS, boards=v26.CHECKPOINT_BOARDS, statuses=("ACTIVE",) * 4, source_counts=(32,) * 4, decision_limit=v26.SEGMENT_DECISION_LIMIT, expected_decision_count=128),
        _segment(profile="V27", preregistration_id=v27.PREREGISTRATION_ID, source_episode_ids=v27.CHECKPOINT_EPISODE_IDS, boards=v27.CHECKPOINT_BOARDS, statuses=("ACTIVE",) * 4, source_counts=(64,) * 4, decision_limit=v27.SEGMENT_DECISION_LIMIT, expected_decision_count=128),
        _segment(profile="V28", preregistration_id=v28.PREREGISTRATION_ID, source_episode_ids=v28.CHECKPOINT_EPISODE_IDS, boards=v28.CHECKPOINT_BOARDS, statuses=("ACTIVE",) * 4, source_counts=(96,) * 4, decision_limit=v28.SEGMENT_DECISION_LIMIT, expected_decision_count=128),
        _segment(profile="V29", preregistration_id=v29.PREREGISTRATION_ID, source_episode_ids=v29.CHECKPOINT_EPISODE_IDS, boards=v29.CHECKPOINT_BOARDS, statuses=("ACTIVE",) * 4, source_counts=(128,) * 4, decision_limit=v29.SEGMENT_DECISION_LIMIT, expected_decision_count=256),
        _segment(profile="V30", preregistration_id=v30.PREREGISTRATION_ID, source_episode_ids=v30.CHECKPOINT_EPISODE_IDS, boards=v30.CHECKPOINT_BOARDS, statuses=("ACTIVE",) * 4, source_counts=(192,) * 4, decision_limit=v30.SEGMENT_DECISION_LIMIT, expected_decision_count=512),
        _segment(profile="V31", preregistration_id=v31.PREREGISTRATION_ID, source_episode_ids=v31.CHECKPOINT_EPISODE_IDS, boards=v31.CHECKPOINT_BOARDS, statuses=("ACTIVE",) * 4, source_counts=(320,) * 4, decision_limit=v31.SEGMENT_DECISION_LIMIT, expected_decision_count=938),
        _segment(profile="V32", preregistration_id=v32.PREREGISTRATION_ID, source_episode_ids=v32.CHECKPOINT_EPISODE_IDS, boards=v32.CHECKPOINT_BOARDS, statuses=v32.CHECKPOINT_STATUSES, source_counts=v32.SOURCE_DECISION_COUNTS, decision_limit=v32.SEGMENT_DECISION_LIMIT, expected_decision_count=765),
        _segment(profile="V33", preregistration_id=v33.PREREGISTRATION_ID, source_episode_ids=v33.CHECKPOINT_EPISODE_IDS, boards=v33.CHECKPOINT_BOARDS, statuses=v33.CHECKPOINT_STATUSES, source_counts=v33.SOURCE_DECISION_COUNTS, decision_limit=v33.SEGMENT_DECISION_LIMIT, expected_decision_count=204),
    ]


def _document() -> dict[str, Any]:
    frozen = registry_v9.freeze_construction_accounting_registry_v9()
    registry = registry_v9.official_counter_registry_v9()
    paths = (*MODEL_OPERATIONAL_PATHS, *MODEL_EVALUATION_PATHS)
    if any(path not in registry.by_path for path in paths):
        _fail("full accounting model path is not registered")
    segments = _segment_plan()
    if sum(row["expected_new_decision_count"] for row in segments) != EXPECTED_COMPLETE_DECISION_COUNT:
        _fail("registered complete decision count changed")
    payload = {
        "schema": "acfqp.standard_2048_expression_full_accounting_preregistration.v34",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "measurement_predecessors": {
            "v33_preregistration_id": V33_PREREGISTRATION_ID,
            "v33_complete_campaign_id": V33_CAMPAIGN_ID,
            "v33_independent_verification_id": V33_VERIFICATION_ID,
            "v24_accounted_campaign_id": V24_ACCOUNTED_CAMPAIGN_ID,
            "v24_accounting_verification_id": V24_ACCOUNTING_VERIFICATION_ID,
            "v25_semantic_verification_id": V25_SEMANTIC_VERIFICATION_ID,
            "expression_world_model_id": WORLD_MODEL_ID,
            "measurement_replays_already_revealed_complete_campaign": True,
            "fresh_blind_scientific_confirmation_claimed": False,
            "predecessor_summary_counters_relabelled_as_actual": False,
        },
        "resource_cap_correction": {
            "failed_v34_preregistration_id": FAILED_V34_PREREGISTRATION_ID,
            "failed_attempt_terminal_code": "WORKER_WORKING_SET_CAP_EXCEEDED",
            "failed_attempt_formal_campaign_id": None,
            "failed_attempt_formal_verification_id": None,
            "failed_attempt_v31_observed_rss_lower_bound_kib": (
                FAILED_V31_OBSERVED_RSS_LOWER_BOUND_KIB
            ),
            "failed_attempt_worker_working_bytes_peak_upper": (
                16 * 1024 * 1024 * 1024
            ),
            "corrected_worker_working_bytes_peak_upper": (
                WORKER_WORKING_BYTES_PEAK_UPPER
            ),
            "maximum_tasks_per_worker_process": MAXIMUM_TASKS_PER_WORKER_PROCESS,
            "worker_recycling_prevents_cross_occurrence_cache_retention": True,
            "all_nine_segments_must_rerun": True,
            "failed_attempt_partial_bundles_may_be_reused": False,
            "scientific_target_or_workload_changed": False,
        },
        "frozen_registry_profiles": frozen,
        "registered_segment_plan": segments,
        "registered_complete_campaign": {
            "logical_occurrence_count": 4,
            "expected_complete_decision_count": EXPECTED_COMPLETE_DECISION_COUNT,
            "expected_won_occurrence_count": EXPECTED_WON_OCCURRENCE_COUNT,
            "expected_lost_occurrence_count": EXPECTED_LOST_OCCURRENCE_COUNT,
            "planning_horizon": 3,
            "inherited_target_probability_label_count": 4,
            "additional_target_probability_label_count": 0,
            "strict_no_prior_target_probability_label_count": 8,
            "terminal_occurrences_remain_in_all_denominators": True,
        },
        "actual_accounting_protocol": {
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": frozen["stage_profile"]["stage_profile_id"],
            "comparison_profile_id": frozen["comparison_profile"]["comparison_profile_id"],
            "actual_projection_profile_id": frozen["actual_projection_profile"]["actual_projection_profile_id"],
            "model_operational_paths": list(MODEL_OPERATIONAL_PATHS),
            "model_evaluation_paths": list(MODEL_EVALUATION_PATHS),
            "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
            "fresh_native_counter_window_required_for_every_segment": True,
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
        },
        "required_positive_conditions": [
            "ALL_NINE_SEGMENTS_RERUN_UNDER_NATIVE_COUNTER_WINDOWS",
            "ALL_3187_DECISIONS_REPRODUCED_WITH_EXACT_IDS_AND_TRANSITIONS",
            "TWO_WON_AND_TWO_LOST_OCCURRENCES_REPRODUCED",
            "EVERY_OPERATIONAL_LEAF_PROJECTS_EXACTLY_ONCE",
            "NINE_SHARED_RESOURCE_PATHS_HAVE_NATIVE_MEASUREMENT_RECEIPTS",
            "EVERY_WORKER_PROCESS_EXECUTES_EXACTLY_ONE_OCCURRENCE",
            "EVALUATION_REPLAY_NEVER_ENTERS_OPERATIONAL_COMPARISON",
        ],
        "outcome_fields_present": False,
        "full_accounting_execution_performed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "expression_full_accounting_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionFullAccountingPreregistrationV34:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("full accounting preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("full accounting preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "expression_full_accounting_preregistration_id"
        }
        if (
            document.get("expression_full_accounting_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("full accounting preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("full accounting preregistration is not an object")
        return document


def freeze_standard_2048_expression_full_accounting_preregistration_v34(
) -> Standard2048ExpressionFullAccountingPreregistrationV34:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["expression_full_accounting_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen full accounting preregistration changed")
    return Standard2048ExpressionFullAccountingPreregistrationV34(
        _ISSUER, raw, identity
    )


def verify_standard_2048_expression_full_accounting_preregistration_v34(
    value: Standard2048ExpressionFullAccountingPreregistrationV34,
) -> Standard2048ExpressionFullAccountingPreregistrationV34:
    if type(value) is not Standard2048ExpressionFullAccountingPreregistrationV34:
        _fail("full accounting preregistration verifier rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("full accounting preregistration semantics changed")
    return value


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_COMPLETE_DECISION_COUNT",
    "FUTURE_DOMAINS",
    "MAXIMUM_WORKER_PROCESSES",
    "MAXIMUM_TASKS_PER_WORKER_PROCESS",
    "MODEL_EVALUATION_PATHS",
    "MODEL_OPERATIONAL_PATHS",
    "PREREGISTRATION_ID",
    "SHARED_RESOURCE_PATHS",
    "Standard2048ExpressionFullAccountingPreregistrationV34",
    "freeze_standard_2048_expression_full_accounting_preregistration_v34",
    "verify_standard_2048_expression_full_accounting_preregistration_v34",
)
