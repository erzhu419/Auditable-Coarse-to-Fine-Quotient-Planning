"""Outcome-free registration of full fresh-board standard-2048 V42.

V41 is evidence for a decision-768 continuation only.  This successor instead
starts every registered episode from an exactly-two-tile board with
``decision_index == 0`` and follows one frozen V35 expression world model until
WON, LOST, or a fail-closed 2,048-decision cap.  No transition outcome is
materialized by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp import construction_k7_standard_2048_history_manifest_v42 as history
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.205"
PROFILE_KEY = "construction_k7_standard_2048_fresh_to_terminal_v42"
PREREGISTRATION_ID = "575e06a306c9dcee816bc5d1ba431ef163d084ae174614d4b3b1b4b4358ff5b3"
EXPECTED_CANONICAL_BYTE_COUNT = 10_010
EXPECTED_CANONICAL_SHA256 = "b7946d186fdcad9b86417b7e9fff655cc3995d7c2d5d0619db43832e1bbaf485"

V35_PREREGISTRATION_ID = (
    "d2705f1b310b2f88f41799376a69f55b3355b53a54a2a103ba11e5dbf00491a9"
)
V35_CAMPAIGN_ID = (
    "c33002f8bac5415d94c5185876ce104ac859243e7b50ee5922c1be9b4a812d25"
)
V35_VERIFICATION_ID = (
    "0591b03140cb3e807b68ee4e90129c93863a45ef29ed44896df49c7d4caea348"
)
V41_PREREGISTRATION_ID = (
    "4298e79e9f8aee401901efb2d534e55954d7cd43932da891f51f7daeb52f6dd7"
)
V41_CAMPAIGN_ID = (
    "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732"
)
V41_VERIFICATION_ID = (
    "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396"
)
TARGET_KERNEL_ID = (
    "e542f25f3929b78c3dd622beaf632df1fee75a775de99bead1232a8a8a936236"
)
ADAPTIVE_EXPRESSION_OVERLAY_ID = (
    "36996bf7b4394e51c1d8a0ef74c50dc9ce5157d28c39ba75d92aae84c9b9f178"
)
ADAPTIVE_EXPRESSION_PROOF_ID = (
    "24e04000e8aa600ba9186618fc2e9fefa37df33fed57e088fef3ed26c83496d5"
)
ADAPTIVE_EXPRESSION_MODEL_ID = (
    "d296cdeb05cc1be50970c7e131d556118b22060ab95a075a67ad4d03e43af82b"
)
PLANNER_SOURCE_FACT = {
    "relative_path": "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
    "byte_count": 15_747,
    "sha256": "c2f06fcd78e41683544d243d23a4bdb5891b0523fbaa84ce771614c551f0aae2",
}
PLANNER_IDENTITY_PAYLOAD = {
    "schema": "acfqp.standard_2048_fresh_terminal_planner_identity.v42",
    "schema_version": SCHEMA_VERSION,
    "planner_source_fact": PLANNER_SOURCE_FACT,
    "planner_entrypoint": "create_expression_planning_session_v1",
    "planning_horizon": 3,
    "persistent_exact_subproof_cache_within_one_process_episode": True,
    "crash_resume_or_cross_process_cache_persistence_claimed": False,
}
PLANNER_ID = domains.extension_content_id_v42(
    domains.CONSTRUCTION_K7_PLANNER_IDENTITY_V42_DOMAIN,
    PLANNER_IDENTITY_PAYLOAD,
)

PLANNING_HORIZON = 3
INITIAL_DECISION_INDEX = 0
MAXIMUM_DECISIONS_PER_EPISODE = 2_048
INHERITED_TARGET_PROBABILITY_LABEL_COUNT = 6
ADDITIONAL_MODEL_LABEL_BUDGET = 0
INITIAL_BOARDS = (
    (2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)
EPISODE_SEEDS = (
    "standard-2048-v42-fresh-terminal-00-7f3c8b19-20260827",
    "standard-2048-v42-fresh-terminal-01-92a64de5-20260827",
)

FUTURE_DOMAINS = {
    key: domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V42[key]
    for key in (
        "source_binding",
        "source_manifest",
        "prepare_receipt",
        "prepare_journal",
        "launch_journal",
        "worker_start",
        "authority_consumption",
        "plan_certificate",
        "transition_step",
        "episode",
        "campaign",
        "verification",
        "runner_attempt",
        "runner_terminal",
        "runner_failure",
    )
}


class ConstructionK7Standard2048FreshTerminalPreregistrationV42Error(ValueError):
    """The fresh start, frozen world model, planner, cap, or claims changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048FreshTerminalPreregistrationV42Error(message)


def _freshness() -> dict[str, Any]:
    manifest = history.freeze_history_manifest_v42()
    if tuple(
        tuple(row["board"]) for row in manifest["candidate_boards"]
    ) != INITIAL_BOARDS or tuple(
        row["seed"] for row in manifest["candidate_seeds"]
    ) != EPISODE_SEEDS:
        _fail("V42 workload differs from the complete history manifest")
    return manifest


def _document() -> dict[str, Any]:
    freshness = _freshness()
    if freshness.get("all_candidates_fresh") is not True:
        _fail("V42 initial-board orbits are not fresh")
    if any(
        len(board) != 16
        or sum(rank != 0 for rank in board) != 2
        or any(rank not in (0, 1, 2) for rank in board)
        for board in INITIAL_BOARDS
    ):
        _fail("V42 requires fresh two-tile standard-2048 boards")
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_preregistration.v42",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "v35_preregistration_id": V35_PREREGISTRATION_ID,
            "v35_campaign_id": V35_CAMPAIGN_ID,
            "v35_independent_verification_id": V35_VERIFICATION_ID,
            "v41_preregistration_id": V41_PREREGISTRATION_ID,
            "v41_campaign_id": V41_CAMPAIGN_ID,
            "v41_independent_verification_id": V41_VERIFICATION_ID,
            "v41_evidence_scope": "DECISION_768_CHECKPOINT_CONTINUATION_ONLY",
            "v41_fresh_from_initial_or_full_game_evidence": False,
        },
        "single_frozen_world_model": {
            "target_kernel_id": TARGET_KERNEL_ID,
            "adaptive_expression_overlay_id": ADAPTIVE_EXPRESSION_OVERLAY_ID,
            "adaptive_expression_proof_id": ADAPTIVE_EXPRESSION_PROOF_ID,
            "adaptive_expression_model_id": ADAPTIVE_EXPRESSION_MODEL_ID,
            "planner_id": PLANNER_ID,
            "planner_identity_payload": PLANNER_IDENTITY_PAYLOAD,
            "expression_ast": {
                "operator": "COUNT_EQ",
                "vector_source": "POST_SWIPE_BOARD_RANKS",
                "constant": 2,
            },
            "direction": "LE_OVERRIDE",
            "threshold": 1,
            "base_rank_two_probability": Fraction(1, 10),
            "override_rank_two_probability": Fraction(1, 4),
            "planning_horizon": PLANNING_HORIZON,
            "model_may_not_change_during_v42": True,
        },
        "fresh_workload": {
            "initial_boards": [list(board) for board in INITIAL_BOARDS],
            "episode_seeds": list(EPISODE_SEEDS),
            "episode_count": len(INITIAL_BOARDS),
            "exactly_two_initial_tiles": True,
            "initial_tile_ranks_within_standard_spawn_support": True,
            "decision_index_starts_at": INITIAL_DECISION_INDEX,
            "maximum_decisions_per_episode": MAXIMUM_DECISIONS_PER_EPISODE,
            "required_closure": ["WON", "LOST"],
            "active_state_at_decision_cap_is_fail_closed": True,
            "midgame_or_checkpoint_initial_state_allowed": False,
            "complete_git_history_freshness_manifest": freshness,
        },
        "step_chain_contract": {
            "first_previous_step_id": None,
            "subsequent_previous_step_id_must_equal_prior_step_id": True,
            "pre_state_must_equal_prior_next_state": True,
            "certificate_frozen_before_selected_action_and_target_transition": True,
            "selected_action_must_equal_certificate_action": True,
            "deterministic_outcome_tape_bound_to_seed_and_decision_index": True,
            "next_state_and_spawn_observation_must_replay_from_target_kernel": True,
            "each_step_content_addressed": True,
            "prepare_receipt_and_runner_attempt_bound_before_first_step": True,
        },
        "sample_and_persistence_boundary": {
            "inherited_target_probability_label_count": INHERITED_TARGET_PROBABILITY_LABEL_COUNT,
            "additional_model_label_budget": ADDITIONAL_MODEL_LABEL_BUDGET,
            "execution_transitions_are_not_model_labels": True,
            "cache_reuse_claim_must_equal_positive_cross_decision_hit_count": True,
            "zero_cross_decision_hit_count_requires_cache_reused_false": True,
            "crash_resume_supported": False,
            "cross_process_cache_persistence_supported": False,
            "cache_persistence_may_not_be_described_as_crash_resume": True,
        },
        "formal_execution_protocol": {
            "source_commit_required_before_execution": True,
            "committed_prepare_receipt_required_before_launch": True,
            "fixed_authority_and_evidence_roots_required": True,
            "fixed_parent_prepare_and_launch_journals_required": True,
            "one_shot_fixed_evidence_root_required": True,
            "o_excl_artifact_publication_required": True,
            "outer_supervisor_required": True,
            "isolated_producer_and_independent_verifier_processes_required": True,
            "isolated_python_flags": ["-I", "-S", "-B"],
            "durable_secret_bound_worker_authorization_required": True,
            "durable_one_shot_authority_consumption_required": True,
            "committed_repository_python_source_closure_required": True,
            "source_closure_scope": "COMMITTED_REPOSITORY_PYTHON_SOURCE_ONLY",
            "stdlib_and_interpreter_sources_excluded": True,
            "external_python_distributions_excluded": True,
            "non_python_resources_excluded": True,
            "runtime_unmanifested_repository_modules_forbidden": True,
            "campaign_outcome_or_terminal_fields_present": False,
            "formal_execution_performed": False,
        },
        "claim_boundary": {
            "positive_scope": "TWO_REGISTERED_DETERMINISTIC_FRESH_STANDARD_2048_EPISODES_ONLY",
            "history_freshness_scope": "GIT_RETAINED_SOURCE_VISIBLE_PRE_V42_CLOSURE_ONLY",
            "unretained_external_or_deleted_history_excluded": True,
            "universal_never_run_claimed": False,
            "broad_iid_sample_efficiency_claimed": False,
            "cross_domain_transfer_claimed": False,
            "total_operational_work_saving_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": "NOT_RUN",
            "workload_economics_gate_status": "NOT_RUN",
        },
        "future_content_domains": FUTURE_DOMAINS,
    }
    preregistration_id = domains.extension_content_id_v42(
        domains.CONSTRUCTION_K7_PREREGISTRATION_V42_DOMAIN, payload
    )
    return {**payload, "fresh_terminal_preregistration_id": preregistration_id}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048FreshTerminalPreregistrationV42:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V42 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V42 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "fresh_terminal_preregistration_id"
        }
        observed = document.get("fresh_terminal_preregistration_id")
        if (
            observed != self.preregistration_id
            or domains.extension_content_id_v42(
                domains.CONSTRUCTION_K7_PREREGISTRATION_V42_DOMAIN, payload
            )
            != observed
        ):
            _fail("V42 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("V42 preregistration is not an object")
        return document


def freeze_standard_2048_fresh_terminal_preregistration_v42(
) -> Standard2048FreshTerminalPreregistrationV42:
    document = _document()
    raw = canonical_json_bytes(document)
    if PREREGISTRATION_ID != "0" * 64 and (
        document["fresh_terminal_preregistration_id"] != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V42 preregistration changed")
    return Standard2048FreshTerminalPreregistrationV42(
        _ISSUER, raw, document["fresh_terminal_preregistration_id"]
    )


def verify_standard_2048_fresh_terminal_preregistration_v42(
    value: Standard2048FreshTerminalPreregistrationV42,
) -> Standard2048FreshTerminalPreregistrationV42:
    if type(value) is not Standard2048FreshTerminalPreregistrationV42:
        _fail("V42 preregistration verifier rejects foreign values")
    value.__post_init__()
    if PREREGISTRATION_ID != "0" * 64 and value.preregistration_id != PREREGISTRATION_ID:
        _fail("V42 preregistration ID differs from the frozen source")
    return value


__all__ = (
    "ADAPTIVE_EXPRESSION_MODEL_ID",
    "ADAPTIVE_EXPRESSION_OVERLAY_ID",
    "ADAPTIVE_EXPRESSION_PROOF_ID",
    "ADDITIONAL_MODEL_LABEL_BUDGET",
    "EPISODE_SEEDS",
    "FUTURE_DOMAINS",
    "INITIAL_BOARDS",
    "INITIAL_DECISION_INDEX",
    "MAXIMUM_DECISIONS_PER_EPISODE",
    "PLANNER_ID",
    "PREREGISTRATION_ID",
    "Standard2048FreshTerminalPreregistrationV42",
    "TARGET_KERNEL_ID",
    "freeze_standard_2048_fresh_terminal_preregistration_v42",
    "verify_standard_2048_fresh_terminal_preregistration_v42",
)
