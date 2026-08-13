"""Producer-free replay of the V23 long expression-model campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_blind_expression_independent_verifier_v22 as v22
from acfqp.domains.standard_2048 import Swipe2048Action, Swipe2048Status, select_seeded_outcome_v1, state_from_board_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CAMPAIGN_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CERTIFICATE_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_EPISODE_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_PREREGISTRATION_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_SOURCE_BINDING_V23_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_VERIFICATION_V23_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "23.0.0"
PREREGISTRATION_ID = "267dbb02e3e1b44a59d158b3e0c5351cdf11cb2b0256cd9c51cf459fd7408cfb"
CAMPAIGN_ID = "cd198082b21cd1d6365f17081669bbdeac1172ac3da8247b68db4b649a3b0660"
EXPECTED_VERIFICATION_ID = "acecc64e9ffe625a1780c49a85fd1bcc256999e9d15adb0f2cb52afbd0ca4b57"
V22_CAMPAIGN_ID = "85a0f59d0751dfcad87517ed8167d66943d4be0ab9159f78aeaaef7f85923c3e"
V22_VERIFICATION_ID = "6b60d2e7d4585716784a6b9a93c7511f96de2f4742ada0d61d6e1ec78aa2e7b2"
V22_PROOF_ID = "06f9585ee717daf391f51a0b36491f2735bc590bb8ed354c2578d86f89856b94"
V22_WORLD_MODEL_ID = "9ddb728f31cac3ec5b14e73054271216bbea85e654433c43092bbaddac2650fa"
V22_TARGET_KERNEL_ID = "9c40dc9f4a33d2f8bdb008aad5af3fc43be228c7fb964cf137c53af03e962eb5"
SOURCE_BINDING_ID = "14d12943bc78b749cbd74156b5273ff2361a3745a0f58b4fb8c4115fc1b4185e"
HORIZON = 3
MAXIMUM_DECISIONS = 32
CHECKPOINTS = (0, 15, 31)
INITIAL_BOARDS = (
    (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (2, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (1, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0),
)
SEEDS = tuple(
    f"standard-2048-v182-expression-long-real-start-{index:02d}-20260813"
    for index in range(4)
)
SOURCE_FACTS = [
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
        "byte_count": 15747,
        "sha256": "c2f06fcd78e41683544d243d23a4bdb5891b0523fbaa84ce771614c551f0aae2",
    },
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_commit_reveal_target_kernel_v22.py",
        "byte_count": 4226,
        "sha256": "6dd212e4ee0998790c278c66b08e0e87f5e1fef9d165dac170d279f3b1fbb27c",
    },
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_blind_expression_independent_verifier_v22.py",
        "byte_count": 39008,
        "sha256": "d0a03d80f8397acf09d07db39e671baceb5ce01f1c96693e7ef9e349d3b9513e",
    },
    {
        "relative_path": "src/acfqp/domains/standard_2048.py",
        "byte_count": 14739,
        "sha256": "0fabdec281cc94c53bceef37bdb5336da45c71c7339370d25d7dfa076aa7154c",
    },
]


class ConstructionK7Standard2048ExpressionLongIndependentVerifierV23Error(ValueError):
    """The V23 bytes differ from independent long-horizon replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionLongIndependentVerifierV23Error(message)


def _verify_id(document: Any, id_key: str, domain: str, label: str) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} document changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != content_id(domain, payload):
        _fail(f"{label} identity changed")
    return document


def _state(document: Any) -> Any:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state schema changed")
    state = state_from_board_v1(tuple(document["board_ranks"]))
    if state.status.value != document["status"]:
        _fail("state status changed")
    return state


def _source_binding_expected() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_long_source_binding.v23",
        "schema_version": SCHEMA_VERSION,
        "expression_long_preregistration_id": PREREGISTRATION_ID,
        "v22_campaign_id": V22_CAMPAIGN_ID,
        "v22_independent_verification_id": V22_VERIFICATION_ID,
        "v22_expression_proof_id": V22_PROOF_ID,
        "v22_world_model_id": V22_WORLD_MODEL_ID,
        "v22_target_kernel_id": V22_TARGET_KERNEL_ID,
        "source_facts": SOURCE_FACTS,
        "expression_ast": {
            "operator": "COUNT_EQ",
            "vector_source": "POST_SWIPE_BOARD_RANKS",
            "constant": 1,
        },
        "threshold": 2,
        "base_probability": Fraction(1, 10),
        "override_probability": Fraction(3, 20),
        "planning_horizon": HORIZON,
        "persistent_subproof_cache_enabled": True,
        "target_probability_query_count_after_v22": 0,
        "binding_frozen_before_long_target_execution": True,
    }
    document = {
        **payload,
        "expression_long_source_binding_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_SOURCE_BINDING_V23_DOMAIN,
            payload,
        ),
    }
    if document["expression_long_source_binding_id"] != SOURCE_BINDING_ID:
        _fail("frozen independent source binding changed")
    return document


class _PersistentPlanner(v22._Planner):  # noqa: SLF001
    def __init__(self) -> None:
        super().__init__()
        self.reusable_keys: frozenset[tuple[tuple[int, ...], str, int]] = frozenset()
        self.cross_decision_hits = 0

    def state_value(self, board: tuple[int, ...], status: str, remaining: int) -> Any:
        key = (v22._canonical(board), status, remaining)  # noqa: SLF001
        if key in self.cache and key in self.reusable_keys:
            self.cross_decision_hits += 1
        return super().state_value(board, status, remaining)

    def plan(self, state: Any) -> dict[str, Any]:
        before = (self.rows, self.outcomes, self.hits, self.misses, self.cross_decision_hits)
        self.reusable_keys = frozenset(self.cache)
        values = self.roots(state)
        best = None
        for value in values:
            if v22._better(value, best):  # noqa: SLF001
                best = value
        if best is None or best.action is None:
            _fail("independent persistent root has no selected action")
        return {
            "root_action_exact_values": [
                {
                    "action": value.action,
                    "expected_merge_score": value.score,
                    "loss_probability_within_horizon": value.loss,
                }
                for value in values
            ],
            "selected_action": best.action,
            "selected_expected_merge_score": best.score,
            "selected_loss_probability_within_horizon": best.loss,
            "rows": self.rows - before[0],
            "outcomes": self.outcomes - before[1],
            "hits": self.hits - before[2],
            "misses": self.misses - before[3],
            "cross_hits": self.cross_decision_hits - before[4],
            "cache_entries": len(self.cache),
        }


def _verify_episode(task: tuple[int, dict[str, Any]]) -> dict[str, int]:
    episode_index, episode = task
    _verify_id(
        episode,
        "expression_long_episode_id",
        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_EPISODE_V23_DOMAIN,
        "episode",
    )
    state = state_from_board_v1(INITIAL_BOARDS[episode_index])
    if (
        episode.get("episode_index") != episode_index
        or episode.get("execution_seed") != SEEDS[episode_index]
        or _state(episode.get("initial_state")) != state
        or episode.get("expression_long_source_binding_id") != SOURCE_BINDING_ID
    ):
        _fail("long episode identity changed")
    rows = episode.get("decisions")
    if type(rows) is not list or len(rows) != MAXIMUM_DECISIONS:
        _fail("long episode decision inventory changed")
    planner = _PersistentPlanner()
    totals = {"rows": 0, "outcomes": 0, "hits": 0, "misses": 0, "cross": 0, "checkpoints": 0}
    for decision_index, decision in enumerate(rows):
        replay = planner.plan(state)
        certificate = _verify_id(
            decision.get("certificate"),
            "expression_long_certificate_id",
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CERTIFICATE_V23_DOMAIN,
            "certificate",
        )
        if (
            decision.get("decision_index") != decision_index
            or _state(decision.get("predecision_state")) != state
            or certificate.get("root_state") != decision.get("predecision_state")
            or certificate.get("root_action_exact_values") != replay["root_action_exact_values"]
            or certificate.get("selected_action") != replay["selected_action"]
            or certificate.get("selected_expected_merge_score") != replay["selected_expected_merge_score"]
            or certificate.get("selected_loss_probability_within_horizon")
            != replay["selected_loss_probability_within_horizon"]
            or certificate.get("factored_action_row_evaluation_count") != replay["rows"]
            or certificate.get("factored_support_outcome_evaluation_count") != replay["outcomes"]
            or certificate.get("subproof_cache_hit_count") != replay["hits"]
            or certificate.get("subproof_cache_miss_count") != replay["misses"]
            or certificate.get("cross_decision_subproof_cache_hit_count") != replay["cross_hits"]
            or certificate.get("persistent_subproof_cache_entry_count") != replay["cache_entries"]
            or certificate.get("operational_target_probability_query_count") != 0
            or certificate.get("operational_ground_state_action_row_count") != 0
            or certificate.get("target_transition_accessed_before_certificate_freeze") is not False
            or certificate.get("status") != "CERTIFIED_PERSISTENT_EXPRESSION_MODEL_H3"
        ):
            _fail("long certificate differs from independent persistent replay")
        checkpoint = decision.get("cold_target_checkpoint")
        if decision_index in CHECKPOINTS:
            expected = {
                "root_action_exact_values": replay["root_action_exact_values"],
                "selected_action": replay["selected_action"],
                "selected_expected_merge_score": replay["selected_expected_merge_score"],
                "selected_loss_probability_within_horizon": replay[
                    "selected_loss_probability_within_horizon"
                ],
                "ground_state_action_row_count": replay["rows"],
                "ground_outcome_count": replay["outcomes"],
                "subproof_cache_hit_count": replay["hits"],
                "subproof_cache_miss_count": replay["misses"],
                "lane": "STANDALONE_EVALUATION_ONLY",
                "route_or_certificate_authority": False,
            }
            # Cold evaluation has an empty cache, so compute it independently.
            cold = v22._root_replay(state)  # noqa: SLF001
            expected.update(
                {
                    "root_action_exact_values": cold["root_action_exact_values"],
                    "selected_action": cold["selected_action"],
                    "selected_expected_merge_score": cold["selected_expected_merge_score"],
                    "selected_loss_probability_within_horizon": cold[
                        "selected_loss_probability_within_horizon"
                    ],
                    "ground_state_action_row_count": cold["action_rows"],
                    "ground_outcome_count": cold["outcomes"],
                    "subproof_cache_hit_count": cold["hits"],
                    "subproof_cache_miss_count": cold["misses"],
                }
            )
            if checkpoint != expected:
                _fail("long cold checkpoint differs from independent replay")
            totals["checkpoints"] += 1
        elif checkpoint is not None:
            _fail("unexpected cold checkpoint appeared")
        if (
            decision.get("route") != "PERSISTENT_EXPRESSION_WORLD_MODEL_CERTIFIED"
            or decision.get("checkpoint_root_values_and_action_exactly_equal") is not True
            or decision.get("certificate_frozen_before_cold_checkpoint_and_target_transition") is not True
            or decision.get("execution_transition_used_to_modify_world_model") is not False
        ):
            _fail("long route or certificate ordering changed")
        outcome, tape = select_seeded_outcome_v1(
            v22._target_outcomes(state, Swipe2048Action(replay["selected_action"])),  # noqa: SLF001
            seed=SEEDS[episode_index],
            decision_index=decision_index,
        )
        if (
            decision.get("executed_action") != replay["selected_action"]
            or decision.get("execution_tape_sha256") != tape
            or _state(decision.get("executed_next_state")) != outcome.next_state
            or decision.get("online_target_transition_observation_count") != 1
        ):
            _fail("long seeded transition differs from independent replay")
        state = outcome.next_state
        totals["rows"] += replay["rows"]
        totals["outcomes"] += replay["outcomes"]
        totals["hits"] += replay["hits"]
        totals["misses"] += replay["misses"]
        totals["cross"] += replay["cross_hits"]
    if (
        _state(episode.get("final_state")) != state
        or episode.get("decision_count") != MAXIMUM_DECISIONS
        or episode.get("model_certificate_count") != MAXIMUM_DECISIONS
        or episode.get("local_ground_recovery_count") != 0
        or episode.get("cold_evaluation_checkpoint_count") != 3
        or episode.get("all_checkpoint_root_values_and_actions_exactly_equal") is not True
        or episode.get("factored_action_row_evaluation_count") != totals["rows"]
        or episode.get("factored_support_outcome_evaluation_count") != totals["outcomes"]
        or episode.get("subproof_cache_hit_count") != totals["hits"]
        or episode.get("subproof_cache_miss_count") != totals["misses"]
        or episode.get("cross_decision_subproof_cache_hit_count") != totals["cross"]
    ):
        _fail("long episode aggregate differs from independent replay")
    return totals


def _verify_preregistration(document: Any) -> None:
    row = _verify_id(
        document,
        "expression_long_preregistration_id",
        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_PREREGISTRATION_V23_DOMAIN,
        "preregistration",
    )
    workload = row.get("long_real_start_workload")
    predecessor = row.get("frozen_v22_predecessor")
    protocol = row.get("persistent_proof_protocol")
    tax = row.get("sample_tax_contract")
    if (
        row["expression_long_preregistration_id"] != PREREGISTRATION_ID
        or type(workload) is not dict
        or workload.get("initial_boards") != [list(board) for board in INITIAL_BOARDS]
        or workload.get("episode_seeds") != list(SEEDS)
        or workload.get("planning_horizon") != HORIZON
        or workload.get("maximum_decisions_per_episode") != MAXIMUM_DECISIONS
        or type(predecessor) is not dict
        or predecessor.get("campaign_id") != V22_CAMPAIGN_ID
        or predecessor.get("independent_verification_id") != V22_VERIFICATION_ID
        or predecessor.get("exact_expression_proof_id") != V22_PROOF_ID
        or predecessor.get("world_model_id") != V22_WORLD_MODEL_ID
        or predecessor.get("target_kernel_id") != V22_TARGET_KERNEL_ID
        or predecessor.get("world_model_immutable_during_long_workload") is not True
        or type(protocol) is not dict
        or protocol.get("one_bellman_subproof_cache_per_episode") is not True
        or protocol.get("cache_reused_across_receding_horizon_decisions") is not True
        or protocol.get("approximation_or_precision_reduction_allowed") is not False
        or protocol.get("cold_evaluation_checkpoint_indices") != list(CHECKPOINTS)
        or type(tax) is not dict
        or tax.get("inherited_target_probability_label_count") != 4
        or tax.get("additional_model_acquisition_label_budget") != 0
        or tax.get("strict_no_prior_context_label_count") != 8
        or row.get("outcome_fields_present") is not False
        or row.get("target_execution_performed") is not False
        or row.get("full_standard_2048_game_claimed") is not False
        or row.get("official_execution_allowed") is not False
    ):
        _fail("long preregistration or claim locks changed")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionLongIndependentVerificationV23:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("long independent verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("long independent verification bytes changed")
        payload = {
            key: value for key, value in document.items()
            if key != "expression_long_verification_id"
        }
        if (
            document.get("expression_long_verification_id") != self.verification_id
            or document.get("expression_long_campaign_id") != self.campaign_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_VERIFICATION_V23_DOMAIN,
                payload,
            )
            != self.verification_id
        ):
            _fail("long independent verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("long independent verification is not an object")
        return document


def verify_standard_2048_expression_long_bytes_independently_v23(
    canonical_bytes: bytes,
) -> Standard2048ExpressionLongIndependentVerificationV23:
    try:
        observed = loads_canonical_json(canonical_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048ExpressionLongIndependentVerifierV23Error(
            "long campaign bytes are not canonical"
        ) from error
    if canonical_json_bytes(observed) != canonical_bytes:
        _fail("long campaign bytes are noncanonical")
    root = _verify_id(
        observed,
        "expression_long_campaign_id",
        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CAMPAIGN_V23_DOMAIN,
        "campaign",
    )
    if root["expression_long_campaign_id"] != CAMPAIGN_ID:
        _fail("long campaign identity changed")
    _verify_preregistration(root.get("expression_long_preregistration"))
    binding = _source_binding_expected()
    if root.get("source_binding") != binding:
        _fail("long source binding differs from independent reconstruction")
    episodes = root.get("episodes")
    if type(episodes) is not list or len(episodes) != 4:
        _fail("long campaign episode inventory changed")
    with ProcessPoolExecutor(max_workers=4) as executor:
        totals = list(executor.map(_verify_episode, enumerate(episodes), chunksize=1))
    aggregate = {
        key: sum(row[key] for row in totals)
        for key in ("rows", "outcomes", "hits", "misses", "cross", "checkpoints")
    }
    if (
        root.get("episode_count") != 4
        or root.get("decision_count") != 128
        or root.get("model_certificate_count") != 128
        or root.get("local_ground_recovery_count") != 0
        or root.get("cold_evaluation_checkpoint_count") != 12
        or root.get("all_checkpoint_root_values_and_actions_exactly_equal") is not True
        or root.get("inherited_target_probability_label_count") != 4
        or root.get("additional_model_acquisition_label_count") != 0
        or root.get("strict_no_prior_context_label_count") != 8
        or root.get("target_label_difference_against_no_prior") != 4
        or root.get("inherited_label_fraction_of_no_prior") != Fraction(1, 2)
        or root.get("certified_decisions_per_acquired_target_label") != 32
        or root.get("online_target_transition_observation_count") != 128
        or root.get("factored_action_row_evaluation_count") != aggregate["rows"]
        or root.get("factored_support_outcome_evaluation_count") != aggregate["outcomes"]
        or root.get("subproof_cache_hit_count") != aggregate["hits"]
        or root.get("subproof_cache_miss_count") != aggregate["misses"]
        or root.get("cross_decision_subproof_cache_hit_count") != aggregate["cross"]
        or root.get("persistent_subproof_cache_preserved_exact_values") is not True
        or root.get("all_planning_performed_in_v22_expression_world_model") is not True
        or root.get("operational_target_probability_query_count_during_long_planning") != 0
        or root.get("operational_ground_state_action_row_count_during_long_planning") != 0
        or root.get("sample_tax_reduced_on_registered_target_label_axis") is not True
        or root.get("broad_or_physical_iid_sample_efficiency_claimed") is not False
        or root.get("total_operational_work_saving_claimed") is not False
        or root.get("full_standard_2048_game_completed") is not False
        or root.get("tile_2048_reached") is not False
        or root.get("maximum_final_board_tile_rank") != 6
        or root.get("official_execution_allowed") is not False
        or root.get("official_scalar_cost") is not None
        or root.get("official_N_break_even") is not None
        or root.get("counter_completeness_gate_status") != "NOT_RUN"
        or root.get("workload_economics_gate_status") != "NOT_RUN"
    ):
        _fail("long campaign aggregate or claim boundary changed")
    payload = {
        "schema": "acfqp.standard_2048_expression_long_independent_verification.v23",
        "schema_version": SCHEMA_VERSION,
        "expression_long_preregistration_id": PREREGISTRATION_ID,
        "expression_long_campaign_id": CAMPAIGN_ID,
        "expression_long_source_binding_id": SOURCE_BINDING_ID,
        "all_128_h3_certificates_independently_replayed": True,
        "all_128_seeded_target_transitions_independently_replayed": True,
        "all_12_cold_target_checkpoints_independently_replayed": True,
        "persistent_cross_decision_subproof_cache_independently_replayed": True,
        "exact_rational_precision_preserved": True,
        "zero_additional_model_labels_independently_verified": True,
        "four_inherited_labels_amortized_over_128_certificates_verified": True,
        "evaluation_counter_aggregates_independently_verified": True,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "full_game_or_tile_2048_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_VERIFICATION_V23_DOMAIN,
        payload,
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen long independent verification identity changed")
    return Standard2048ExpressionLongIndependentVerificationV23(
        _ISSUER,
        canonical_json_bytes({**payload, "expression_long_verification_id": verification_id}),
        verification_id,
        CAMPAIGN_ID,
    )


__all__ = (
    "CAMPAIGN_ID",
    "ConstructionK7Standard2048ExpressionLongIndependentVerifierV23Error",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048ExpressionLongIndependentVerificationV23",
    "verify_standard_2048_expression_long_bytes_independently_v23",
)
