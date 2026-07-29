"""V0-072 five-arm campaign authority.

The registered entry point remains fail closed.  The executable path in this
module is a registration-disjoint development control.  Its source prior is
mechanically reconstructed from two immutable synthetic source-trial tapes;
the prior is ranking-only and cannot enter any model, Bellman backup, audit,
or certificate.

The final five-arm orchestration is defined below the source authority.  It
consumes only the typed selector/materializer/postbuild, matched-direct, and
campaign-reconciliation authorities.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import combinations
import multiprocessing
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as source_v2
from acfqp import v072_development_complete_adaptive_run_v1 as adaptive_complete
from acfqp import (
    v072_development_complete_adaptive_run_independent_verifier_v1
    as adaptive_complete_independent,
)
from acfqp import v072_incremental_materializer_v1 as materializer
from acfqp import v072_matched_direct_ground_baseline_v1 as matched_direct
from acfqp import (
    v072_matched_direct_ground_baseline_independent_verifier_v1
    as matched_direct_independent,
)
from acfqp import v072_campaign_reconciliation_authority_v1 as reconciliation
from acfqp import (
    v072_campaign_reconciliation_independent_verifier_v1
    as reconciliation_independent,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_five_arm_confirmatory_campaign_v1"
REGISTERED_EXECUTION_STATUS = (
    "NONAUTHORIZING_DRAFT_TARGET_LOCKED_GATE_NOT_RUN"
)
DEVELOPMENT_ROLE = (
    "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
)
SAMPLE_EFFICIENCY_GATE_STATUS = "NOT_RUN"

ARM_ORDER = prereg.ARM_ORDER
ADAPTIVE_ARM_ORDER = ARM_ORDER[:-1]
if ADAPTIVE_ARM_ORDER != selector.ADAPTIVE_ARMS:  # pragma: no cover
    raise RuntimeError("campaign and selector adaptive-arm order diverged")

SOURCE_BEFORE_DRAWS = 128
SOURCE_AFTER_DRAWS = 256
SOURCE_SUFFIX_DRAWS = SOURCE_AFTER_DRAWS - SOURCE_BEFORE_DRAWS


class V072FiveArmCampaignInvariantViolation(ValueError):
    """A source, arm, execution-order, or campaign identity is invalid."""


class RegisteredV072FiveArmCampaignLockedV1(RuntimeError):
    """The final manifest and semantic remote-main anchor do not exist."""


DOMAIN_TAGS = {
    "source_context": "acfqp:v072-five-arm-dev-source-context:v1",
    "source_raw": "acfqp:v072-five-arm-dev-source-raw-observation:v1",
    "source_trial": "acfqp:v072-five-arm-dev-source-trial:v1",
    "source_archive": "acfqp:v072-five-arm-dev-source-archive:v1",
    "source_authority": "acfqp:v072-five-arm-dev-source-authority:v1",
    "source_attestation": (
        "acfqp:v072-five-arm-dev-source-independent-attestation:v1"
    ),
    "ood_schema": "acfqp:v072-five-arm-dev-ood-schema:v1",
    "occurrence": "acfqp:v072-five-arm-dev-occurrence:v1",
    "campaign": "acfqp:v072-five-arm-dev-campaign:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("five-arm campaign content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072FiveArmCampaignInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072FiveArmCampaignInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072FiveArmCampaignInvariantViolation(
            "campaign arithmetic must remain exact"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


class DevelopmentSourceContextKeyV1(str, Enum):
    PATH4_SOURCE = "PATH4_SOURCE"
    STAR4_SOURCE = "STAR4_SOURCE"


class DevelopmentCampaignEventKindV1(str, Enum):
    SOURCE_PRIOR_FROZEN = "SOURCE_PRIOR_FROZEN"
    SOURCE_PRIOR_INDEPENDENTLY_VERIFIED = (
        "SOURCE_PRIOR_INDEPENDENTLY_VERIFIED"
    )
    ARM_STARTED = "ARM_STARTED"
    PREAUTHORIZATION_FROZEN = "PREAUTHORIZATION_FROZEN"
    ROUND_MATERIALIZED = "ROUND_MATERIALIZED"
    POSTBUILD_INDEPENDENTLY_VERIFIED = (
        "POSTBUILD_INDEPENDENTLY_VERIFIED"
    )
    ARM_TERMINAL_DERIVED = "ARM_TERMINAL_DERIVED"
    DIRECT_CHECKPOINT_DERIVED = "DIRECT_CHECKPOINT_DERIVED"
    DIRECT_INDEPENDENTLY_VERIFIED = "DIRECT_INDEPENDENTLY_VERIFIED"
    CAMPAIGN_RECONCILED = "CAMPAIGN_RECONCILED"


@dataclass(frozen=True, slots=True)
class DevelopmentFiveArmProtocolV1:
    """Frozen control protocol; it carries no target outcome or result."""

    source_authority_id: str
    source_attestation_id: str
    context_key: str = "V072_DEVELOPMENT_P4_FIVE_ARM_MECHANICS_V1"
    adaptive_law_key: materializer.DevelopmentLawKeyV1 = (
        materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_B
    )
    direct_law: matched_direct.DevelopmentMatchedDirectLawV1 = (
        matched_direct.DevelopmentMatchedDirectLawV1
        .FAILURE_RESIDUE_1_OF_100
    )
    arm_order: tuple[str, ...] = ARM_ORDER
    maximum_adaptive_rounds: int = 2
    occurrence_replacement_allowed: bool = False
    campaign_early_stop_allowed: bool = False
    caller_terminal_input_allowed: bool = False
    registered_target_execution: bool = False
    matched_scientific_endpoint_authority: bool = False
    _protocol_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.source_authority_id, "protocol source authority")
        _cid(self.source_attestation_id, "protocol source attestation")
        if (
            self.context_key
            != "V072_DEVELOPMENT_P4_FIVE_ARM_MECHANICS_V1"
            or self.adaptive_law_key
            is not materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_B
            or self.direct_law
            is not (
                matched_direct.DevelopmentMatchedDirectLawV1
                .FAILURE_RESIDUE_1_OF_100
            )
            or self.arm_order != ARM_ORDER
            or self.maximum_adaptive_rounds != 2
            or self.occurrence_replacement_allowed is not False
            or self.campaign_early_stop_allowed is not False
            or self.caller_terminal_input_allowed is not False
            or self.registered_target_execution is not False
            or self.matched_scientific_endpoint_authority is not False
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "development five-arm protocol was rerolled or overstated"
            )
        object.__setattr__(
            self,
            "_protocol_id",
            _content_id("campaign", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_five_arm_dev_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_authority_id": self.source_authority_id,
            "source_attestation_id": self.source_attestation_id,
            "context_key": self.context_key,
            "adaptive_law_key": self.adaptive_law_key.value,
            "direct_law": self.direct_law.value,
            "arm_order": list(self.arm_order),
            "maximum_adaptive_rounds": self.maximum_adaptive_rounds,
            "occurrence_replacement_allowed": False,
            "campaign_early_stop_allowed": False,
            "caller_terminal_input_allowed": False,
            "registered_target_execution": False,
            "matched_scientific_endpoint_authority": False,
            "development_backends_are_not_a_scientific_matched_pair": True,
            "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
        }

    @property
    def protocol_id(self) -> str:
        return self._protocol_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}


@dataclass(frozen=True, slots=True)
class DevelopmentSourceContextV1:
    context_key: DevelopmentSourceContextKeyV1
    topology_edges: tuple[tuple[int, int], ...]
    observation_law: str
    _context_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected = {
            DevelopmentSourceContextKeyV1.PATH4_SOURCE: (
                ((0, 1), (1, 2), (2, 3)),
                "PERIODIC_FEATURE_DIFFICULTY_LAW_P1_V1",
            ),
            DevelopmentSourceContextKeyV1.STAR4_SOURCE: (
                ((0, 1), (0, 2), (0, 3)),
                "PERIODIC_FEATURE_DIFFICULTY_LAW_P2_V1",
            ),
        }
        if (
            type(self.context_key) is not DevelopmentSourceContextKeyV1
            or (self.topology_edges, self.observation_law)
            != expected[self.context_key]
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "development source context is not the frozen source control"
            )
        object.__setattr__(
            self,
            "_context_id",
            _content_id("source_context", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_five_arm_dev_source_context.v1",
            "schema_version": SCHEMA_VERSION,
            "context_key": self.context_key.value,
            "topology_edges": [list(item) for item in self.topology_edges],
            "observation_law": self.observation_law,
            "source_role": "OFFLINE_DEVELOPMENT_PROPOSAL_ONLY",
            "registered_context": False,
            "target_observations_used": 0,
        }

    @property
    def context_id(self) -> str:
        return self._context_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def _development_source_contexts_v1(
) -> tuple[DevelopmentSourceContextV1, ...]:
    return (
        DevelopmentSourceContextV1(
            DevelopmentSourceContextKeyV1.PATH4_SOURCE,
            ((0, 1), (1, 2), (2, 3)),
            "PERIODIC_FEATURE_DIFFICULTY_LAW_P1_V1",
        ),
        DevelopmentSourceContextV1(
            DevelopmentSourceContextKeyV1.STAR4_SOURCE,
            ((0, 1), (0, 2), (0, 3)),
            "PERIODIC_FEATURE_DIFFICULTY_LAW_P2_V1",
        ),
    )


def _nonempty_subsets(values: tuple[str, ...]) -> Iterable[tuple[str, ...]]:
    for size in range(1, len(values) + 1):
        yield from combinations(values, size)


def _development_source_feature_universe_v1(
) -> tuple[source_v2.PortableAcquisitionCoreFeatureV2, ...]:
    destination_categories = tuple(
        item.value
        for item in robust.DestinationCategory
        if item is not robust.DestinationCategory.OTHER
    )
    stage_categories = {
        "ROOT": (
            robust.SelectedRowCategory.ROOT_SELECTED.value,
            robust.SelectedRowCategory.ROOT_CONCRETIZER_COMPONENT.value,
        ),
        "CONTINUATION": (
            robust.SelectedRowCategory.CONTINUATION_SELECTED.value,
            robust.SelectedRowCategory
            .CONTINUATION_CONCRETIZER_COMPONENT.value,
        ),
    }
    values = tuple(
        source_v2.PortableAcquisitionCoreFeatureV2(
            stage,
            category,
            action_bin,
            support_bin,
            tuple(destinations),
        )
        for stage, categories in stage_categories.items()
        for category in categories
        for action_bin in ("1", "2", "3_PLUS")
        for support_bin in ("1", "2", "3_PLUS")
        for destinations in _nonempty_subsets(destination_categories)
    )
    return tuple(sorted(values, key=lambda item: item.feature_key))


def _source_probability_numerator(
    *,
    context: DevelopmentSourceContextV1,
    feature_ordinal: int,
) -> int:
    difficulty = feature_ordinal % 24
    return (
        4 + difficulty
        if context.context_key
        is DevelopmentSourceContextKeyV1.PATH4_SOURCE
        else 8 + 2 * difficulty
    )


def _source_event_success(
    *,
    context: DevelopmentSourceContextV1,
    feature: source_v2.PortableAcquisitionCoreFeatureV2,
    feature_ordinal: int,
    sequence_index: int,
) -> bool:
    if (
        type(sequence_index) is not int
        or not 1 <= sequence_index <= SOURCE_AFTER_DRAWS
    ):
        raise V072FiveArmCampaignInvariantViolation(
            "source-trial sequence index is outside the frozen tape"
        )
    numerator = _source_probability_numerator(
        context=context,
        feature_ordinal=feature_ordinal,
    )
    rotation = int(feature.feature_key[:8], 16) % 64
    return (sequence_index - 1 + rotation) % 64 < numerator


def _source_raw_commitment_id(
    *,
    context: DevelopmentSourceContextV1,
    feature: source_v2.PortableAcquisitionCoreFeatureV2,
    sequence_index: int,
    success: bool,
) -> str:
    return _content_id(
        "source_raw",
        {
            "schema": "acfqp.v072_five_arm_dev_source_raw.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context.context_id,
            "portable_feature_key": feature.feature_key,
            "sequence_index": sequence_index,
            "success": success,
            "source_role": "OFFLINE_DEVELOPMENT_PROPOSAL_ONLY",
            "registered_target_evidence": False,
        },
    )


def _source_tape_replay(
    *,
    context: DevelopmentSourceContextV1,
    feature: source_v2.PortableAcquisitionCoreFeatureV2,
    feature_ordinal: int,
) -> tuple[int, int, str, str, str]:
    digest = hashlib.sha256()
    before_successes = 0
    after_successes = 0
    first = ""
    last = ""
    for sequence_index in range(1, SOURCE_AFTER_DRAWS + 1):
        success = _source_event_success(
            context=context,
            feature=feature,
            feature_ordinal=feature_ordinal,
            sequence_index=sequence_index,
        )
        commitment = _source_raw_commitment_id(
            context=context,
            feature=feature,
            sequence_index=sequence_index,
            success=success,
        )
        if not first:
            first = commitment
        last = commitment
        digest.update(bytes.fromhex(commitment))
        after_successes += int(success)
        if sequence_index <= SOURCE_BEFORE_DRAWS:
            before_successes += int(success)
    return before_successes, after_successes, first, last, digest.hexdigest()


def _proposal_uncertainty_proxy(
    *,
    draws: int,
    successes: int,
) -> Fraction:
    if (
        draws not in (SOURCE_BEFORE_DRAWS, SOURCE_AFTER_DRAWS)
        or type(successes) is not int
        or not 0 <= successes <= draws
    ):
        raise V072FiveArmCampaignInvariantViolation(
            "source proposal proxy received an invalid count"
        )
    # Ranking-only exact proxy.  It is not a confidence interval and cannot
    # enter target confidence or certificate arithmetic.
    return Fraction(successes + 1, draws + 1) / (draws // 64)


@dataclass(frozen=True, slots=True)
class DevelopmentSourceTrialV1:
    context: DevelopmentSourceContextV1
    portable_feature: source_v2.PortableAcquisitionCoreFeatureV2
    feature_ordinal: int
    before_success_count: int
    after_success_count: int
    first_raw_commitment_id: str
    last_raw_commitment_id: str
    ordered_raw_commitment_digest: str
    before_uncertainty_proxy: Fraction
    after_uncertainty_proxy: Fraction
    proposal_gain: Fraction
    gain_per_draw: Fraction
    _trial_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.first_raw_commitment_id, "first source commitment"),
            (self.last_raw_commitment_id, "last source commitment"),
            (self.ordered_raw_commitment_digest, "source tape digest"),
        ):
            _cid(value, field_name)
        if (
            type(self.context) is not DevelopmentSourceContextV1
            or type(self.portable_feature)
            is not source_v2.PortableAcquisitionCoreFeatureV2
            or type(self.feature_ordinal) is not int
            or self.feature_ordinal < 0
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "source trial lacks exact typed context/feature semantics"
            )
        replay = _source_tape_replay(
            context=self.context,
            feature=self.portable_feature,
            feature_ordinal=self.feature_ordinal,
        )
        before_proxy = _proposal_uncertainty_proxy(
            draws=SOURCE_BEFORE_DRAWS,
            successes=replay[0],
        )
        after_proxy = _proposal_uncertainty_proxy(
            draws=SOURCE_AFTER_DRAWS,
            successes=replay[1],
        )
        gain = max(Fraction(0), before_proxy - after_proxy)
        if (
            (
                self.before_success_count,
                self.after_success_count,
                self.first_raw_commitment_id,
                self.last_raw_commitment_id,
                self.ordered_raw_commitment_digest,
            )
            != replay
            or self.before_uncertainty_proxy != before_proxy
            or self.after_uncertainty_proxy != after_proxy
            or self.proposal_gain != gain
            or self.gain_per_draw != gain / SOURCE_SUFFIX_DRAWS
            or gain <= 0
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "source trial is not the exact replay-derived proposal trial"
            )
        object.__setattr__(
            self,
            "_trial_id",
            _content_id("source_trial", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_five_arm_dev_source_trial.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.context.context_id,
            "portable_feature_key": self.portable_feature.feature_key,
            "feature_ordinal": self.feature_ordinal,
            "before_draws": SOURCE_BEFORE_DRAWS,
            "after_draws": SOURCE_AFTER_DRAWS,
            "incremental_draws": SOURCE_SUFFIX_DRAWS,
            "before_success_count": self.before_success_count,
            "after_success_count": self.after_success_count,
            "first_raw_commitment_id": self.first_raw_commitment_id,
            "last_raw_commitment_id": self.last_raw_commitment_id,
            "ordered_raw_commitment_digest": (
                self.ordered_raw_commitment_digest
            ),
            "before_uncertainty_proxy": _fdoc(
                self.before_uncertainty_proxy
            ),
            "after_uncertainty_proxy": _fdoc(
                self.after_uncertainty_proxy
            ),
            "proposal_gain": _fdoc(self.proposal_gain),
            "gain_per_draw": _fdoc(self.gain_per_draw),
            "raw_tape_replayed": True,
            "ranking_only": True,
            "confidence_interval_claimed": False,
            "certificate_input": False,
            "caller_supplied_gain": False,
            "registered_target_evidence": False,
        }

    @property
    def trial_id(self) -> str:
        return self._trial_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_context": self.context.to_document(),
            "portable_feature": self.portable_feature.to_document(),
            "trial_id": self.trial_id,
        }


def _freeze_development_source_trial(
    *,
    context: DevelopmentSourceContextV1,
    feature: source_v2.PortableAcquisitionCoreFeatureV2,
    feature_ordinal: int,
) -> DevelopmentSourceTrialV1:
    replay = _source_tape_replay(
        context=context,
        feature=feature,
        feature_ordinal=feature_ordinal,
    )
    before_proxy = _proposal_uncertainty_proxy(
        draws=SOURCE_BEFORE_DRAWS,
        successes=replay[0],
    )
    after_proxy = _proposal_uncertainty_proxy(
        draws=SOURCE_AFTER_DRAWS,
        successes=replay[1],
    )
    gain = max(Fraction(0), before_proxy - after_proxy)
    return DevelopmentSourceTrialV1(
        context,
        feature,
        feature_ordinal,
        replay[0],
        replay[1],
        replay[2],
        replay[3],
        replay[4],
        before_proxy,
        after_proxy,
        gain,
        gain / SOURCE_SUFFIX_DRAWS,
    )


def _replay_development_source_consensus(
    trials: tuple[DevelopmentSourceTrialV1, ...],
) -> tuple[
    tuple[source_v2.SourceContextFeatureAggregateV2, ...],
    tuple[source_v2.NonrectangularFeatureConsensusV2, ...],
]:
    if (
        type(trials) is not tuple
        or not trials
        or any(type(item) is not DevelopmentSourceTrialV1 for item in trials)
    ):
        raise V072FiveArmCampaignInvariantViolation(
            "source consensus requires exact immutable source trials"
        )
    grouped: dict[
        tuple[str, str], list[DevelopmentSourceTrialV1]
    ] = {}
    for trial in trials:
        grouped.setdefault(
            (
                trial.context.context_id,
                trial.portable_feature.feature_key,
            ),
            [],
        ).append(trial)
    mean_by_key = {
        key: sum(
            (item.gain_per_draw for item in values),
            Fraction(0),
        )
        / len(values)
        for key, values in grouped.items()
    }
    by_context: dict[str, list[tuple[str, Fraction]]] = {}
    for (context_id, feature_key), mean in mean_by_key.items():
        by_context.setdefault(context_id, []).append((feature_key, mean))
    midranks: dict[tuple[str, str], Fraction] = {}
    degenerate: dict[str, bool] = {}
    for context_id, entries in by_context.items():
        ordered = sorted(entries, key=lambda item: (item[1], item[0]))
        denominator = len(ordered) - 1
        degenerate[context_id] = (
            denominator <= 0 or len({item[1] for item in ordered}) <= 1
        )
        cursor = 0
        while cursor < len(ordered):
            end = cursor + 1
            while end < len(ordered) and ordered[end][1] == ordered[cursor][1]:
                end += 1
            value = (
                Fraction(1, 2)
                if denominator <= 0
                else Fraction(cursor + end - 1, 2 * denominator)
            )
            for feature_key, _ in ordered[cursor:end]:
                midranks[(context_id, feature_key)] = value
            cursor = end
    aggregates = tuple(
        sorted(
            (
                source_v2.SourceContextFeatureAggregateV2(
                    context_id,
                    feature_key,
                    tuple(
                        sorted(
                            item.trial_id
                            for item in grouped[
                                (context_id, feature_key)
                            ]
                        )
                    ),
                    mean_by_key[(context_id, feature_key)],
                    midranks[(context_id, feature_key)],
                    degenerate[context_id],
                )
                for context_id, feature_key in sorted(grouped)
            ),
            key=lambda item: item.aggregate_id,
        )
    )
    by_feature: dict[
        str, list[source_v2.SourceContextFeatureAggregateV2]
    ] = {}
    for aggregate in aggregates:
        by_feature.setdefault(aggregate.feature_key, []).append(aggregate)
    consensus: list[source_v2.NonrectangularFeatureConsensusV2] = []
    for feature_key, values in by_feature.items():
        ordered = sorted(values, key=lambda item: item.source_context_id)
        ranks = tuple(item.normalized_midrank for item in ordered)
        mean_rank = sum(ranks, Fraction(0)) / len(ranks)
        worst_rank = min(ranks)
        disagreement = mean_rank - worst_rank
        mean_gain = sum(
            (item.mean_gain_per_draw for item in ordered),
            Fraction(0),
        ) / len(ordered)
        any_degenerate = any(
            item.context_ranking_degenerate for item in ordered
        )
        disposition = (
            source_v2.FeatureConsensusDispositionV2.INSUFFICIENT_CONTEXTS
            if len(ordered) < source_v2.MIN_SOURCE_CONTEXTS_PER_FEATURE
            else (
                source_v2.FeatureConsensusDispositionV2
                .DEGENERATE_CONTEXT_RANKING
                if any_degenerate
                else (
                    source_v2.FeatureConsensusDispositionV2
                    .NONPOSITIVE_SOURCE_GAIN
                    if mean_gain <= 0
                    else (
                        source_v2.FeatureConsensusDispositionV2
                        .HIGH_DISAGREEMENT
                        if disagreement
                        > source_v2.MAX_MIDRANK_DISAGREEMENT
                        else source_v2.FeatureConsensusDispositionV2.APPLIED
                    )
                )
            )
        )
        multiplier = (
            source_v2.MIN_PRIOR_MULTIPLIER
            + (
                source_v2.MAX_PRIOR_MULTIPLIER
                - source_v2.MIN_PRIOR_MULTIPLIER
            )
            * mean_rank
            if disposition
            is source_v2.FeatureConsensusDispositionV2.APPLIED
            else source_v2.NEUTRAL_PRIOR_MULTIPLIER
        )
        consensus.append(
            source_v2.NonrectangularFeatureConsensusV2(
                feature_key,
                tuple(item.source_context_id for item in ordered),
                tuple(sorted(item.aggregate_id for item in ordered)),
                mean_gain,
                mean_rank,
                worst_rank,
                disagreement,
                any_degenerate,
                disposition,
                multiplier,
            )
        )
    return aggregates, tuple(
        sorted(consensus, key=lambda item: item.consensus_id)
    )


@dataclass(frozen=True, slots=True)
class DevelopmentSourcePriorAuthorityV1:
    contexts: tuple[DevelopmentSourceContextV1, ...]
    trials: tuple[DevelopmentSourceTrialV1, ...]
    context_feature_aggregates: tuple[
        source_v2.SourceContextFeatureAggregateV2, ...
    ]
    consensus: tuple[source_v2.NonrectangularFeatureConsensusV2, ...]
    source_archive_id: str
    source_prior_binding: selector.VerifiedSourcePriorBindingV2
    ood_abstention: selector.OodPriorTypedAbstentionV2
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected_contexts = _development_source_contexts_v1()
        expected_features = _development_source_feature_universe_v1()
        if (
            self.contexts != expected_contexts
            or type(self.trials) is not tuple
            or tuple(item.trial_id for item in self.trials)
            != tuple(sorted({item.trial_id for item in self.trials}))
            or {
                item.portable_feature.feature_key for item in self.trials
            }
            != {item.feature_key for item in expected_features}
            or {
                item.context.context_id for item in self.trials
            }
            != {item.context_id for item in expected_contexts}
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "development source trial inventory is incomplete"
            )
        aggregates, consensus = _replay_development_source_consensus(
            self.trials
        )
        expected_archive_id = _content_id(
            "source_archive",
            {
                "schema": "acfqp.v072_five_arm_dev_source_archive.v1",
                "schema_version": SCHEMA_VERSION,
                "source_context_ids": [
                    item.context_id for item in self.contexts
                ],
                "source_trial_ids": [item.trial_id for item in self.trials],
                "aggregate_ids": [
                    item.aggregate_id for item in aggregates
                ],
                "consensus_ids": [
                    item.consensus_id for item in consensus
                ],
                "source_frozen": True,
                "proposal_only": True,
                "registered_target_evidence": False,
            },
        )
        if (
            self.context_feature_aggregates != aggregates
            or self.consensus != consensus
            or self.source_archive_id != expected_archive_id
            or self.source_prior_binding.archive_id != expected_archive_id
            or self.source_prior_binding.consensus != consensus
            or self.source_prior_binding.may_certify is not False
            or self.ood_abstention.rejected_prior_id
            != self.source_prior_binding.source_prior_binding_id
            or self.ood_abstention.source_numerical_inputs_absent is not True
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "development source prior was not derived from source trials"
            )
        object.__setattr__(
            self,
            "_authority_id",
            _content_id("source_authority", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_five_arm_dev_source_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_context_ids": [
                item.context_id for item in self.contexts
            ],
            "source_archive_id": self.source_archive_id,
            "source_prior_binding_id": (
                self.source_prior_binding.source_prior_binding_id
            ),
            "ood_abstention_id": self.ood_abstention.abstention_id,
            "source_trial_count": len(self.trials),
            "source_raw_accepted_draws": (
                len(self.trials) * SOURCE_AFTER_DRAWS
            ),
            "consensus_count": len(self.consensus),
            "source_quantities_are_proposal_only": True,
            "source_quantities_in_certificate_inputs": 0,
            "caller_supplied_gain": False,
            "caller_supplied_rank": False,
            "caller_supplied_multiplier": False,
            "registered_target_evidence": False,
            "sample_efficiency_evidence": False,
        }

    @property
    def authority_id(self) -> str:
        return self._authority_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "contexts": [item.to_document() for item in self.contexts],
            "trials": [item.to_document() for item in self.trials],
            "context_feature_aggregates": [
                item.to_document()
                for item in self.context_feature_aggregates
            ],
            "consensus": [item.to_document() for item in self.consensus],
            "source_prior_binding": (
                self.source_prior_binding.to_document()
            ),
            "ood_abstention": self.ood_abstention.to_document(),
            "authority_id": self.authority_id,
        }


@dataclass(frozen=True, slots=True)
class DevelopmentSourcePriorIndependentAttestationV1:
    authority_id: str
    source_archive_id: str
    source_prior_binding_id: str
    source_context_count: int
    source_trial_count: int
    source_raw_accepted_draws: int
    applied_consensus_count: int
    verified: bool = True

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.authority_id, "source authority"),
            (self.source_archive_id, "source archive"),
            (self.source_prior_binding_id, "source prior binding"),
        ):
            _cid(value, field_name)
        if (
            self.source_context_count != 2
            or self.source_trial_count <= 0
            or self.source_raw_accepted_draws
            != self.source_trial_count * SOURCE_AFTER_DRAWS
            or self.applied_consensus_count <= 0
            or self.verified is not True
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "source-prior independent attestation is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_five_arm_dev_source_independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authority_id": self.authority_id,
            "source_archive_id": self.source_archive_id,
            "source_prior_binding_id": self.source_prior_binding_id,
            "source_context_count": self.source_context_count,
            "source_trial_count": self.source_trial_count,
            "source_raw_accepted_draws": self.source_raw_accepted_draws,
            "applied_consensus_count": self.applied_consensus_count,
            "raw_tapes_replayed": True,
            "aggregate_midrank_consensus_replayed": True,
            "caller_quantities_trusted": False,
            "proposal_only": True,
            "may_certify": False,
            "registered_target_evidence": False,
            "verified": True,
        }

    @property
    def attestation_id(self) -> str:
        return _content_id("source_attestation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def freeze_development_source_prior_authority_v1(
) -> DevelopmentSourcePriorAuthorityV1:
    """Build a source-only proposal authority; no target input is accepted."""

    contexts = _development_source_contexts_v1()
    features = _development_source_feature_universe_v1()
    trials = tuple(
        sorted(
            (
                _freeze_development_source_trial(
                    context=context,
                    feature=feature,
                    feature_ordinal=ordinal,
                )
                for context in contexts
                for ordinal, feature in enumerate(features)
            ),
            key=lambda item: item.trial_id,
        )
    )
    aggregates, consensus = _replay_development_source_consensus(trials)
    archive_id = _content_id(
        "source_archive",
        {
            "schema": "acfqp.v072_five_arm_dev_source_archive.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_ids": [
                item.context_id for item in contexts
            ],
            "source_trial_ids": [item.trial_id for item in trials],
            "aggregate_ids": [item.aggregate_id for item in aggregates],
            "consensus_ids": [item.consensus_id for item in consensus],
            "source_frozen": True,
            "proposal_only": True,
            "registered_target_evidence": False,
        },
    )
    binding = selector.VerifiedSourcePriorBindingV2(
        archive_id,
        source_v2.FEATURE_SCHEMA_ID,
        consensus,
    )
    rejected_schema_id = _content_id(
        "ood_schema",
        {
            "schema": "acfqp.v072_five_arm_dev_ood_schema.v1",
            "schema_version": SCHEMA_VERSION,
            "name": "DEVELOPMENT_INTENTIONALLY_INCOMPATIBLE_FEATURE_SCHEMA",
            "compatible_with": [],
            "numerical_inputs": [],
        },
    )
    abstention = selector.OodPriorTypedAbstentionV2(
        binding.source_prior_binding_id,
        rejected_schema_id,
    )
    return DevelopmentSourcePriorAuthorityV1(
        contexts,
        trials,
        aggregates,
        consensus,
        archive_id,
        binding,
        abstention,
    )


def verify_development_source_prior_authority_independently_v1(
    claimed: DevelopmentSourcePriorAuthorityV1,
) -> DevelopmentSourcePriorIndependentAttestationV1:
    """Delegate to separately implemented raw/consensus/content replay."""

    from acfqp import (
        v072_five_arm_source_prior_independent_verifier_v1 as independent,
    )

    try:
        return (
            independent
            .verify_development_source_prior_authority_independently_v1(
                claimed
            )
        )
    except (
        independent
        .IndependentDevelopmentSourcePriorVerificationFailure
    ) as error:
        raise V072FiveArmCampaignInvariantViolation(
            f"independent source-prior replay failed: {error}"
        ) from error


def freeze_development_five_arm_protocol_v1(
    *,
    source_authority: DevelopmentSourcePriorAuthorityV1,
    source_attestation: DevelopmentSourcePriorIndependentAttestationV1,
) -> DevelopmentFiveArmProtocolV1:
    if (
        type(source_authority) is not DevelopmentSourcePriorAuthorityV1
        or type(source_attestation)
        is not DevelopmentSourcePriorIndependentAttestationV1
        or source_attestation.authority_id != source_authority.authority_id
        or source_attestation.source_archive_id
        != source_authority.source_archive_id
        or source_attestation.source_prior_binding_id
        != source_authority.source_prior_binding.source_prior_binding_id
    ):
        raise V072FiveArmCampaignInvariantViolation(
            "five-arm protocol lacks its matching source attestation"
        )
    return DevelopmentFiveArmProtocolV1(
        source_authority.authority_id,
        source_attestation.attestation_id,
    )


def freeze_development_shared_context_binding_v1(
    *,
    protocol: DevelopmentFiveArmProtocolV1,
) -> reconciliation.DevelopmentSharedExperimentalContextBindingV1:
    if type(protocol) is not DevelopmentFiveArmProtocolV1:
        raise V072FiveArmCampaignInvariantViolation(
            "shared-context binding requires the exact campaign protocol"
        )
    adaptive_context_id = (
        materializer.development_public_context_v1().context_id
    )
    direct_context_id = (
        matched_direct.development_matched_direct_context_id_v1()
    )
    return reconciliation.DevelopmentSharedExperimentalContextBindingV1(
        protocol.context_key,
        tuple(
            (
                arm,
                (
                    direct_context_id
                    if arm == "MATCHED_DIRECT_GROUND"
                    else adaptive_context_id
                ),
            )
            for arm in protocol.arm_order
        ),
    )


def development_logical_occurrence_id_v1(
    *,
    protocol: DevelopmentFiveArmProtocolV1,
    arm: str,
) -> str:
    """Derive one arm-bound occurrence identity in the frozen campaign order."""

    if (
        type(protocol) is not DevelopmentFiveArmProtocolV1
        or type(arm) is not str
        or arm not in protocol.arm_order
    ):
        raise V072FiveArmCampaignInvariantViolation(
            "development occurrence requires one frozen protocol arm"
        )
    return _content_id(
        "occurrence",
        {
            "schema": "acfqp.v072_five_arm_dev_logical_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "protocol_id": protocol.protocol_id,
            "mechanics_context_key": protocol.context_key,
            "arm": arm,
            "arm_ordinal": protocol.arm_order.index(arm),
            "occurrence_replacement_allowed": False,
            "registered_target_evidence": False,
        },
    )


def development_prior_inputs_for_arm_v1(
    *,
    arm: selector.TargetSelectionArmV2,
    source_authority: DevelopmentSourcePriorAuthorityV1,
    source_attestation: DevelopmentSourcePriorIndependentAttestationV1,
) -> tuple[
    selector.VerifiedSourcePriorBindingV2 | None,
    selector.OodPriorTypedAbstentionV2 | None,
]:
    """Resolve proposal-only arm inputs without accepting numerical claims."""

    if (
        type(arm) is not selector.TargetSelectionArmV2
        or type(source_authority) is not DevelopmentSourcePriorAuthorityV1
        or type(source_attestation)
        is not DevelopmentSourcePriorIndependentAttestationV1
        or source_attestation.authority_id != source_authority.authority_id
        or source_attestation.source_archive_id
        != source_authority.source_archive_id
        or source_attestation.source_prior_binding_id
        != source_authority.source_prior_binding.source_prior_binding_id
    ):
        raise V072FiveArmCampaignInvariantViolation(
            "arm prior resolution lacks the matching independently verified "
            "source authority"
        )
    if arm in (
        selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
        selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
    ):
        return source_authority.source_prior_binding, None
    if arm is selector.TargetSelectionArmV2.NO_PRIOR:
        return None, None
    if arm is selector.TargetSelectionArmV2.OOD_ABSTENTION:
        return None, source_authority.ood_abstention
    raise V072FiveArmCampaignInvariantViolation(
        "matched direct ground has no adaptive prior input"
    )


def _adaptive_schedule_signature(
    run: adaptive_complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> tuple[tuple[tuple[Any, ...], ...], ...]:
    signatures = []
    for selection in run.round_selections:
        score_by_candidate = {
            item.candidate_id: item for item in selection.scores
        }
        signatures.append(
            tuple(
                (
                    score_by_candidate[entry.candidate_id].feature_key,
                    entry.score,
                    entry.gain,
                    entry.exact_draw_upper,
                    entry.gain_eligible,
                    entry.cap_eligible,
                )
                for entry in selection.schedule.entries
            )
        )
    return tuple(signatures)


def _selected_feature_signature(
    run: adaptive_complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> tuple[str, ...]:
    return tuple(
        next(
            item.feature_key
            for item in selection.scores
            if item.candidate_id
            == selection.authorization.selected_candidate_id
        )
        for selection in run.round_selections
    )


def _incremental_streams(
    run: adaptive_complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> tuple[materializer.DevelopmentRawObservationStreamV1, ...]:
    return tuple(
        stream
        for handoff in run.handoffs
        for stream in (
            handoff.parent_validation_stream,
            *(
                child_stream
                for child in handoff.child_rows
                for child_stream in (
                    child.discovery_stream,
                    child.validation_stream,
                )
            ),
        )
    )


def _arm_free_crn_map(
    run: adaptive_complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> dict[tuple[int, str, str, int], tuple[str, str, tuple[int, ...]]]:
    return {
        (
            stream.round_index,
            stream.physical_row_id,
            stream.lane.value,
            stream.draw_count,
        ): (
            stream.seed_id,
            stream.raw_word_digest,
            stream.outcome_bucket_counts,
        )
        for stream in _incremental_streams(run)
    }


@dataclass(frozen=True, slots=True)
class DevelopmentFiveArmCampaignRunV1:
    """One complete development five-arm bundle; it has no endpoint claim."""

    source_authority: DevelopmentSourcePriorAuthorityV1
    source_attestation: DevelopmentSourcePriorIndependentAttestationV1
    protocol: DevelopmentFiveArmProtocolV1
    context_binding: (
        reconciliation.DevelopmentSharedExperimentalContextBindingV1
    )
    adaptive_runs: tuple[
        adaptive_complete.DevelopmentCompleteAdaptivePlanningRunV1, ...
    ]
    adaptive_attestations: tuple[
        adaptive_complete_independent
        .IndependentCompleteAdaptiveRunAttestationV1,
        ...,
    ]
    direct_run: matched_direct.MatchedDirectGroundRunV1
    direct_attestation: (
        matched_direct_independent
        .MatchedDirectGroundIndependentVerificationV1
    )
    reconciled_occurrences: tuple[
        reconciliation.ReconciledOperationalOccurrenceV1, ...
    ]
    reconciliation_ledger: (
        reconciliation.CampaignReconciliationLedgerV1
    )
    reconciliation_attestation: (
        reconciliation_independent
        .IndependentCampaignReconciliationAttestationV1
    )
    _campaign_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.source_authority)
            is not DevelopmentSourcePriorAuthorityV1
            or type(self.source_attestation)
            is not DevelopmentSourcePriorIndependentAttestationV1
            or type(self.protocol) is not DevelopmentFiveArmProtocolV1
            or type(self.context_binding)
            is not (
                reconciliation
                .DevelopmentSharedExperimentalContextBindingV1
            )
            or type(self.adaptive_runs) is not tuple
            or len(self.adaptive_runs) != 4
            or any(
                type(item)
                is not (
                    adaptive_complete
                    .DevelopmentCompleteAdaptivePlanningRunV1
                )
                for item in self.adaptive_runs
            )
            or type(self.adaptive_attestations) is not tuple
            or len(self.adaptive_attestations) != 4
            or any(
                type(item)
                is not (
                    adaptive_complete_independent
                    .IndependentCompleteAdaptiveRunAttestationV1
                )
                for item in self.adaptive_attestations
            )
            or type(self.direct_run)
            is not matched_direct.MatchedDirectGroundRunV1
            or type(self.direct_attestation)
            is not (
                matched_direct_independent
                .MatchedDirectGroundIndependentVerificationV1
            )
            or type(self.reconciled_occurrences) is not tuple
            or len(self.reconciled_occurrences) != 5
            or any(
                type(item)
                is not reconciliation.ReconciledOperationalOccurrenceV1
                for item in self.reconciled_occurrences
            )
            or type(self.reconciliation_ledger)
            is not reconciliation.CampaignReconciliationLedgerV1
            or type(self.reconciliation_attestation)
            is not (
                reconciliation_independent
                .IndependentCampaignReconciliationAttestationV1
            )
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "five-arm campaign lacks one exact typed bundle"
            )
        if (
            self.source_attestation.authority_id
            != self.source_authority.authority_id
            or self.source_attestation.source_archive_id
            != self.source_authority.source_archive_id
            or self.source_attestation.source_prior_binding_id
            != (
                self.source_authority.source_prior_binding
                .source_prior_binding_id
            )
            or self.protocol.source_authority_id
            != self.source_authority.authority_id
            or self.protocol.source_attestation_id
            != self.source_attestation.attestation_id
            or self.protocol.arm_order != ARM_ORDER
            or self.context_binding.mechanics_context_key
            != self.protocol.context_key
            or self.context_binding.matched_endpoint_authority is not False
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "source/protocol/context identity chain is stale"
            )
        if tuple(item.arm.value for item in self.adaptive_runs) != (
            ADAPTIVE_ARM_ORDER
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "adaptive occurrences were skipped, replaced, or reordered"
            )
        if any(
            attestation.complete_run_id != run.run_id
            or attestation.arm != run.arm.value
            or attestation.logical_occurrence_id
            != run.logical_occurrence_id
            or attestation.total_accepted_draws
            != run.total_accepted_draws
            for run, attestation in zip(
                self.adaptive_runs,
                self.adaptive_attestations,
                strict=True,
            )
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "adaptive complete-run independent replay is stale"
            )
        if any(
            item.law_key is not self.protocol.adaptive_law_key
            for item in self.adaptive_runs
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "adaptive occurrence changed the frozen transition law"
            )
        if any(
            item.logical_occurrence_id
            != development_logical_occurrence_id_v1(
                protocol=self.protocol,
                arm=item.arm.value,
            )
            for item in self.adaptive_runs
        ) or self.direct_run.logical_occurrence_id != (
            development_logical_occurrence_id_v1(
                protocol=self.protocol,
                arm="MATCHED_DIRECT_GROUND",
            )
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "native occurrence was not bound to protocol and arm"
            )
        run_by_arm = {
            item.arm: item for item in self.adaptive_runs
        }
        source_binding_id = (
            self.source_authority.source_prior_binding
            .source_prior_binding_id
        )
        ood_id = self.source_authority.ood_abstention.abstention_id
        for arm, run in run_by_arm.items():
            expected_source = (
                source_binding_id
                if arm
                in (
                    selector.TargetSelectionArmV2
                    .SOURCE_CONSENSUS_PRIOR,
                    selector.TargetSelectionArmV2
                    .WRONG_CONSENSUS_PRIOR,
                )
                else None
            )
            expected_ood = (
                ood_id
                if arm
                is selector.TargetSelectionArmV2.OOD_ABSTENTION
                else None
            )
            if (
                run.handoffs[0].request.authorization
                .source_prior_binding_id
                != expected_source
                or run.handoffs[0].request.authorization
                .ood_abstention_id
                != expected_ood
                or any(
                    selection.authorization.source_prior_binding_id
                    != expected_source
                    or selection.authorization.ood_abstention_id
                    != expected_ood
                    for selection in run.round_selections
                )
            ):
                raise V072FiveArmCampaignInvariantViolation(
                    "adaptive prior input was transplanted across arms"
                )
        for arm in (
            selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
            selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
        ):
            selections = run_by_arm[arm].round_selections
            if (
                not selections
                or not any(
                    score.multiplier != Fraction(1)
                    for selection in selections
                    for score in selection.scores
                )
            ):
                raise V072FiveArmCampaignInvariantViolation(
                    "source/wrong prior produced no real ranking multiplier"
                )
        neutral = run_by_arm[selector.TargetSelectionArmV2.NO_PRIOR]
        ood = run_by_arm[selector.TargetSelectionArmV2.OOD_ABSTENTION]
        if (
            _adaptive_schedule_signature(neutral)
            != _adaptive_schedule_signature(ood)
            or _selected_feature_signature(neutral)
            != _selected_feature_signature(ood)
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "OOD abstention differs from arm-free no-prior scheduling"
            )
        crn_maps = tuple(
            _arm_free_crn_map(item) for item in self.adaptive_runs
        )
        common_keys = set.intersection(
            *(set(item) for item in crn_maps)
        )
        if not common_keys or any(
            len({mapping[key] for mapping in crn_maps}) != 1
            for key in common_keys
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "adaptive CRN words are not arm-free on paired rows"
            )
        occurrence_ids = tuple(
            item.logical_occurrence_id for item in self.adaptive_runs
        ) + (self.direct_run.logical_occurrence_id,)
        if len(set(occurrence_ids)) != 5:
            raise V072FiveArmCampaignInvariantViolation(
                "five-arm logical occurrence identities overlap"
            )
        disjoint_inventories = tuple(
            {
                item.run_id,
                *(
                    handoff.handoff_id for handoff in item.handoffs
                ),
                *(
                    result.result_id for result in item.postbuild_results
                ),
                *(
                    proof.range_proof_id
                    for handoff in item.handoffs
                    for proof in handoff.raw_commitment_ranges
                ),
                *(
                    proof.range_proof_id
                    for proof in item.handoffs[0]
                    .prior_cold_raw_commitment_ranges
                ),
                *(
                    transcript.upstream_row_evidence_id
                    for transcript in item.handoffs[0].request
                    .parent_evidence.upstream_root_rows
                ),
                *(
                    stream_id
                    for transcript in item.handoffs[0].request
                    .parent_evidence.upstream_root_rows
                    for stream_id in (
                        transcript.discovery_stream_id,
                        transcript.validation_stream_id,
                    )
                ),
            }
            for item in self.adaptive_runs
        )
        if any(
            disjoint_inventories[left] & disjoint_inventories[right]
            for left, right in combinations(range(4), 2)
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "arm-bound evidence or model identities overlap"
            )
        if (
            self.direct_attestation.run_id != self.direct_run.run_id
            or self.direct_attestation.logical_occurrence_id
            != self.direct_run.logical_occurrence_id
            or self.direct_attestation.terminal_class
            != self.direct_run.terminal_class.value
            or self.direct_attestation.terminal_code
            != self.direct_run.terminal_code.value
            or self.direct_run.source_prior_reads != 0
            or self.direct_run.quotient_planner_calls != 0
            or self.direct_run.local_promotion_calls != 0
            or self.direct_run.crn_cost_discount_draws != 0
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "matched direct arm used quotient/prior/local work"
            )
        if (
            tuple(
                item.arm for item in self.reconciled_occurrences
            )
            != ARM_ORDER
            or self.reconciliation_ledger.occurrences
            != self.reconciled_occurrences
            or self.reconciliation_ledger.order_profile
            is not (
                reconciliation.CampaignOrderProfileV1
                .CONTEXT_MAJOR_FROZEN_ARM_ORDER
            )
            or self.reconciliation_ledger.development_context_binding
            != self.context_binding
            or self.reconciliation_ledger.logical_occurrence_denominator
            != 5
            or self.reconciliation_ledger.total_terminal_artifacts != 5
            or self.reconciliation_ledger.crn_cost_discount_draws != 0
            or self.reconciliation_ledger
            .registered_target_evidence_count
            != 0
            or self.reconciliation_attestation.ledger_id
            != self.reconciliation_ledger.ledger_id
            or self.reconciliation_attestation
            .logical_occurrence_denominator
            != 5
            or self.reconciliation_attestation.crn_cost_discount_draws
            != 0
        ):
            raise V072FiveArmCampaignInvariantViolation(
                "campaign denominator/work reconciliation is incomplete"
            )
        object.__setattr__(
            self,
            "_campaign_id",
            _content_id("campaign", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_five_arm_development_campaign_run.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_authority_id": self.source_authority.authority_id,
            "source_attestation_id": self.source_attestation.attestation_id,
            "source_offline_accepted_draws": (
                self.source_attestation.source_raw_accepted_draws
            ),
            "protocol_id": self.protocol.protocol_id,
            "context_binding_id": self.context_binding.binding_id,
            "arm_order": list(ARM_ORDER),
            "adaptive_run_ids": [
                item.run_id for item in self.adaptive_runs
            ],
            "adaptive_attestation_ids": [
                item.attestation_id for item in self.adaptive_attestations
            ],
            "direct_run_id": self.direct_run.run_id,
            "direct_attestation_id":
                self.direct_attestation.verification_id,
            "reconciled_occurrence_ids": [
                item.occurrence_record_id
                for item in self.reconciled_occurrences
            ],
            "reconciliation_ledger_id":
                self.reconciliation_ledger.ledger_id,
            "reconciliation_attestation_id":
                self.reconciliation_attestation.attestation_id,
            "online_accepted_draws": (
                self.reconciliation_ledger.total_accepted_draws
            ),
            "logical_occurrence_denominator": 5,
            "all_terminal_artifacts_retained": True,
            "occurrence_replacement_allowed": False,
            "campaign_early_stop_allowed": False,
            "source_quantities_are_proposal_only": True,
            "source_quantities_in_certificate_inputs": 0,
            "crn_cost_discount_draws": 0,
            "caller_supplied_terminal": False,
            "caller_supplied_counts": False,
            "matched_scientific_endpoint_authority": False,
            "registered_target_evidence": False,
            "registered_execution_allowed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def campaign_id(self) -> str:
        return self._campaign_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_id": self.campaign_id}


def _run_and_verify_adaptive_arm_v1(
    job: tuple[
        materializer.DevelopmentLawKeyV1,
        selector.TargetSelectionArmV2,
        selector.VerifiedSourcePriorBindingV2 | None,
        selector.OodPriorTypedAbstentionV2 | None,
        str,
    ],
) -> tuple[
    adaptive_complete.DevelopmentCompleteAdaptivePlanningRunV1,
    adaptive_complete_independent
    .IndependentCompleteAdaptiveRunAttestationV1,
]:
    """Spawn-safe arm worker; it returns the run and fresh replay together."""

    law_key, arm, source_prior, ood_abstention, occurrence_id = job
    run = (
        adaptive_complete
        .run_development_complete_adaptive_planning_control_v1(
            law_key=law_key,
            arm=arm,
            source_prior=source_prior,
            ood_abstention=ood_abstention,
            logical_occurrence_id=occurrence_id,
        )
    )
    attestation = (
        adaptive_complete_independent
        .verify_development_complete_adaptive_run_v1(run)
    )
    return run, attestation


def _adaptive_jobs_v1(
    *,
    protocol: DevelopmentFiveArmProtocolV1,
    source_authority: DevelopmentSourcePriorAuthorityV1,
    source_attestation: DevelopmentSourcePriorIndependentAttestationV1,
) -> tuple[
    tuple[
        materializer.DevelopmentLawKeyV1,
        selector.TargetSelectionArmV2,
        selector.VerifiedSourcePriorBindingV2 | None,
        selector.OodPriorTypedAbstentionV2 | None,
        str,
    ],
    ...,
]:
    jobs = []
    for value in ADAPTIVE_ARM_ORDER:
        arm = selector.TargetSelectionArmV2(value)
        source_prior, ood_abstention = (
            development_prior_inputs_for_arm_v1(
                arm=arm,
                source_authority=source_authority,
                source_attestation=source_attestation,
            )
        )
        jobs.append(
            (
                protocol.adaptive_law_key,
                arm,
                source_prior,
                ood_abstention,
                development_logical_occurrence_id_v1(
                    protocol=protocol,
                    arm=arm.value,
                ),
            )
        )
    return tuple(jobs)


def _execute_adaptive_jobs_v1(
    jobs: tuple[
        tuple[
            materializer.DevelopmentLawKeyV1,
            selector.TargetSelectionArmV2,
            selector.VerifiedSourcePriorBindingV2 | None,
            selector.OodPriorTypedAbstentionV2 | None,
            str,
        ],
        ...,
    ],
    *,
    parallel: bool,
) -> tuple[
    tuple[
        adaptive_complete.DevelopmentCompleteAdaptivePlanningRunV1,
        adaptive_complete_independent
        .IndependentCompleteAdaptiveRunAttestationV1,
    ],
    ...,
]:
    if len(jobs) != 4:
        raise V072FiveArmCampaignInvariantViolation(
            "adaptive execution requires the exact four frozen arms"
        )
    if parallel:
        with ProcessPoolExecutor(
            max_workers=4,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            # executor.map preserves the frozen input order.  Each occurrence
            # remains fully charged; parallel wall time never discounts work.
            return tuple(
                executor.map(
                    _run_and_verify_adaptive_arm_v1,
                    jobs,
                    chunksize=1,
                )
            )
    return tuple(_run_and_verify_adaptive_arm_v1(job) for job in jobs)


def _run_development_five_arm_campaign_with_mode_v1(
    *,
    parallel: bool,
) -> DevelopmentFiveArmCampaignRunV1:
    source_authority = freeze_development_source_prior_authority_v1()
    source_attestation = (
        verify_development_source_prior_authority_independently_v1(
            source_authority
        )
    )
    protocol = freeze_development_five_arm_protocol_v1(
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    context_binding = freeze_development_shared_context_binding_v1(
        protocol=protocol,
    )
    pairs = _execute_adaptive_jobs_v1(
        _adaptive_jobs_v1(
            protocol=protocol,
            source_authority=source_authority,
            source_attestation=source_attestation,
        ),
        parallel=parallel,
    )
    direct_run = (
        matched_direct.run_development_matched_direct_ground_baseline_v1(
            law=protocol.direct_law,
            logical_occurrence_id=development_logical_occurrence_id_v1(
                protocol=protocol,
                arm="MATCHED_DIRECT_GROUND",
            ),
        )
    )
    direct_attestation = (
        matched_direct_independent
        .verify_matched_direct_ground_run_independently_v1(direct_run)
    )
    return _assemble_development_campaign_v1(
        source_authority=source_authority,
        source_attestation=source_attestation,
        protocol=protocol,
        context_binding=context_binding,
        adaptive_pairs=pairs,
        direct_run=direct_run,
        direct_attestation=direct_attestation,
    )


def _assemble_development_campaign_v1(
    *,
    source_authority: DevelopmentSourcePriorAuthorityV1,
    source_attestation: DevelopmentSourcePriorIndependentAttestationV1,
    protocol: DevelopmentFiveArmProtocolV1,
    context_binding: (
        reconciliation.DevelopmentSharedExperimentalContextBindingV1
    ),
    adaptive_pairs: tuple[
        tuple[
            adaptive_complete.DevelopmentCompleteAdaptivePlanningRunV1,
            adaptive_complete_independent
            .IndependentCompleteAdaptiveRunAttestationV1,
        ],
        ...,
    ],
    direct_run: matched_direct.MatchedDirectGroundRunV1,
    direct_attestation: (
        matched_direct_independent
        .MatchedDirectGroundIndependentVerificationV1
    ),
) -> DevelopmentFiveArmCampaignRunV1:
    adaptive_runs = tuple(item[0] for item in adaptive_pairs)
    adaptive_attestations = tuple(item[1] for item in adaptive_pairs)
    occurrences = tuple(
        reconciliation.reconcile_complete_adaptive_run_v1(item)
        for item in adaptive_runs
    ) + (reconciliation.reconcile_matched_direct_run_v1(direct_run),)
    ledger = reconciliation.reconcile_campaign_v1(
        occurrences=occurrences,
        order_profile=(
            reconciliation.CampaignOrderProfileV1
            .CONTEXT_MAJOR_FROZEN_ARM_ORDER
        ),
        development_context_binding=context_binding,
    )
    ledger_attestation = (
        reconciliation_independent
        .verify_campaign_reconciliation_independently_v1(ledger)
    )
    return DevelopmentFiveArmCampaignRunV1(
        source_authority,
        source_attestation,
        protocol,
        context_binding,
        adaptive_runs,
        adaptive_attestations,
        direct_run,
        direct_attestation,
        occurrences,
        ledger,
        ledger_attestation,
    )


def run_development_five_arm_campaign_v1(
) -> DevelopmentFiveArmCampaignRunV1:
    """Run all arms with four fixed spawn workers and retain every terminal."""

    return _run_development_five_arm_campaign_with_mode_v1(parallel=True)


def run_development_five_arm_campaign_serial_equivalence_v1(
) -> DevelopmentFiveArmCampaignRunV1:
    """Serial diagnostic with byte-identical semantics, IDs, and accounting."""

    return _run_development_five_arm_campaign_with_mode_v1(parallel=False)


def replay_development_five_arm_campaign_serial_equivalence_v1(
    reference: DevelopmentFiveArmCampaignRunV1,
) -> DevelopmentFiveArmCampaignRunV1:
    """Serially rerun adaptive arms against one parallel bundle's inputs."""

    if type(reference) is not DevelopmentFiveArmCampaignRunV1:
        raise V072FiveArmCampaignInvariantViolation(
            "serial equivalence requires one exact parallel campaign bundle"
        )
    pairs = _execute_adaptive_jobs_v1(
        _adaptive_jobs_v1(
            protocol=reference.protocol,
            source_authority=reference.source_authority,
            source_attestation=reference.source_attestation,
        ),
        parallel=False,
    )
    return _assemble_development_campaign_v1(
        source_authority=reference.source_authority,
        source_attestation=reference.source_attestation,
        protocol=reference.protocol,
        context_binding=reference.context_binding,
        adaptive_pairs=pairs,
        direct_run=reference.direct_run,
        direct_attestation=reference.direct_attestation,
    )


def run_registered_v072_five_arm_campaign_v1(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise RegisteredV072FiveArmCampaignLockedV1(
        "registered five-arm execution remains locked: "
        f"status={REGISTERED_EXECUTION_STATUS}, "
        f"draft_preregistration_id={prereg.DRAFT_PREREGISTRATION_ID}, "
        "confirmatory_execution_manifest_id=null, "
        "anchor_commit_id=null, target_execution_allowed=false"
    )


__all__ = [
    "ADAPTIVE_ARM_ORDER",
    "ARM_ORDER",
    "DEVELOPMENT_ROLE",
    "DevelopmentCampaignEventKindV1",
    "DevelopmentFiveArmCampaignRunV1",
    "DevelopmentFiveArmProtocolV1",
    "DevelopmentSourceContextKeyV1",
    "DevelopmentSourceContextV1",
    "DevelopmentSourcePriorAuthorityV1",
    "DevelopmentSourcePriorIndependentAttestationV1",
    "DevelopmentSourceTrialV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_EXECUTION_STATUS",
    "RegisteredV072FiveArmCampaignLockedV1",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "SOURCE_AFTER_DRAWS",
    "SOURCE_BEFORE_DRAWS",
    "V072FiveArmCampaignInvariantViolation",
    "development_logical_occurrence_id_v1",
    "development_prior_inputs_for_arm_v1",
    "freeze_development_source_prior_authority_v1",
    "freeze_development_five_arm_protocol_v1",
    "freeze_development_shared_context_binding_v1",
    "run_registered_v072_five_arm_campaign_v1",
    "run_development_five_arm_campaign_v1",
    "run_development_five_arm_campaign_serial_equivalence_v1",
    "replay_development_five_arm_campaign_serial_equivalence_v1",
    "verify_development_source_prior_authority_independently_v1",
]
