"""Preregistration authority for the V0-072 held-out acquisition Gate.

This module freezes public seven-vertex contexts, target-arm semantics, finite
caps, and a separately role-bound hidden environment manifest.  It exposes no
transition sampler and deliberately keeps target execution disabled until a
later artifact binds the first remote ``main`` commit containing the finalized
non-null execution manifest and final preregistration ID.  This module is the
nonauthorizing draft authority until then.  No target outcome is generated
while this module is imported or constructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from itertools import combinations
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "transfer_guided_adaptive_observation_acquisition_v1"
CONFIRMATORY_FAMILY_GENERATION = (
    "v072_anchor_clean_confirmatory_family_generation_1"
)
DRAFT_PREREGISTRATION_ID = (
    "7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2"
)
SUPERSEDED_DRAFT_PREREGISTRATION_IDS = (
    "8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29",
    "e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4",
)
RETIRED_DEVELOPMENT_DRY_RUN_IDS = (
    "0f8061ac58630cced8f01bce01191ab0d02aff5cf64b4cc106f579ad53d02312",
    "1f240bb0305012a9144b4039d9f2f9b13a0be18b23c0cc7c70dc2909f09ccc29",
    "a5775190ea336702a7f4e1f06bdd93ec0bd0609f03f69ad7a72c2262e6645976",
    "ad7dca2b9db96d98d0c8bd6608315264995d3dcb0b6457a4b2b5d073db494ab0",
    "571d4cb2a7b2b55fc85012b2b417f397b57226df7ae4b00c47d0bb5f35639441",
    "e8cb7a070c7d6bbdb93683367a8026f422a8ef397877b87d07a3c6c549820cde",
    "f0d8db6165c3d0a125945b43b4b0d8e221b13ea7870021e96f18b91e218ed00e",
    "495927b2c72c847086008b2b2c6e8f65ea4a2b5a45ce409c8c7ec3d4be915500",
)

HORIZON = 2
RANK_CAP = 6
ROOT_RANKS = (1, 1, 2, 0, 0, 0, 0)
RISK_TOLERANCE = Fraction(1, 20)
REWARD_CEILING = Fraction(3, 64)
NORMALIZED_REGRET_TOLERANCE = Fraction(1, 20)
MAX_ROUNDS = 2
FAMILY_ROW_EPOCH_CAP = 512
MAX_CONFIDENCE_EPOCHS_PER_PHYSICAL_ROW = 3
MAX_PROMOTIONS_PER_PHYSICAL_ROW = MAX_ROUNDS
MAX_PROMOTION_AUTHORITIES_PER_CONTEXT = MAX_ROUNDS
# Compatibility name retained for components that predate the audit
# correction.  It now denotes initial evidence plus both possible promotions.
MAX_EPOCHS = MAX_CONFIDENCE_EPOCHS_PER_PHYSICAL_ROW
INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW = 64
INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW = 2_048
PROMOTION_VALIDATION_DRAWS_PER_ROUND = 2_048
NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW = 64
NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW = 8_192
MAX_NEW_CHILD_ACTION_ROWS_ACROSS_ROUNDS = 19
MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM = 160_960
MAX_INITIAL_ACCEPTED_DRAW_CAP_PER_ARM = (
    240
    * (
        INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
        + INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW
    )
)
ROW_EPOCH_BETA = Fraction(1, 300_000)
MAX_ROW_EPOCH_AUTHORITIES_PER_ARM = 480
ROW_EPOCH_AUTHORITY_CAP_RULE = (
    "SUM_CONTEXT_INITIAL_UNIQUE_ROW_AUTHORITIES_LE_PUBLIC_ROW_CAP_PLUS_"
    "PROMOTION_AUTHORITIES_LE_MAX_ROUNDS_LE_"
    "TWO_TIMES_SUM_PUBLIC_ROW_CAP"
)
MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES = (
    len(
        (
            "SOURCE_CONSENSUS_PRIOR",
            "NO_PRIOR",
            "WRONG_CONSENSUS_PRIOR",
            "OOD_ABSTENTION",
            "MATCHED_DIRECT_GROUND",
        )
    )
    * MAX_ROW_EPOCH_AUTHORITIES_PER_ARM
)
CAMPAIGN_JOINT_TAIL_UPPER = Fraction(1, 125)
CAMPAIGN_CONFIDENCE_LOWER = Fraction(124, 125)

INITIAL_CLOSURE_ORDER = (
    "COLD_START_ALL_LEGAL_ROOT_ROWS_DISCOVERY64_THEN_VALIDATION2048_"
    "THEN_ACTIVE_NONTERMINAL_ROOT_DISCOVERY_SUCCESSORS_"
    "THEN_ALL_LEGAL_CHILD_ROWS_DISCOVERY64_THEN_VALIDATION2048_"
    "BUILD_COMPLETE_H2_GROUND_AND_QUOTIENT_MODELS_"
    "AUDIT_ONCE_ONLY_AFTER_COMPLETE_CHECKPOINT"
)
NOVEL_CHILD_CARDINALITY_RULE = (
    "PROMOTE_TO_PARENT_SUPPORT_UNION_ALL_CURRENT_VALIDATION_NOVEL_"
    "DESCRIPTORS_REQUIRE_POSITIVE_GAIN_AND_NONEMPTY_NOVEL_SET_"
    "DERIVE_DISTINCT_ABSENT_H1_PHYSICAL_STATE_LEGAL_ACTION_ROWS_"
    "FROM_COMPLETE_PUBLIC_CATALOGUES_BEFORE_AUTHORIZATION_"
    "CONTENT_ADDRESS_FULL_CANONICAL_ROW_LIST"
)
RAW_WORD_PAIRING_RULE = (
    "PAIR_ONLY_IDENTICAL_CONTEXT_PHYSICAL_ROW_ARM_FREE_SUPPORT_SET_AND_"
    "LINEAGE_ROUND_EPOCH_LANE_CHECKPOINT_AND_RANDOM_WORD_INDEX_"
    "WITH_ARM_DISJOINT_STREAM_OBSERVATION_EVIDENCE_MODEL_AND_WORK_IDS"
)
ADAPTIVE_AUDIT_CHECKPOINTS = (
    "ROUND0_COMPLETE_VALIDATION_2048",
    "ROUND1_COMPLETE_MATERIALIZATION",
    "ROUND2_COMPLETE_FRESH_MATERIALIZATION",
)
DIRECT_VALIDATION_CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
DIRECT_BASELINE_RULE = (
    "SAME_COLD_ROUND0_H2_CLOSURE_GROUND_NO_QUOTIENT_THEN_"
    "CHRONOLOGICALLY_EXTEND_EVERY_FIXED_EPOCH1_VALIDATION_PREFIX_"
    "TO_4096_8192_16384_WITH_COMPLETE_GROUND_REPLAN_AND_AUDIT_"
    "STOP_AT_FIRST_SOUND_CERTIFICATE_NO_SOURCE_OR_LOCAL_PROMOTION"
)
INCREMENTAL_CUMULATIVE_CAP_RULE = (
    "C_R=2048*R+8256*CARDINALITY_OF_UNION_NEW_CHILD_ROWS_THROUGH_R_"
    "LE_160960_AND_UNION_CARDINALITY_LE_19_NO_RESET_OR_BORROW"
)
EXACT_LAZY_RESOURCE_LIMITS = {
    "max_branch_nodes": 10_000_000,
    "max_complete_policies": 1_000_000,
    "max_root_bound_evaluations": 10_000_000,
}
CONFIRMATORY_OCCURRENCE_COUNT = 15
CONFIRMATORY_EXECUTION_MANIFEST_REQUIRED = True

ARM_ORDER = (
    "SOURCE_CONSENSUS_PRIOR",
    "NO_PRIOR",
    "WRONG_CONSENSUS_PRIOR",
    "OOD_ABSTENTION",
    "MATCHED_DIRECT_GROUND",
)
DIRECT_CHECKPOINT_CAP_TERMINAL_CODE = (
    "DIRECT_CHECKPOINT_CAP_EXHAUSTED_NONCERTIFICATE"
)
TERMINAL_CODES = (
    "CONDITIONAL_PLAN_CERTIFICATE",
    "EXACT_FEASIBLE_FALLBACK",
    "EXACT_INFEASIBILITY_CERTIFICATE",
    "NO_POSITIVE_GAIN_NONCERTIFICATE",
    "INCREMENTAL_CAP_EXHAUSTED_NONCERTIFICATE",
    DIRECT_CHECKPOINT_CAP_TERMINAL_CODE,
    "EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE",
    "TWO_ROUND_CAP_EXHAUSTED_NONCERTIFICATE",
    "PROTOCOL_FAILURE",
    "INTEGRITY_FAILURE",
)

DOMAIN_TAGS = {
    "context": "acfqp:v072-heldout-public-context:v2",
    "law": "acfqp:v072-hidden-spawn-law:v2",
    "environment": "acfqp:v072-heldout-environment-manifest:v2",
    "preregistration": "acfqp:v072-adaptive-acquisition-preregistration:v2",
}


class TransferGuidedAcquisitionPreregistrationInvariantViolation(ValueError):
    """A V0-072 preregistration identity or frozen-value invariant failed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise TransferGuidedAcquisitionPreregistrationInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise TransferGuidedAcquisitionPreregistrationInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise TransferGuidedAcquisitionPreregistrationInvariantViolation(
            "registered arithmetic must use exact Fraction"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _canonical_edges(
    edges: Iterable[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    return tuple(sorted({tuple(sorted(edge)) for edge in edges}))


K7_TOPOLOGY = GraphTopologyV1(
    7,
    tuple(combinations(range(7), 2)),
)
W7_TOPOLOGY = GraphTopologyV1(
    7,
    _canonical_edges(
        tuple((index, (index + 1) % 6) for index in range(6))
        + tuple((6, index) for index in range(6))
    ),
)
K7_MINUS_TWO_TOPOLOGY = GraphTopologyV1(
    7,
    tuple(
        edge
        for edge in combinations(range(7), 2)
        if edge not in {(4, 6), (5, 6)}
    ),
)

_CONTEXT_SPECS = (
    ("heldout_graph_k7_confirmatory_v1", K7_TOPOLOGY, 96),
    ("heldout_graph_w7_confirmatory_v1", W7_TOPOLOGY, 48),
    (
        "heldout_graph_k7_minus_two_confirmatory_v1",
        K7_MINUS_TWO_TOPOLOGY,
        96,
    ),
)

# Environment-only values.  They are intentionally absent from every public
# context document.  This tuple is frozen before any target sampler exists.
_HIDDEN_LAW_SPECS = {
    "heldout_graph_k7_confirmatory_v1": (
        (1, Fraction(197, 200)),
        (2, Fraction(1, 100)),
        (3, Fraction(1, 200)),
    ),
    "heldout_graph_w7_confirmatory_v1": (
        (1, Fraction(99, 100)),
        (2, Fraction(1, 100)),
    ),
    "heldout_graph_k7_minus_two_confirmatory_v1": (
        (1, Fraction(49, 50)),
        (2, Fraction(3, 200)),
        (3, Fraction(1, 200)),
    ),
}


@dataclass(frozen=True, slots=True)
class HeldoutPublicGraphContextV2:
    context_key: str
    topology: GraphTopologyV1
    maximum_physical_rows_per_confidence_epoch: int
    root_ranks: tuple[int, ...] = ROOT_RANKS
    horizon: int = HORIZON
    risk_tolerance: Fraction = RISK_TOLERANCE
    rank_cap: int = RANK_CAP
    reward_ceiling: Fraction = REWARD_CEILING
    normalized_regret_tolerance: Fraction = (
        NORMALIZED_REGRET_TOLERANCE
    )

    def __post_init__(self) -> None:
        registered = next(
            (
                (topology, cap)
                for key, topology, cap in _CONTEXT_SPECS
                if key == self.context_key
            ),
            None,
        )
        if (
            registered
            != (
                self.topology,
                self.maximum_physical_rows_per_confidence_epoch,
            )
            or type(self.topology) is not GraphTopologyV1
            or self.root_ranks != ROOT_RANKS
            or self.horizon != HORIZON
            or self.risk_tolerance != RISK_TOLERANCE
            or self.rank_cap != RANK_CAP
            or self.reward_ceiling != REWARD_CEILING
            or self.normalized_regret_tolerance
            != NORMALIZED_REGRET_TOLERANCE
        ):
            raise TransferGuidedAcquisitionPreregistrationInvariantViolation(
                "held-out public graph context changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_public_graph_context.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "confirmatory_family_generation": (
                CONFIRMATORY_FAMILY_GENERATION
            ),
            "context_key": self.context_key,
            "topology": self.topology.to_document(),
            "root_ranks": list(self.root_ranks),
            "horizon": self.horizon,
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "rank_cap": self.rank_cap,
            "reward_ceiling": _fdoc(self.reward_ceiling),
            "normalized_regret_tolerance": _fdoc(
                self.normalized_regret_tolerance
            ),
            "maximum_physical_rows_per_confidence_epoch": (
                self.maximum_physical_rows_per_confidence_epoch
            ),
            "hidden_law_serialized": False,
            "target_execution_allowed": False,
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def registered_heldout_public_contexts_v2(
) -> tuple[HeldoutPublicGraphContextV2, ...]:
    return tuple(
        HeldoutPublicGraphContextV2(key, topology, cap)
        for key, topology, cap in _CONTEXT_SPECS
    )


@dataclass(frozen=True, slots=True)
class HiddenSpawnLawCommitmentV1:
    context_id: str
    context_key: str
    rank_probabilities: tuple[tuple[int, Fraction], ...]
    role: str = "ENVIRONMENT_AUTHORITY_ONLY"

    def __post_init__(self) -> None:
        context = next(
            (
                item
                for item in registered_heldout_public_contexts_v2()
                if item.context_key == self.context_key
            ),
            None,
        )
        if (
            context is None
            or _cid(self.context_id, "law context") != context.context_id
            or self.rank_probabilities
            != _HIDDEN_LAW_SPECS.get(self.context_key)
            or sum(
                (
                    probability
                    for _, probability in self.rank_probabilities
                ),
                Fraction(0),
            )
            != 1
            or tuple(rank for rank, _ in self.rank_probabilities)
            != tuple(
                sorted({rank for rank, _ in self.rank_probabilities})
            )
            or any(
                type(rank) is not int
                or type(probability) is not Fraction
                or probability <= 0
                for rank, probability in self.rank_probabilities
            )
            or self.role != "ENVIRONMENT_AUTHORITY_ONLY"
        ):
            raise TransferGuidedAcquisitionPreregistrationInvariantViolation(
                "hidden spawn-law commitment changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_hidden_spawn_law_commitment.v2",
            "schema_version": SCHEMA_VERSION,
            "confirmatory_family_generation": (
                CONFIRMATORY_FAMILY_GENERATION
            ),
            "context_id": self.context_id,
            "context_key": self.context_key,
            "rank_probabilities": [
                {"rank": rank, "probability": _fdoc(probability)}
                for rank, probability in self.rank_probabilities
            ],
            "role": self.role,
            "frozen_before_target_execution": True,
        }

    @property
    def law_id(self) -> str:
        return _content_id("law", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "law_id": self.law_id}


@dataclass(frozen=True, slots=True)
class HeldoutEnvironmentManifestV1:
    laws: tuple[HiddenSpawnLawCommitmentV1, ...]
    target_tapes_opened: bool = False
    target_observations_generated: int = 0

    def __post_init__(self) -> None:
        contexts = registered_heldout_public_contexts_v2()
        expected = tuple(
            HiddenSpawnLawCommitmentV1(
                context.context_id,
                context.context_key,
                _HIDDEN_LAW_SPECS[context.context_key],
            )
            for context in contexts
        )
        if (
            self.laws != expected
            or self.target_tapes_opened is not False
            or self.target_observations_generated != 0
        ):
            raise TransferGuidedAcquisitionPreregistrationInvariantViolation(
                "held-out environment manifest is not pre-execution"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_heldout_environment_manifest.v2",
            "schema_version": SCHEMA_VERSION,
            "confirmatory_family_generation": (
                CONFIRMATORY_FAMILY_GENERATION
            ),
            "law_ids": [item.law_id for item in self.laws],
            "target_tapes_opened": False,
            "target_observations_generated": 0,
            "reroll_allowed": False,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("environment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}


def frozen_heldout_environment_manifest_v1(
) -> HeldoutEnvironmentManifestV1:
    contexts = registered_heldout_public_contexts_v2()
    return HeldoutEnvironmentManifestV1(
        tuple(
            HiddenSpawnLawCommitmentV1(
                context.context_id,
                context.context_key,
                _HIDDEN_LAW_SPECS[context.context_key],
            )
            for context in contexts
        )
    )


@dataclass(frozen=True, slots=True)
class TransferGuidedAcquisitionPreregistrationV1:
    context_ids: tuple[str, ...]
    environment_manifest_id: str
    arm_order: tuple[str, ...]
    terminal_codes: tuple[str, ...]
    physical_row_cap_sum_per_confidence_epoch: int
    maximum_confidence_epochs_per_physical_row: int
    maximum_promotions_per_physical_row: int
    maximum_promotion_authorities_per_context: int
    row_epoch_authority_cap_rule: str
    family_row_epoch_cap: int
    maximum_rounds: int
    initial_discovery_draws_per_physical_row: int
    initial_validation_draws_per_physical_row: int
    initial_closure_order: str
    maximum_initial_accepted_draw_cap_per_arm: int
    promotion_validation_draws_per_round: int
    new_child_discovery_draws_per_physical_row: int
    new_child_validation_draws_per_physical_row: int
    maximum_new_child_action_rows_across_rounds: int
    maximum_two_round_incremental_draw_cap_per_arm: int
    row_epoch_beta: Fraction
    maximum_arm_bound_row_epoch_authorities_per_arm: int
    maximum_campaign_row_epoch_authorities: int
    campaign_joint_tail_upper: Fraction
    campaign_confidence_lower: Fraction
    novel_child_cardinality_rule: str
    raw_word_pairing_rule: str
    confirmatory_execution_manifest_id: None = None
    confirmatory_profile_finalized: bool = False
    first_remote_main_commit_required: bool = True
    anchor_commit_id: None = None
    target_execution_allowed: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        contexts = registered_heldout_public_contexts_v2()
        expected_context_ids = tuple(item.context_id for item in contexts)
        expected_row_cap_sum = sum(
            item.maximum_physical_rows_per_confidence_epoch
            for item in contexts
        )
        manifest = frozen_heldout_environment_manifest_v1()
        if (
            self.context_ids != expected_context_ids
            or _cid(
                self.environment_manifest_id,
                "environment manifest",
            )
            != manifest.manifest_id
            or self.arm_order != ARM_ORDER
            or self.terminal_codes != TERMINAL_CODES
            or self.physical_row_cap_sum_per_confidence_epoch
            != expected_row_cap_sum
            or self.maximum_confidence_epochs_per_physical_row
            != MAX_EPOCHS
            or self.maximum_promotions_per_physical_row
            != MAX_PROMOTIONS_PER_PHYSICAL_ROW
            or self.maximum_confidence_epochs_per_physical_row
            != 1 + self.maximum_promotions_per_physical_row
            or self.maximum_promotion_authorities_per_context
            != MAX_PROMOTION_AUTHORITIES_PER_CONTEXT
            or self.maximum_promotion_authorities_per_context
            != self.maximum_rounds
            or self.row_epoch_authority_cap_rule
            != ROW_EPOCH_AUTHORITY_CAP_RULE
            or self.family_row_epoch_cap != FAMILY_ROW_EPOCH_CAP
            or self.maximum_arm_bound_row_epoch_authorities_per_arm
            > self.family_row_epoch_cap
            or self.maximum_arm_bound_row_epoch_authorities_per_arm
            != 2 * self.physical_row_cap_sum_per_confidence_epoch
            or self.maximum_promotion_authorities_per_context
            > min(
                item.maximum_physical_rows_per_confidence_epoch
                for item in contexts
            )
            or self.maximum_rounds != MAX_ROUNDS
            or self.initial_discovery_draws_per_physical_row
            != INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
            or self.initial_validation_draws_per_physical_row
            != INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW
            or self.initial_closure_order != INITIAL_CLOSURE_ORDER
            or self.maximum_initial_accepted_draw_cap_per_arm
            != MAX_INITIAL_ACCEPTED_DRAW_CAP_PER_ARM
            or self.promotion_validation_draws_per_round
            != PROMOTION_VALIDATION_DRAWS_PER_ROUND
            or self.new_child_discovery_draws_per_physical_row
            != NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
            or self.new_child_validation_draws_per_physical_row
            != NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
            or self.maximum_new_child_action_rows_across_rounds
            != MAX_NEW_CHILD_ACTION_ROWS_ACROSS_ROUNDS
            or self.maximum_two_round_incremental_draw_cap_per_arm
            != MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM
            or self.row_epoch_beta != ROW_EPOCH_BETA
            or self.maximum_arm_bound_row_epoch_authorities_per_arm
            != MAX_ROW_EPOCH_AUTHORITIES_PER_ARM
            or self.maximum_campaign_row_epoch_authorities
            != MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES
            or self.campaign_joint_tail_upper
            != CAMPAIGN_JOINT_TAIL_UPPER
            or self.campaign_confidence_lower
            != CAMPAIGN_CONFIDENCE_LOWER
            or self.campaign_joint_tail_upper
            != (
                self.maximum_campaign_row_epoch_authorities
                * self.row_epoch_beta
            )
            or self.campaign_confidence_lower
            != 1 - self.campaign_joint_tail_upper
            or self.novel_child_cardinality_rule
            != NOVEL_CHILD_CARDINALITY_RULE
            or self.raw_word_pairing_rule != RAW_WORD_PAIRING_RULE
            or self.confirmatory_execution_manifest_id is not None
            or self.confirmatory_profile_finalized is not False
            or self.first_remote_main_commit_required is not True
            or self.anchor_commit_id is not None
            or self.target_execution_allowed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise TransferGuidedAcquisitionPreregistrationInvariantViolation(
                "V0-072 preregistration changed or execution was enabled"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_adaptive_acquisition_preregistration.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "confirmatory_family_generation": (
                CONFIRMATORY_FAMILY_GENERATION
            ),
            "retired_development_dry_run_ids": list(
                RETIRED_DEVELOPMENT_DRY_RUN_IDS
            ),
            "superseded_draft_preregistration_ids": list(
                SUPERSEDED_DRAFT_PREREGISTRATION_IDS
            ),
            "retired_development_dry_run_disposition": (
                "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
            ),
            "context_ids": list(self.context_ids),
            "environment_manifest_id": self.environment_manifest_id,
            "arm_order": list(self.arm_order),
            "context_arm_occurrences": {
                "context_count": len(self.context_ids),
                "arm_count": len(self.arm_order),
                "occurrence_count": CONFIRMATORY_OCCURRENCE_COUNT,
                "order": "CONTEXT_MAJOR_THEN_FROZEN_ARM_ORDER",
                "all_occurrences_retained": True,
                "replacement_allowed": False,
                "campaign_early_stop_allowed": False,
            },
            "terminal_codes": list(self.terminal_codes),
            "physical_row_cap_sum_per_confidence_epoch": (
                self.physical_row_cap_sum_per_confidence_epoch
            ),
            "maximum_confidence_epochs_per_physical_row": (
                self.maximum_confidence_epochs_per_physical_row
            ),
            "maximum_promotions_per_physical_row": (
                self.maximum_promotions_per_physical_row
            ),
            "maximum_promotion_authorities_per_context": (
                self.maximum_promotion_authorities_per_context
            ),
            "row_epoch_authority_cap_rule": (
                self.row_epoch_authority_cap_rule
            ),
            "family_row_epoch_cap": self.family_row_epoch_cap,
            "maximum_rounds": self.maximum_rounds,
            "initial_acquisition_schedule": {
                "discovery_draws_per_physical_row": (
                    self.initial_discovery_draws_per_physical_row
                ),
                "validation_draws_per_physical_row": (
                    self.initial_validation_draws_per_physical_row
                ),
                "closure_order": self.initial_closure_order,
                "same_for_all_arms": True,
                "starts_cold": True,
                "source_or_v068_target_rows_imported": False,
                "accepted_draws_enter_online_endpoint": True,
                "maximum_accepted_draw_cap_per_arm": (
                    self.maximum_initial_accepted_draw_cap_per_arm
                ),
            },
            "incremental_acquisition_schedule": {
                "promotion_validation_draws_per_round": (
                    self.promotion_validation_draws_per_round
                ),
                "new_child_discovery_draws_per_physical_row": (
                    self.new_child_discovery_draws_per_physical_row
                ),
                "new_child_validation_draws_per_physical_row": (
                    self.new_child_validation_draws_per_physical_row
                ),
                "maximum_new_child_action_rows_across_rounds": (
                    self.maximum_new_child_action_rows_across_rounds
                ),
                "maximum_two_round_incremental_draw_cap_per_arm": (
                    self.maximum_two_round_incremental_draw_cap_per_arm
                ),
                "per_round_formula": (
                    "2048+n_new_child_actions*(64+8192)"
                ),
                "fresh_validation_and_discovery_streams_required": True,
                "fresh_parent_discovery_forbidden": True,
                "cumulative_cap_rule": INCREMENTAL_CUMULATIVE_CAP_RULE,
            },
            "confidence_allocation": {
                "row_epoch_beta": _fdoc(self.row_epoch_beta),
                "maximum_arm_bound_row_epoch_authorities_per_arm": (
                    self.maximum_arm_bound_row_epoch_authorities_per_arm
                ),
                "maximum_campaign_row_epoch_authorities": (
                    self.maximum_campaign_row_epoch_authorities
                ),
                "campaign_joint_tail_upper": _fdoc(
                    self.campaign_joint_tail_upper
                ),
                "campaign_confidence_lower": _fdoc(
                    self.campaign_confidence_lower
                ),
                "maximum_support_descriptors_per_row_epoch": 16,
                "event_alpha_rule": (
                    "ROW_EPOCH_BETA_DIVIDED_BY_SUPPORT_CARDINALITY_PLUS_ONE"
                ),
                "confidence_sequence": (
                    "V068_TIME_UNIFORM_BERNOULLI_MIXTURE_CS"
                ),
                "proof_rule": "FINITE_UNION_BOUND_NO_INDEPENDENCE_REQUIRED",
            },
            "novel_child_cardinality_rule": (
                self.novel_child_cardinality_rule
            ),
            "raw_word_pairing_rule": self.raw_word_pairing_rule,
            "raw_word_pairing_deduplicates_statistical_evidence": False,
            "raw_word_pairing_deduplicates_charged_work": False,
            "cross_arm_independence_claimed": False,
            "arm_bound_evidence_identities_required": True,
            "adaptive_audit_checkpoints": list(
                ADAPTIVE_AUDIT_CHECKPOINTS
            ),
            "intermediate_peeking_allowed": False,
            "third_adaptive_round_allowed": False,
            "round2_rebuilds_model_plan_frontier_and_registry": True,
            "matched_direct_ground_profile": {
                "validation_checkpoints": list(
                    DIRECT_VALIDATION_CHECKPOINTS
                ),
                "rule": DIRECT_BASELINE_RULE,
                "quotient_sharing": False,
            },
            "exact_lazy_resource_limits": dict(
                EXACT_LAZY_RESOURCE_LIMITS
            ),
            "fallback_rule": (
                "ONLY_AFTER_REGISTERED_ACQUISITION_STOPPING_PATH_"
                "FALLBACK_CLOSURE_IS_NOT_ENDPOINT_ACQUISITION_SUCCESS"
            ),
            "endpoint_eligibility": (
                "CONDITIONAL_PLAN_CERTIFICATE_AND_"
                "INDEPENDENT_EXACT_EVALUATION_PASS"
            ),
            "contextwise_source_coverage_noninferior_to": [
                "NO_PRIOR",
                "MATCHED_DIRECT_GROUND",
            ],
            "source_positive_coverage_required": {
                "required_contexts": 3,
                "registered_contexts": 3,
            },
            "online_draw_total_includes": [
                "COLD_INITIAL_MODEL",
                "FAILED_ACQUISITION_WORK",
                "INCREMENTAL_ACQUISITION",
            ],
            "offline_source_cost_rule": (
                "CARDINALITY_OF_UNION_OF_VERIFIED_SOURCE_RAW_IDS_"
                "REPORTED_SEPARATELY"
            ),
            "formal_exact_iid_implementation_claimed": False,
            "formal_exact_iid_plan_certificate": False,
            "randomness_claim_scope": (
                "REPRODUCIBLE_SPLITMIX64_TAPE_CONDITIONAL_ON_"
                "IDEALIZED_IID_MODEL_ONLY"
            ),
            "confirmatory_execution_manifest_required": (
                CONFIRMATORY_EXECUTION_MANIFEST_REQUIRED
            ),
            "confirmatory_execution_manifest_id": None,
            "confirmatory_profile_finalized": False,
            "primary_endpoint": (
                "SOURCE_ONLINE_DRAWS_STRICTLY_LESS_THAN_NO_PRIOR"
            ),
            "matched_sample_tax_endpoint": (
                "SOURCE_ONLINE_DRAWS_LE_MATCHED_DIRECT_GROUND"
            ),
            "first_remote_main_commit_required": True,
            "anchor_condition": (
                "FIRST_ORIGIN_MAIN_COMMIT_CONTAINING_THE_FINAL_NON_NULL_"
                "CONFIRMATORY_EXECUTION_MANIFEST_AND_FINAL_PREREGISTRATION_ID_"
                "WHOSE_PARENT_DOES_NOT_CONTAIN_THAT_PREREGISTRATION_ID"
            ),
            "anchor_commit_id": None,
            "target_execution_allowed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "NOT_RUN",
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistration_id": self.preregistration_id,
        }


def freeze_transfer_guided_acquisition_preregistration_v1(
) -> TransferGuidedAcquisitionPreregistrationV1:
    contexts = registered_heldout_public_contexts_v2()
    manifest = frozen_heldout_environment_manifest_v1()
    frozen = TransferGuidedAcquisitionPreregistrationV1(
        tuple(item.context_id for item in contexts),
        manifest.manifest_id,
        ARM_ORDER,
        TERMINAL_CODES,
        sum(
            item.maximum_physical_rows_per_confidence_epoch
            for item in contexts
        ),
        MAX_EPOCHS,
        MAX_PROMOTIONS_PER_PHYSICAL_ROW,
        MAX_PROMOTION_AUTHORITIES_PER_CONTEXT,
        ROW_EPOCH_AUTHORITY_CAP_RULE,
        FAMILY_ROW_EPOCH_CAP,
        MAX_ROUNDS,
        INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW,
        INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW,
        INITIAL_CLOSURE_ORDER,
        MAX_INITIAL_ACCEPTED_DRAW_CAP_PER_ARM,
        PROMOTION_VALIDATION_DRAWS_PER_ROUND,
        NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW,
        NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW,
        MAX_NEW_CHILD_ACTION_ROWS_ACROSS_ROUNDS,
        MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM,
        ROW_EPOCH_BETA,
        MAX_ROW_EPOCH_AUTHORITIES_PER_ARM,
        MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES,
        CAMPAIGN_JOINT_TAIL_UPPER,
        CAMPAIGN_CONFIDENCE_LOWER,
        NOVEL_CHILD_CARDINALITY_RULE,
        RAW_WORD_PAIRING_RULE,
    )
    if frozen.preregistration_id != DRAFT_PREREGISTRATION_ID:
        raise TransferGuidedAcquisitionPreregistrationInvariantViolation(
            "nonauthorizing draft preregistration identity changed"
        )
    return frozen


__all__ = [
    "ARM_ORDER",
    "CAMPAIGN_CONFIDENCE_LOWER",
    "CAMPAIGN_JOINT_TAIL_UPPER",
    "CONFIRMATORY_FAMILY_GENERATION",
    "DIRECT_VALIDATION_CHECKPOINTS",
    "DIRECT_CHECKPOINT_CAP_TERMINAL_CODE",
    "DRAFT_PREREGISTRATION_ID",
    "EXACT_LAZY_RESOURCE_LIMITS",
    "FAMILY_ROW_EPOCH_CAP",
    "HiddenSpawnLawCommitmentV1",
    "HeldoutEnvironmentManifestV1",
    "HeldoutPublicGraphContextV2",
    "K7_MINUS_TWO_TOPOLOGY",
    "K7_TOPOLOGY",
    "MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES",
    "MAX_CONFIDENCE_EPOCHS_PER_PHYSICAL_ROW",
    "MAX_EPOCHS",
    "MAX_INITIAL_ACCEPTED_DRAW_CAP_PER_ARM",
    "MAX_NEW_CHILD_ACTION_ROWS_ACROSS_ROUNDS",
    "MAX_PROMOTIONS_PER_PHYSICAL_ROW",
    "MAX_PROMOTION_AUTHORITIES_PER_CONTEXT",
    "MAX_ROUNDS",
    "MAX_ROW_EPOCH_AUTHORITIES_PER_ARM",
    "MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM",
    "NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW",
    "NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW",
    "NOVEL_CHILD_CARDINALITY_RULE",
    "PROFILE_KEY",
    "RAW_WORD_PAIRING_RULE",
    "ROW_EPOCH_AUTHORITY_CAP_RULE",
    "ROW_EPOCH_BETA",
    "RETIRED_DEVELOPMENT_DRY_RUN_IDS",
    "SUPERSEDED_DRAFT_PREREGISTRATION_IDS",
    "TERMINAL_CODES",
    "TransferGuidedAcquisitionPreregistrationInvariantViolation",
    "TransferGuidedAcquisitionPreregistrationV1",
    "W7_TOPOLOGY",
    "freeze_transfer_guided_acquisition_preregistration_v1",
    "frozen_heldout_environment_manifest_v1",
    "registered_heldout_public_contexts_v2",
]
