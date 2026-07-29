"""Verified V0-072 source-acquisition archive.

The archive is deliberately downstream of the frozen V0-068 campaign.  It
does not accept caller-provided gains, ranks, scores, source pairs, or feature
keys.  Seven registered adjacent quotient-checkpoint pairs are reconstructed
from campaign chronology and every score is recomputed with an independent
exact-``Fraction`` H=2 recurrence.

The portable feature contains only coarse relational roles and bins.  All
sample-dependent interval endpoints and all content identities live in a
separate identity-bound snapshot.  Consensus is per feature and therefore
nonrectangular: a missing or disputed feature abstains locally instead of
invalidating the entire source archive.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping, Sequence

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import observation_support_campaign_v1 as campaign_v1
from . import observation_support_graph_acquisition_v1 as graph_acquisition
from . import partial_support_robust_planner_v1 as robust


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "verified_source_acquisition_archive_v2"
FEATURE_SCHEMA_ID = hashlib.sha256(
    b"acfqp:portable-acquisition-core-feature:v2"
).hexdigest()
MIN_SOURCE_CONTEXTS_PER_FEATURE = 2
MAX_MIDRANK_DISAGREEMENT = Fraction(1, 4)
MIN_PRIOR_MULTIPLIER = Fraction(1, 2)
MAX_PRIOR_MULTIPLIER = Fraction(2)
NEUTRAL_PRIOR_MULTIPLIER = Fraction(1)

REGISTERED_ADJACENT_PAIRS: Mapping[str, tuple[tuple[int, int], ...]] = {
    "opaque_graph_w5_v0": ((2_048, 4_096),),
    "opaque_graph_k6_v0": (
        (2_048, 4_096),
        (4_096, 8_192),
        (8_192, 16_384),
    ),
    "opaque_graph_k6_minus_edge_v0": (
        (2_048, 4_096),
        (4_096, 8_192),
        (8_192, 16_384),
    ),
}


class VerifiedSourceAcquisitionArchiveInvariantViolation(ValueError):
    """Raised when source chronology, recurrence, or consensus is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
    except Exception as error:  # pragma: no cover - normalized boundary
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(
        f"acfqp:verified-source-acquisition-archive:{role}:v2".encode(
            "utf-8"
        )
        + b"\x00"
        + encoded
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _ids(values: Sequence[str], field: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            f"{field} must be an immutable tuple"
        )
    result = tuple(_cid(item, field) for item in values)
    if result != tuple(sorted(set(result))):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            f"{field} must be sorted and distinct"
        )
    return result


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "archive arithmetic must remain exact"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _bin_count(value: int) -> str:
    if type(value) is not int or value < 0:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "portable count bin input is invalid"
        )
    if value == 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_PLUS"


def _ordered_id_digest(
    domain: str,
    values: tuple[str, ...],
) -> str:
    if type(values) is not tuple:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "raw-prefix identity sequence must be an immutable tuple"
        )
    for value in values:
        _cid(value, "raw-prefix observation")
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(list(values))
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class PortableAcquisitionCoreFeatureV2:
    """Sample/probability-independent acquisition coordinate.

    No IDs, exact counts, interval endpoints, probabilities, vertex labels,
    or context names are admitted.
    """

    stage_role: str
    selected_row_category: str
    catalogue_action_count_bin: str
    concretizer_support_count_bin: str
    destination_category_presence: tuple[str, ...]
    feature_schema_id: str = FEATURE_SCHEMA_ID
    ids_stripped: bool = True
    exact_probabilities_absent: bool = True

    def __post_init__(self) -> None:
        valid_categories = {item.value for item in robust.SelectedRowCategory}
        valid_destination_categories = {
            item.value
            for item in robust.DestinationCategory
            if item is not robust.DestinationCategory.OTHER
        }
        valid_bins = {"0", "1", "2", "3_PLUS"}
        if (
            self.stage_role not in {"ROOT", "CONTINUATION"}
            or self.selected_row_category not in valid_categories
            or self.catalogue_action_count_bin not in valid_bins
            or self.concretizer_support_count_bin not in valid_bins
            or type(self.destination_category_presence) is not tuple
            or not self.destination_category_presence
            or self.destination_category_presence
            != tuple(sorted(set(self.destination_category_presence)))
            or not set(self.destination_category_presence).issubset(
                valid_destination_categories
            )
            or self.feature_schema_id != FEATURE_SCHEMA_ID
            or self.ids_stripped is not True
            or self.exact_probabilities_absent is not True
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "portable acquisition core feature is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_acquisition_core_feature.v2",
            "schema_version": SCHEMA_VERSION,
            "feature_schema_id": self.feature_schema_id,
            "stage_role": self.stage_role,
            "selected_row_category": self.selected_row_category,
            "catalogue_action_count_bin": (
                self.catalogue_action_count_bin
            ),
            "concretizer_support_count_bin": (
                self.concretizer_support_count_bin
            ),
            "destination_category_presence": list(
                self.destination_category_presence
            ),
            "ids_stripped": True,
            "exact_probabilities_absent": True,
            "exact_counts_absent": True,
            "vertex_labels_absent": True,
            "context_identity_absent": True,
            "observed_support_count_absent": True,
        }

    @property
    def feature_key(self) -> str:
        return _content_id("portable-feature", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "feature_key": self.feature_key}


@dataclass(frozen=True, slots=True)
class IdentityBoundMassIntervalV2:
    destination_id: str
    category: robust.DestinationCategory
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.destination_id, "snapshot destination")
        if (
            type(self.category) is not robust.DestinationCategory
            or type(self.lower) is not Fraction
            or type(self.upper) is not Fraction
            or not 0 <= self.lower <= self.upper <= 1
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "identity-bound mass interval is malformed"
            )

    def _document(self) -> dict[str, Any]:
        return {
            "destination_id": self.destination_id,
            "category": self.category.value,
            "lower": _fdoc(self.lower),
            "upper": _fdoc(self.upper),
        }


@dataclass(frozen=True, slots=True)
class RawPrefixExtensionProofV2:
    """Compact binding of one replayed physical validation-prefix extension."""

    binding_id: str
    support_epoch_id: str
    before_partial_row_id: str
    after_partial_row_id: str
    before_physical_evidence_id: str
    after_physical_evidence_id: str
    discovery_ids_digest: str
    before_validation_ids_digest: str
    after_validation_ids_digest: str
    suffix_ids_digest: str
    before_validation_draws: int
    after_validation_draws: int
    incremental_accepted_draws: int
    incremental_random_word_calls: int
    incremental_rejections: int
    exact_ordered_prefix: bool = True
    same_support_epoch: bool = True
    semantically_replayed_by_source_campaign_verification: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.binding_id, "raw-prefix binding"),
            (self.support_epoch_id, "raw-prefix support epoch"),
            (self.before_partial_row_id, "raw-prefix before row"),
            (self.after_partial_row_id, "raw-prefix after row"),
            (
                self.before_physical_evidence_id,
                "raw-prefix before evidence",
            ),
            (
                self.after_physical_evidence_id,
                "raw-prefix after evidence",
            ),
            (self.discovery_ids_digest, "raw-prefix discovery digest"),
            (
                self.before_validation_ids_digest,
                "raw-prefix before validation digest",
            ),
            (
                self.after_validation_ids_digest,
                "raw-prefix after validation digest",
            ),
            (self.suffix_ids_digest, "raw-prefix suffix digest"),
        ):
            _cid(value, field)
        if (
            any(
                type(value) is not int or value < 0
                for value in (
                    self.before_validation_draws,
                    self.after_validation_draws,
                    self.incremental_accepted_draws,
                    self.incremental_random_word_calls,
                    self.incremental_rejections,
                )
            )
            or self.after_validation_draws
            <= self.before_validation_draws
            or self.incremental_accepted_draws
            != self.after_validation_draws - self.before_validation_draws
            or self.incremental_random_word_calls
            != self.incremental_accepted_draws
            + self.incremental_rejections
            or self.exact_ordered_prefix is not True
            or self.same_support_epoch is not True
            or (
                self.semantically_replayed_by_source_campaign_verification
                is not True
            )
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "raw-prefix extension proof does not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_prefix_extension_proof.v2",
            "schema_version": SCHEMA_VERSION,
            "binding_id": self.binding_id,
            "support_epoch_id": self.support_epoch_id,
            "before_partial_row_id": self.before_partial_row_id,
            "after_partial_row_id": self.after_partial_row_id,
            "before_physical_evidence_id": (
                self.before_physical_evidence_id
            ),
            "after_physical_evidence_id": self.after_physical_evidence_id,
            "discovery_ids_digest": self.discovery_ids_digest,
            "before_validation_ids_digest": (
                self.before_validation_ids_digest
            ),
            "after_validation_ids_digest": (
                self.after_validation_ids_digest
            ),
            "suffix_ids_digest": self.suffix_ids_digest,
            "before_validation_draws": self.before_validation_draws,
            "after_validation_draws": self.after_validation_draws,
            "incremental_accepted_draws": self.incremental_accepted_draws,
            "incremental_random_word_calls": (
                self.incremental_random_word_calls
            ),
            "incremental_rejections": self.incremental_rejections,
            "exact_ordered_prefix": True,
            "same_support_epoch": True,
            "semantically_replayed_by_source_campaign_verification": True,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("raw-prefix-extension", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


@dataclass(frozen=True, slots=True)
class IdentityBoundLocalSnapshotV2:
    """Exact local source state; never used as a cross-context feature."""

    source_context_id: str
    before_execution_id: str
    after_execution_id: str
    before_model_id: str
    after_model_id: str
    before_audit_id: str
    after_audit_id: str
    threshold_profile_id: str
    before_checkpoint: int
    after_checkpoint: int
    before_row_id: str
    after_row_id: str
    state_id: str
    action_id: str
    remaining_horizon: int
    before_reward_lower: Fraction
    before_reward_upper: Fraction
    after_reward_lower: Fraction
    after_reward_upper: Fraction
    before_mass_intervals: tuple[IdentityBoundMassIntervalV2, ...]
    after_mass_intervals: tuple[IdentityBoundMassIntervalV2, ...]
    raw_prefix_extension: RawPrefixExtensionProofV2
    incremental_draws: int
    portable_feature_key: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.source_context_id, "snapshot context"),
            (self.before_execution_id, "before execution"),
            (self.after_execution_id, "after execution"),
            (self.before_model_id, "before model"),
            (self.after_model_id, "after model"),
            (self.before_audit_id, "before audit"),
            (self.after_audit_id, "after audit"),
            (self.threshold_profile_id, "snapshot threshold"),
            (self.before_row_id, "before row"),
            (self.after_row_id, "after row"),
            (self.state_id, "snapshot state"),
            (self.action_id, "snapshot action"),
            (self.portable_feature_key, "portable feature"),
        ):
            _cid(value, field)
        for value in (
            self.before_reward_lower,
            self.before_reward_upper,
            self.after_reward_lower,
            self.after_reward_upper,
        ):
            if type(value) is not Fraction or value < 0:
                raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                    "snapshot reward interval is invalid"
                )
        if (
            self.before_reward_lower > self.before_reward_upper
            or self.after_reward_lower > self.after_reward_upper
            or (self.before_checkpoint, self.after_checkpoint)
            not in {
                pair
                for values in REGISTERED_ADJACENT_PAIRS.values()
                for pair in values
            }
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
            or type(self.incremental_draws) is not int
            or self.incremental_draws
            != self.after_checkpoint - self.before_checkpoint
            or self.incremental_draws <= 0
            or type(self.raw_prefix_extension)
            is not RawPrefixExtensionProofV2
            or self.raw_prefix_extension.incremental_accepted_draws
            != self.incremental_draws
            or self.raw_prefix_extension.before_validation_draws
            != self.before_checkpoint
            or self.raw_prefix_extension.after_validation_draws
            != self.after_checkpoint
            or type(self.before_mass_intervals) is not tuple
            or type(self.after_mass_intervals) is not tuple
            or not self.before_mass_intervals
            or not self.after_mass_intervals
            or any(
                type(item) is not IdentityBoundMassIntervalV2
                for item in (
                    *self.before_mass_intervals,
                    *self.after_mass_intervals,
                )
            )
            or tuple(
                item.destination_id for item in self.before_mass_intervals
            )
            != tuple(
                sorted(
                    {
                        item.destination_id
                        for item in self.before_mass_intervals
                    }
                )
            )
            or tuple(
                item.destination_id for item in self.after_mass_intervals
            )
            != tuple(
                sorted(
                    {
                        item.destination_id
                        for item in self.after_mass_intervals
                    }
                )
            )
            or tuple(
                item.destination_id for item in self.before_mass_intervals
            )
            != tuple(
                item.destination_id for item in self.after_mass_intervals
            )
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "identity-bound local snapshot is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.identity_bound_local_snapshot.v2",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "before_execution_id": self.before_execution_id,
            "after_execution_id": self.after_execution_id,
            "before_model_id": self.before_model_id,
            "after_model_id": self.after_model_id,
            "before_audit_id": self.before_audit_id,
            "after_audit_id": self.after_audit_id,
            "threshold_profile_id": self.threshold_profile_id,
            "before_checkpoint": self.before_checkpoint,
            "after_checkpoint": self.after_checkpoint,
            "before_row_id": self.before_row_id,
            "after_row_id": self.after_row_id,
            "state_id": self.state_id,
            "action_id": self.action_id,
            "remaining_horizon": self.remaining_horizon,
            "before_reward_lower": _fdoc(self.before_reward_lower),
            "before_reward_upper": _fdoc(self.before_reward_upper),
            "after_reward_lower": _fdoc(self.after_reward_lower),
            "after_reward_upper": _fdoc(self.after_reward_upper),
            "before_mass_intervals": [
                item._document() for item in self.before_mass_intervals
            ],
            "after_mass_intervals": [
                item._document() for item in self.after_mass_intervals
            ],
            "raw_prefix_extension_proof_id": (
                self.raw_prefix_extension.proof_id
            ),
            "incremental_draws": self.incremental_draws,
            "portable_feature_key": self.portable_feature_key,
            "portable_fields_repeated": False,
        }

    @property
    def snapshot_id(self) -> str:
        return _content_id("local-snapshot", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "snapshot_id": self.snapshot_id}


@dataclass(frozen=True, slots=True)
class IndependentFixedPolicyMetricsV2:
    reward_lower: Fraction
    failure_upper: Fraction
    unrestricted_reward_upper: Fraction
    normalized_regret_upper: Fraction
    certificate_slack: Fraction

    def __post_init__(self) -> None:
        if (
            any(
                type(item) is not Fraction
                for item in (
                    self.reward_lower,
                    self.failure_upper,
                    self.unrestricted_reward_upper,
                    self.normalized_regret_upper,
                    self.certificate_slack,
                )
            )
            or self.reward_lower < 0
            or not 0 <= self.failure_upper <= 1
            or self.unrestricted_reward_upper < self.reward_lower
            or self.normalized_regret_upper < 0
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "independent fixed-policy metrics are inconsistent"
            )

    def _document(self) -> dict[str, Any]:
        return {
            "reward_lower": _fdoc(self.reward_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "unrestricted_reward_upper": _fdoc(
                self.unrestricted_reward_upper
            ),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "certificate_slack": _fdoc(self.certificate_slack),
        }


@dataclass(frozen=True, slots=True)
class VerifiedSourceLocalTrialV2:
    source_context_id: str
    portable_feature: PortableAcquisitionCoreFeatureV2
    local_snapshot: IdentityBoundLocalSnapshotV2
    before_metrics: IndependentFixedPolicyMetricsV2
    roll_forward_metrics: IndependentFixedPolicyMetricsV2
    slack_gain: Fraction
    gain_per_draw: Fraction
    independent_fraction_recurrence: bool = True
    proposal_only: bool = True

    def __post_init__(self) -> None:
        _cid(self.source_context_id, "trial context")
        if (
            type(self.portable_feature)
            is not PortableAcquisitionCoreFeatureV2
            or type(self.local_snapshot)
            is not IdentityBoundLocalSnapshotV2
            or type(self.before_metrics)
            is not IndependentFixedPolicyMetricsV2
            or type(self.roll_forward_metrics)
            is not IndependentFixedPolicyMetricsV2
            or self.local_snapshot.source_context_id
            != self.source_context_id
            or self.local_snapshot.portable_feature_key
            != self.portable_feature.feature_key
            or type(self.slack_gain) is not Fraction
            or self.slack_gain
            != max(
                Fraction(0),
                self.roll_forward_metrics.certificate_slack
                - self.before_metrics.certificate_slack,
            )
            or type(self.gain_per_draw) is not Fraction
            or self.gain_per_draw
            != self.slack_gain / self.local_snapshot.incremental_draws
            or self.independent_fraction_recurrence is not True
            or self.proposal_only is not True
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "source-local trial is not mechanically derived"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_source_local_trial.v2",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "portable_feature_key": self.portable_feature.feature_key,
            "local_snapshot_id": self.local_snapshot.snapshot_id,
            "before_metrics": self.before_metrics._document(),
            "roll_forward_metrics": (
                self.roll_forward_metrics._document()
            ),
            "slack_gain": _fdoc(self.slack_gain),
            "gain_per_draw": _fdoc(self.gain_per_draw),
            "independent_fraction_recurrence": True,
            "production_scoring_helper_used": False,
            "caller_supplied_score": False,
            "proposal_only": True,
        }

    @property
    def trial_id(self) -> str:
        return _content_id("source-trial", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "portable_feature": self.portable_feature.to_document(),
            "local_snapshot": self.local_snapshot.to_document(),
            "trial_id": self.trial_id,
        }


@dataclass(frozen=True, slots=True)
class VerifiedAdjacentCheckpointPairV2:
    source_context_id: str
    source_context_key: str
    before_checkpoint: int
    after_checkpoint: int
    before_execution_id: str
    after_execution_id: str
    before_model_id: str
    after_model_id: str
    before_audit_id: str
    after_audit_id: str
    trial_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, field in (
            (self.source_context_id, "pair context"),
            (self.before_execution_id, "pair before execution"),
            (self.after_execution_id, "pair after execution"),
            (self.before_model_id, "pair before model"),
            (self.after_model_id, "pair after model"),
            (self.before_audit_id, "pair before audit"),
            (self.after_audit_id, "pair after audit"),
        ):
            _cid(value, field)
        if (
            self.source_context_key not in REGISTERED_ADJACENT_PAIRS
            or (self.before_checkpoint, self.after_checkpoint)
            not in REGISTERED_ADJACENT_PAIRS[self.source_context_key]
            or not _ids(self.trial_ids, "pair trials")
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "adjacent checkpoint pair is unregistered or empty"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_adjacent_checkpoint_pair.v2",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "source_context_key": self.source_context_key,
            "before_checkpoint": self.before_checkpoint,
            "after_checkpoint": self.after_checkpoint,
            "before_execution_id": self.before_execution_id,
            "after_execution_id": self.after_execution_id,
            "before_model_id": self.before_model_id,
            "after_model_id": self.after_model_id,
            "before_audit_id": self.before_audit_id,
            "after_audit_id": self.after_audit_id,
            "trial_ids": list(self.trial_ids),
        }

    @property
    def pair_id(self) -> str:
        return _content_id("checkpoint-pair", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "pair_id": self.pair_id}


class FeatureConsensusDispositionV2(str, Enum):
    APPLIED = "APPLIED"
    INSUFFICIENT_CONTEXTS = "INSUFFICIENT_CONTEXTS"
    DEGENERATE_CONTEXT_RANKING = "DEGENERATE_CONTEXT_RANKING"
    NONPOSITIVE_SOURCE_GAIN = "NONPOSITIVE_SOURCE_GAIN"
    HIGH_DISAGREEMENT = "HIGH_DISAGREEMENT"


@dataclass(frozen=True, slots=True)
class SourceContextFeatureAggregateV2:
    source_context_id: str
    feature_key: str
    trial_ids: tuple[str, ...]
    mean_gain_per_draw: Fraction
    normalized_midrank: Fraction
    context_ranking_degenerate: bool

    def __post_init__(self) -> None:
        _cid(self.source_context_id, "aggregate context")
        _cid(self.feature_key, "aggregate feature")
        if (
            not _ids(self.trial_ids, "aggregate trials")
            or type(self.mean_gain_per_draw) is not Fraction
            or self.mean_gain_per_draw < 0
            or type(self.normalized_midrank) is not Fraction
            or not 0 <= self.normalized_midrank <= 1
            or type(self.context_ranking_degenerate) is not bool
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "source context-feature aggregate is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.source_context_feature_aggregate.v2",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "feature_key": self.feature_key,
            "trial_ids": list(self.trial_ids),
            "mean_gain_per_draw": _fdoc(self.mean_gain_per_draw),
            "normalized_midrank": _fdoc(self.normalized_midrank),
            "context_ranking_degenerate": (
                self.context_ranking_degenerate
            ),
        }

    @property
    def aggregate_id(self) -> str:
        return _content_id("context-feature-aggregate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "aggregate_id": self.aggregate_id}


@dataclass(frozen=True, slots=True)
class NonrectangularFeatureConsensusV2:
    feature_key: str
    source_context_ids: tuple[str, ...]
    aggregate_ids: tuple[str, ...]
    mean_gain_per_draw: Fraction
    mean_midrank: Fraction
    worst_midrank: Fraction
    disagreement: Fraction
    any_context_ranking_degenerate: bool
    disposition: FeatureConsensusDispositionV2
    multiplier: Fraction

    def __post_init__(self) -> None:
        _cid(self.feature_key, "consensus feature")
        contexts = _ids(self.source_context_ids, "consensus contexts")
        aggregates = _ids(self.aggregate_ids, "consensus aggregates")
        if (
            len(contexts) != len(aggregates)
            or not contexts
            or any(
                type(item) is not Fraction
                for item in (
                    self.mean_gain_per_draw,
                    self.mean_midrank,
                    self.worst_midrank,
                    self.disagreement,
                    self.multiplier,
                )
            )
            or self.mean_gain_per_draw < 0
            or not 0 <= self.worst_midrank <= self.mean_midrank <= 1
            or self.disagreement != self.mean_midrank - self.worst_midrank
            or type(self.any_context_ranking_degenerate) is not bool
            or type(self.disposition)
            is not FeatureConsensusDispositionV2
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "nonrectangular feature consensus is malformed"
            )
        expected_disposition = (
            FeatureConsensusDispositionV2.INSUFFICIENT_CONTEXTS
            if len(contexts) < MIN_SOURCE_CONTEXTS_PER_FEATURE
            else (
                FeatureConsensusDispositionV2
                .DEGENERATE_CONTEXT_RANKING
                if self.any_context_ranking_degenerate
                else (
                    FeatureConsensusDispositionV2
                    .NONPOSITIVE_SOURCE_GAIN
                    if self.mean_gain_per_draw <= 0
                    else (
                        FeatureConsensusDispositionV2
                        .HIGH_DISAGREEMENT
                        if self.disagreement
                        > MAX_MIDRANK_DISAGREEMENT
                        else FeatureConsensusDispositionV2.APPLIED
                    )
                )
            )
        )
        expected_multiplier = (
            MIN_PRIOR_MULTIPLIER
            + (
                MAX_PRIOR_MULTIPLIER - MIN_PRIOR_MULTIPLIER
            )
            * self.mean_midrank
            if expected_disposition
            is FeatureConsensusDispositionV2.APPLIED
            else NEUTRAL_PRIOR_MULTIPLIER
        )
        if (
            self.disposition is not expected_disposition
            or self.multiplier != expected_multiplier
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "consensus disposition/multiplier was not derived"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.nonrectangular_feature_consensus.v2",
            "schema_version": SCHEMA_VERSION,
            "feature_key": self.feature_key,
            "source_context_ids": list(self.source_context_ids),
            "aggregate_ids": list(self.aggregate_ids),
            "mean_gain_per_draw": _fdoc(self.mean_gain_per_draw),
            "mean_midrank": _fdoc(self.mean_midrank),
            "worst_midrank": _fdoc(self.worst_midrank),
            "disagreement": _fdoc(self.disagreement),
            "any_context_ranking_degenerate": (
                self.any_context_ranking_degenerate
            ),
            "disagreement_threshold": _fdoc(
                MAX_MIDRANK_DISAGREEMENT
            ),
            "disposition": self.disposition.value,
            "multiplier": _fdoc(self.multiplier),
            "missing_feature_behavior": "NEUTRAL_MULTIPLIER",
        }

    @property
    def consensus_id(self) -> str:
        return _content_id("feature-consensus", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "consensus_id": self.consensus_id}


@dataclass(frozen=True, slots=True)
class VerifiedSourceAcquisitionArchiveV2:
    source_campaign_id: str
    source_campaign_verification_id: str
    source_family_id: str
    source_training_split_id: str
    adjacent_pairs: tuple[VerifiedAdjacentCheckpointPairV2, ...]
    trials: tuple[VerifiedSourceLocalTrialV2, ...]
    context_feature_aggregates: tuple[
        SourceContextFeatureAggregateV2, ...
    ]
    consensus: tuple[NonrectangularFeatureConsensusV2, ...]
    source_campaign_same_implementation_verified: bool = True
    independent_fraction_recurrence_verified: bool = True
    independent_source_campaign_verifier_claimed: bool = False
    source_frozen: bool = True
    proposal_only: bool = True
    may_certify: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.source_campaign_id, "archive campaign"),
            (
                self.source_campaign_verification_id,
                "archive campaign verification",
            ),
            (self.source_family_id, "archive family"),
            (self.source_training_split_id, "archive split"),
        ):
            _cid(value, field)
        if (
            type(self.adjacent_pairs) is not tuple
            or len(self.adjacent_pairs) != 7
            or any(
                type(item) is not VerifiedAdjacentCheckpointPairV2
                for item in self.adjacent_pairs
            )
            or tuple(item.pair_id for item in self.adjacent_pairs)
            != tuple(sorted({item.pair_id for item in self.adjacent_pairs}))
            or {
                (
                    item.source_context_key,
                    item.before_checkpoint,
                    item.after_checkpoint,
                )
                for item in self.adjacent_pairs
            }
            != {
                (context, before, after)
                for context, pairs in REGISTERED_ADJACENT_PAIRS.items()
                for before, after in pairs
            }
            or type(self.trials) is not tuple
            or not self.trials
            or any(
                type(item) is not VerifiedSourceLocalTrialV2
                for item in self.trials
            )
            or tuple(item.trial_id for item in self.trials)
            != tuple(sorted({item.trial_id for item in self.trials}))
            or {
                trial_id
                for item in self.adjacent_pairs
                for trial_id in item.trial_ids
            }
            != {item.trial_id for item in self.trials}
            or type(self.context_feature_aggregates) is not tuple
            or any(
                type(item) is not SourceContextFeatureAggregateV2
                for item in self.context_feature_aggregates
            )
            or tuple(
                item.aggregate_id
                for item in self.context_feature_aggregates
            )
            != tuple(
                sorted(
                    {
                        item.aggregate_id
                        for item in self.context_feature_aggregates
                    }
                )
            )
            or type(self.consensus) is not tuple
            or any(
                type(item) is not NonrectangularFeatureConsensusV2
                for item in self.consensus
            )
            or tuple(item.consensus_id for item in self.consensus)
            != tuple(sorted({item.consensus_id for item in self.consensus}))
            or self.source_campaign_same_implementation_verified is not True
            or self.independent_fraction_recurrence_verified is not True
            or self.independent_source_campaign_verifier_claimed is not False
            or self.source_frozen is not True
            or self.proposal_only is not True
            or self.may_certify is not False
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "verified source archive is incomplete or overstated"
            )
        trial_by_id = {item.trial_id: item for item in self.trials}
        for pair in self.adjacent_pairs:
            for trial_id in pair.trial_ids:
                trial = trial_by_id[trial_id]
                snapshot = trial.local_snapshot
                if (
                    trial.source_context_id != pair.source_context_id
                    or snapshot.before_checkpoint != pair.before_checkpoint
                    or snapshot.after_checkpoint != pair.after_checkpoint
                    or snapshot.before_execution_id
                    != pair.before_execution_id
                    or snapshot.after_execution_id != pair.after_execution_id
                    or snapshot.before_model_id != pair.before_model_id
                    or snapshot.after_model_id != pair.after_model_id
                    or snapshot.before_audit_id != pair.before_audit_id
                    or snapshot.after_audit_id != pair.after_audit_id
                ):
                    raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                        "checkpoint pair contains a foreign source trial"
                    )
        aggregates, consensus = _derive_nonrectangular_consensus(self.trials)
        if (
            aggregates != self.context_feature_aggregates
            or consensus != self.consensus
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "archive consensus differs from trial-derived consensus"
            )

    def multiplier_for(self, feature_key: str) -> Fraction:
        _cid(feature_key, "target portable feature")
        item = {
            value.feature_key: value for value in self.consensus
        }.get(feature_key)
        return (
            NEUTRAL_PRIOR_MULTIPLIER
            if item is None
            else item.multiplier
        )

    def disposition_for(
        self,
        feature_key: str,
    ) -> FeatureConsensusDispositionV2 | None:
        _cid(feature_key, "target portable feature")
        item = {
            value.feature_key: value for value in self.consensus
        }.get(feature_key)
        return None if item is None else item.disposition

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_source_acquisition_archive.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "source_family_id": self.source_family_id,
            "source_training_split_id": self.source_training_split_id,
            "feature_schema_id": FEATURE_SCHEMA_ID,
            "adjacent_pair_ids": [
                item.pair_id for item in self.adjacent_pairs
            ],
            "trial_ids": [item.trial_id for item in self.trials],
            "context_feature_aggregate_ids": [
                item.aggregate_id
                for item in self.context_feature_aggregates
            ],
            "consensus_ids": [
                item.consensus_id for item in self.consensus
            ],
            "source_campaign_same_implementation_verified": True,
            "independent_fraction_recurrence_verified": True,
            "independent_source_campaign_verifier_claimed": False,
            "source_frozen": True,
            "proposal_only": True,
            "may_certify": False,
            "caller_supplied_gain_or_score": False,
            "raw_prefix_extensions_semantically_replayed": True,
            "nonrectangular_consensus": True,
            "observed_support_count_in_portable_feature": False,
            "promoted_mixed_epoch_source_excluded": True,
            "target_identity_fields_absent": True,
            "missing_or_abstained_multiplier": _fdoc(
                NEUTRAL_PRIOR_MULTIPLIER
            ),
        }

    @property
    def archive_id(self) -> str:
        return _content_id("archive", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "adjacent_pairs": [
                item.to_document() for item in self.adjacent_pairs
            ],
            "trials": [item.to_document() for item in self.trials],
            "context_feature_aggregates": [
                item.to_document()
                for item in self.context_feature_aggregates
            ],
            "consensus": [item.to_document() for item in self.consensus],
            "archive_id": self.archive_id,
        }


@dataclass(frozen=True, slots=True)
class _IndependentStateActionValue:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction


def _extreme_expectation(
    masses: Sequence[robust.IntervalDestinationMassV1],
    values: Mapping[str, Fraction],
    *,
    maximize: bool,
) -> Fraction:
    """Independent greedy optimizer for one interval simplex."""

    if {item.destination_id for item in masses} != set(values):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "independent recurrence destination registry changed"
        )
    allocation = {
        item.destination_id: item.lower for item in masses
    }
    residual = Fraction(1) - sum(allocation.values(), Fraction(0))
    ordered = sorted(
        masses,
        key=lambda item: (
            -values[item.destination_id]
            if maximize
            else values[item.destination_id],
            item.destination_id,
        ),
    )
    for item in ordered:
        if residual == 0:
            break
        increment = min(
            residual,
            item.upper - allocation[item.destination_id],
        )
        allocation[item.destination_id] += increment
        residual -= increment
    if residual != 0:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "independent recurrence found an infeasible interval simplex"
        )
    return sum(
        allocation[key] * value for key, value in values.items()
    )


def _row_value(
    row: robust.IntervalSimplexRowV1,
    *,
    destination_by_id: Mapping[str, robust.RegisteredDestinationV1],
    child_values: Mapping[str, _IndependentStateActionValue],
    threshold: robust.RobustThresholdProfileV1,
) -> _IndependentStateActionValue:
    risk_values: dict[str, Fraction] = {}
    reward_lower_values: dict[str, Fraction] = {}
    reward_upper_values: dict[str, Fraction] = {}
    for mass in row.masses:
        destination = destination_by_id.get(mass.destination_id)
        if destination is None:
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "row references an unknown destination"
            )
        active_child = (
            destination.category is robust.DestinationCategory.ACTIVE_STATE
            and row.remaining_horizon > 1
        )
        if active_child:
            assert destination.state_id is not None
            child = child_values.get(destination.state_id)
            if child is None:
                raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                    "independent recurrence lacks one child value"
                )
            risk_values[mass.destination_id] = child.failure_upper
            reward_lower_values[mass.destination_id] = child.reward_lower
            reward_upper_values[mass.destination_id] = child.reward_upper
        else:
            risk_values[mass.destination_id] = (
                Fraction(1)
                if destination.category
                in (
                    robust.DestinationCategory.FAILURE,
                    robust.DestinationCategory.OTHER,
                )
                else Fraction(0)
            )
            reward_lower_values[mass.destination_id] = Fraction(0)
            reward_upper_values[mass.destination_id] = (
                threshold.reward_ceiling
                if (
                    destination.category
                    is robust.DestinationCategory.OTHER
                    and row.remaining_horizon > 1
                )
                else Fraction(0)
            )
    lower = row.reward_lower + _extreme_expectation(
        row.masses,
        reward_lower_values,
        maximize=False,
    )
    upper = min(
        threshold.reward_ceiling,
        row.reward_upper
        + _extreme_expectation(
            row.masses,
            reward_upper_values,
            maximize=True,
        ),
    )
    failure = _extreme_expectation(
        row.masses,
        risk_values,
        maximize=True,
    )
    if lower > upper or upper > threshold.reward_ceiling:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "independent recurrence produced an invalid reward interval"
        )
    return _IndependentStateActionValue(lower, upper, failure)


def _model_registries(
    model: robust.PartialSupportIntervalModelV1,
    row_overrides: Mapping[
        tuple[str, int, str], robust.IntervalSimplexRowV1
    ] | None = None,
) -> tuple[
    dict[str, robust.StateActionCatalogueV1],
    dict[str, robust.RegisteredDestinationV1],
    dict[tuple[str, int, str], robust.IntervalSimplexRowV1],
]:
    catalogues = {item.state_id: item for item in model.catalogues}
    destinations = {item.destination_id: item for item in model.destinations}
    rows = {item.row_key: item for item in model.rows}
    for key, row in (row_overrides or {}).items():
        if key != row.row_key or key not in rows:
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "roll-forward row does not replace the same semantic key"
            )
        rows[key] = row
    return catalogues, destinations, rows


def _reachable_children(
    model: robust.PartialSupportIntervalModelV1,
    rows: Mapping[
        tuple[str, int, str], robust.IntervalSimplexRowV1
    ],
    destinations: Mapping[str, robust.RegisteredDestinationV1],
) -> tuple[str, ...]:
    root = next(
        item
        for item in model.catalogues
        if item.state_id == model.root_state_id
    )
    result: set[str] = set()
    for action in root.actions:
        row = rows[(model.root_state_id, 2, action.action_id)]
        for mass in row.masses:
            destination = destinations[mass.destination_id]
            if (
                mass.upper > 0
                and destination.category
                is robust.DestinationCategory.ACTIVE_STATE
            ):
                assert destination.state_id is not None
                result.add(destination.state_id)
    return tuple(sorted(result))


def _concretized_value(
    *,
    model: robust.PartialSupportIntervalModelV1,
    state_id: str,
    remaining_horizon: int,
    abstract_action_key: str,
    child_values: Mapping[str, _IndependentStateActionValue],
    catalogues: Mapping[str, robust.StateActionCatalogueV1],
    destinations: Mapping[str, robust.RegisteredDestinationV1],
    rows: Mapping[
        tuple[str, int, str], robust.IntervalSimplexRowV1
    ],
    threshold: robust.RobustThresholdProfileV1,
) -> _IndependentStateActionValue:
    cell = catalogues[state_id].state_coordinate_key
    entries = tuple(
        item
        for item in model.concretizer_entries
        if (
            item.state_coordinate_key == cell
            and item.state_id == state_id
            and item.abstract_action_key == abstract_action_key
        )
    )
    if len(entries) != 1:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "selected semantic action lacks one fixed concretizer"
        )
    values = tuple(
        _row_value(
            rows[(state_id, remaining_horizon, action_id)],
            destination_by_id=destinations,
            child_values=child_values,
            threshold=threshold,
        )
        for action_id in entries[0].ground_action_ids
    )
    denominator = len(values)
    return _IndependentStateActionValue(
        sum((item.reward_lower for item in values), Fraction(0))
        / denominator,
        sum((item.reward_upper for item in values), Fraction(0))
        / denominator,
        sum((item.failure_upper for item in values), Fraction(0))
        / denominator,
    )


def _unrestricted_ground_reward_upper(
    *,
    model: robust.PartialSupportIntervalModelV1,
    catalogues: Mapping[str, robust.StateActionCatalogueV1],
    destinations: Mapping[str, robust.RegisteredDestinationV1],
    rows: Mapping[
        tuple[str, int, str], robust.IntervalSimplexRowV1
    ],
    child_states: Sequence[str],
    threshold: robust.RobustThresholdProfileV1,
) -> Fraction:
    child_values: dict[str, _IndependentStateActionValue] = {}
    for state_id in child_states:
        candidates = tuple(
            _row_value(
                rows[(state_id, 1, action.action_id)],
                destination_by_id=destinations,
                child_values={},
                threshold=threshold,
            )
            for action in catalogues[state_id].actions
        )
        child_values[state_id] = min(
            candidates,
            key=lambda item: -item.reward_upper,
        )
    root_values = tuple(
        _row_value(
            rows[(model.root_state_id, 2, action.action_id)],
            destination_by_id=destinations,
            child_values=child_values,
            threshold=threshold,
        ).reward_upper
        for action in catalogues[model.root_state_id].actions
    )
    return max(root_values)


def independent_fixed_policy_metrics_v2(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    row_overrides: Mapping[
        tuple[str, int, str], robust.IntervalSimplexRowV1
    ] | None = None,
) -> IndependentFixedPolicyMetricsV2:
    """Recompute one quotient policy without production scoring helpers."""

    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
        or audit.model_id != model.model_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or threshold.context_id != model.context_id
        or any(
            item.scope is not robust.PolicyScope.QUOTIENT_CELL
            for item in audit.assignments
        )
    ):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "independent recurrence inputs are stale or non-quotient"
        )
    assignments = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if len(assignments) != len(audit.assignments):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source audit duplicates a policy assignment scope"
        )
    catalogues, destinations, rows = _model_registries(
        model,
        row_overrides,
    )
    child_states = _reachable_children(model, rows, destinations)
    child_values: dict[str, _IndependentStateActionValue] = {}
    expected: set[tuple[str, int]] = set()
    for state_id in child_states:
        cell = catalogues[state_id].state_coordinate_key
        key = (cell, 1)
        expected.add(key)
        action = assignments.get(key)
        if action is None:
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "source policy omits a reachable continuation cell"
            )
        child_values[state_id] = _concretized_value(
            model=model,
            state_id=state_id,
            remaining_horizon=1,
            abstract_action_key=action,
            child_values={},
            catalogues=catalogues,
            destinations=destinations,
            rows=rows,
            threshold=threshold,
        )
    root_cell = catalogues[
        model.root_state_id
    ].state_coordinate_key
    root_key = (root_cell, 2)
    expected.add(root_key)
    root_action = assignments.get(root_key)
    if root_action is None or set(assignments) != expected:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source policy domain changed under row roll-forward"
        )
    root = _concretized_value(
        model=model,
        state_id=model.root_state_id,
        remaining_horizon=2,
        abstract_action_key=root_action,
        child_values=child_values,
        catalogues=catalogues,
        destinations=destinations,
        rows=rows,
        threshold=threshold,
    )
    unrestricted = _unrestricted_ground_reward_upper(
        model=model,
        catalogues=catalogues,
        destinations=destinations,
        rows=rows,
        child_states=child_states,
        threshold=threshold,
    )
    regret = max(Fraction(0), unrestricted - root.reward_lower) / (
        threshold.reward_ceiling
    )
    slack = min(
        threshold.risk_tolerance - root.failure_upper,
        threshold.normalized_regret_tolerance - regret,
    )
    return IndependentFixedPolicyMetricsV2(
        root.reward_lower,
        root.failure_upper,
        unrestricted,
        regret,
        slack,
    )


def _verify_audit_arithmetic(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> IndependentFixedPolicyMetricsV2:
    metrics = independent_fixed_policy_metrics_v2(
        model=model,
        audit=audit,
        threshold=threshold,
    )
    if (
        metrics.reward_lower != audit.root_reward_lower
        or metrics.failure_upper != audit.root_failure_upper
        or metrics.unrestricted_reward_upper
        != audit.unrestricted_reward_upper
        or metrics.normalized_regret_upper
        != audit.normalized_regret_upper
    ):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source audit fails the independent exact recurrence"
        )
    return metrics


def _structurally_compatible_models(
    before: robust.PartialSupportIntervalModelV1,
    after: robust.PartialSupportIntervalModelV1,
) -> None:
    if (
        before.context_id != after.context_id
        or before.root_state_id != after.root_state_id
        or before.catalogues != after.catalogues
        or before.destinations != after.destinations
        or before.concretizer_entries != after.concretizer_entries
        or {item.row_key for item in before.rows}
        != {item.row_key for item in after.rows}
        or {
            item.row_key: tuple(
                mass.destination_id for mass in item.masses
            )
            for item in before.rows
        }
        != {
            item.row_key: tuple(
                mass.destination_id for mass in item.masses
            )
            for item in after.rows
        }
    ):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "adjacent checkpoint models changed structural semantics"
        )


def _physical_row_for_planner_row(
    execution: campaign_v1.CheckpointExecutionV1,
    planner_row_id: str,
) -> graph_acquisition.GraphPartialSupportRowV1:
    projection = next(
        (
            item
            for item in execution.bridge.row_projections
            if item.planner_row.row_id == planner_row_id
        ),
        None,
    )
    if projection is None:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "planner row lacks a physical source-row projection"
        )
    physical = next(
        (
            item
            for item in execution.closure.all_rows
            if item.partial_row_id == projection.partial_row_id
        ),
        None,
    )
    if (
        type(physical) is not graph_acquisition.GraphPartialSupportRowV1
        or physical.confidence_authority.authority_id
        != projection.confidence_authority_id
        or physical.support_epoch.support_epoch_id
        != projection.support_epoch_id
    ):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source-row projection is stale relative to raw evidence"
        )
    return physical


def _raw_prefix_extension(
    before: graph_acquisition.GraphPartialSupportRowV1,
    after: graph_acquisition.GraphPartialSupportRowV1,
) -> RawPrefixExtensionProofV2:
    before_ids = before.current_validation_observation_ids
    after_ids = after.current_validation_observation_ids
    if (
        before.binding != after.binding
        or before.support_epoch.support_epoch_id
        != after.support_epoch.support_epoch_id
        or before.initial_discovery_observation_ids
        != after.initial_discovery_observation_ids
        or before.prior_validation_observation_ids
        != after.prior_validation_observation_ids
        or len(after_ids) <= len(before_ids)
        or after_ids[: len(before_ids)] != before_ids
        or before.counters.support_epoch_index != 1
        or after.counters.support_epoch_index != 1
    ):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source validation rows are not one exact epoch-1 raw prefix"
        )
    suffix = after_ids[len(before_ids) :]
    incremental_random_words = (
        after.counters.current_validation_random_word_calls
        - before.counters.current_validation_random_word_calls
    )
    incremental_rejections = (
        after.counters.current_validation_rejections
        - before.counters.current_validation_rejections
    )
    return RawPrefixExtensionProofV2(
        before.binding.row_id,
        before.support_epoch.support_epoch_id,
        before.partial_row_id,
        after.partial_row_id,
        before.physical_evidence_id,
        after.physical_evidence_id,
        _ordered_id_digest(
            "acfqp:v072-source-discovery-prefix:v1",
            before.initial_discovery_observation_ids,
        ),
        _ordered_id_digest(
            "acfqp:v072-source-validation-before:v1",
            before_ids,
        ),
        _ordered_id_digest(
            "acfqp:v072-source-validation-after:v1",
            after_ids,
        ),
        _ordered_id_digest(
            "acfqp:v072-source-validation-suffix:v1",
            suffix,
        ),
        len(before_ids),
        len(after_ids),
        len(suffix),
        incremental_random_words,
        incremental_rejections,
    )


def _portable_feature(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    row: robust.IntervalSimplexRowV1,
) -> PortableAcquisitionCoreFeatureV2:
    provenance = {
        item.row_id: item for item in audit.selected_row_provenance
    }.get(row.row_id)
    if provenance is None:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source frontier row lacks selected-policy provenance"
        )
    catalogues = {item.state_id: item for item in model.catalogues}
    catalogue = catalogues[row.state_id]
    assignment = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    action_key = assignment.get(
        (provenance.policy_scope_key, row.remaining_horizon)
    )
    if action_key is None:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "frontier row is not bound to the frozen semantic action"
        )
    support_sizes = {
        len(item.ground_action_ids)
        for item in model.concretizer_entries
        if (
            item.state_id == row.state_id
            and item.abstract_action_key == action_key
        )
    }
    if len(support_sizes) != 1:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "frontier row has no unique concretizer support size"
        )
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    categories = tuple(
        sorted(
            {
                destination_by_id[item.destination_id].category.value
                for item in row.masses
                if item.destination_id != row.other_destination_id
            }
        )
    )
    return PortableAcquisitionCoreFeatureV2(
        "ROOT" if row.remaining_horizon == 2 else "CONTINUATION",
        provenance.category.value,
        _bin_count(len(catalogue.actions)),
        _bin_count(next(iter(support_sizes))),
        categories,
    )


def _mass_intervals(
    model: robust.PartialSupportIntervalModelV1,
    row: robust.IntervalSimplexRowV1,
) -> tuple[IdentityBoundMassIntervalV2, ...]:
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    return tuple(
        IdentityBoundMassIntervalV2(
            item.destination_id,
            destination_by_id[item.destination_id].category,
            item.lower,
            item.upper,
        )
        for item in row.masses
    )


def _derive_pair(
    *,
    source_context_id: str,
    source_context_key: str,
    before: campaign_v1.CheckpointExecutionV1,
    after: campaign_v1.CheckpointExecutionV1,
) -> tuple[
    VerifiedAdjacentCheckpointPairV2,
    tuple[VerifiedSourceLocalTrialV2, ...],
]:
    if (
        type(before) is not campaign_v1.CheckpointExecutionV1
        or type(after) is not campaign_v1.CheckpointExecutionV1
        or (before.checkpoint, after.checkpoint)
        not in REGISTERED_ADJACENT_PAIRS[source_context_key]
        or not before.quotient_considered
        or not after.quotient_considered
        or type(before.quotient_base_audit) is not robust.RobustPlanAuditV1
        or type(after.quotient_base_audit) is not robust.RobustPlanAuditV1
        or before.quotient_base_audit.certified
        or before.quotient_base_audit.failed_frontier is None
        or before.threshold != after.threshold
    ):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source adjacent pair is missing its failed-to-next chronology"
        )
    before_model = before.bridge.quotient_model
    after_model = after.bridge.quotient_model
    before_audit = before.quotient_base_audit
    after_audit = after.quotient_base_audit
    threshold = before.threshold
    _structurally_compatible_models(before_model, after_model)
    before_metrics = _verify_audit_arithmetic(
        before_model,
        before_audit,
        threshold,
    )
    _verify_audit_arithmetic(after_model, after_audit, threshold)
    before_by_id = {item.row_id: item for item in before_model.rows}
    after_by_key = {item.row_key: item for item in after_model.rows}
    frontier_ids = before_audit.failed_frontier.other_positive_row_ids
    if not frontier_ids:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source failed frontier has no acquisition-relevant row"
        )
    trials: list[VerifiedSourceLocalTrialV2] = []
    for row_id in frontier_ids:
        row = before_by_id.get(row_id)
        if row is None:
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "source frontier references an absent row"
            )
        later = after_by_key[row.row_key]
        before_physical = _physical_row_for_planner_row(
            before,
            row.row_id,
        )
        after_physical = _physical_row_for_planner_row(
            after,
            later.row_id,
        )
        prefix_extension = _raw_prefix_extension(
            before_physical,
            after_physical,
        )
        feature = _portable_feature(
            model=before_model,
            audit=before_audit,
            row=row,
        )
        snapshot = IdentityBoundLocalSnapshotV2(
            source_context_id,
            before.execution_id,
            after.execution_id,
            before_model.model_id,
            after_model.model_id,
            before_audit.audit_id,
            after_audit.audit_id,
            threshold.threshold_profile_id,
            before.checkpoint,
            after.checkpoint,
            row.row_id,
            later.row_id,
            row.state_id,
            row.action_id,
            row.remaining_horizon,
            row.reward_lower,
            row.reward_upper,
            later.reward_lower,
            later.reward_upper,
            _mass_intervals(before_model, row),
            _mass_intervals(after_model, later),
            prefix_extension,
            prefix_extension.incremental_accepted_draws,
            feature.feature_key,
        )
        roll_forward = independent_fixed_policy_metrics_v2(
            model=before_model,
            audit=before_audit,
            threshold=threshold,
            row_overrides={row.row_key: later},
        )
        gain = max(
            Fraction(0),
            roll_forward.certificate_slack
            - before_metrics.certificate_slack,
        )
        trials.append(
            VerifiedSourceLocalTrialV2(
                source_context_id,
                feature,
                snapshot,
                before_metrics,
                roll_forward,
                gain,
                gain / snapshot.incremental_draws,
            )
        )
    trial_tuple = tuple(sorted(trials, key=lambda item: item.trial_id))
    pair = VerifiedAdjacentCheckpointPairV2(
        source_context_id,
        source_context_key,
        before.checkpoint,
        after.checkpoint,
        before.execution_id,
        after.execution_id,
        before_model.model_id,
        after_model.model_id,
        before_audit.audit_id,
        after_audit.audit_id,
        tuple(item.trial_id for item in trial_tuple),
    )
    return pair, trial_tuple


def _derive_nonrectangular_consensus(
    trials: tuple[VerifiedSourceLocalTrialV2, ...],
) -> tuple[
    tuple[SourceContextFeatureAggregateV2, ...],
    tuple[NonrectangularFeatureConsensusV2, ...],
]:
    grouped: dict[
        tuple[str, str], list[VerifiedSourceLocalTrialV2]
    ] = {}
    for trial in trials:
        grouped.setdefault(
            (
                trial.source_context_id,
                trial.portable_feature.feature_key,
            ),
            [],
        ).append(trial)
    means = {
        key: sum(
            (item.gain_per_draw for item in values),
            Fraction(0),
        )
        / len(values)
        for key, values in grouped.items()
    }
    by_context: dict[str, list[tuple[str, Fraction]]] = {}
    for (context_id, feature_key), mean in means.items():
        by_context.setdefault(context_id, []).append((feature_key, mean))
    context_ranking_degenerate = {
        context_id: (
            len(entries) < 2
            or len({mean for _, mean in entries}) < 2
        )
        for context_id, entries in by_context.items()
    }
    midranks: dict[tuple[str, str], Fraction] = {}
    for context_id, entries in by_context.items():
        ordered = sorted(entries, key=lambda item: (item[1], item[0]))
        denominator = len(ordered) - 1
        cursor = 0
        while cursor < len(ordered):
            end = cursor + 1
            while (
                end < len(ordered)
                and ordered[end][1] == ordered[cursor][1]
            ):
                end += 1
            rank = (
                Fraction(1, 2)
                if denominator == 0
                else Fraction(cursor + end - 1, 2 * denominator)
            )
            for feature_key, _ in ordered[cursor:end]:
                midranks[(context_id, feature_key)] = rank
            cursor = end
    aggregates = tuple(
        sorted(
            (
                SourceContextFeatureAggregateV2(
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
                    means[(context_id, feature_key)],
                    midranks[(context_id, feature_key)],
                    context_ranking_degenerate[context_id],
                )
                for context_id, feature_key in sorted(grouped)
            ),
            key=lambda item: item.aggregate_id,
        )
    )
    by_feature: dict[
        str, list[SourceContextFeatureAggregateV2]
    ] = {}
    for item in aggregates:
        by_feature.setdefault(item.feature_key, []).append(item)
    consensus: list[NonrectangularFeatureConsensusV2] = []
    for feature_key, values in by_feature.items():
        ordered = sorted(values, key=lambda item: item.source_context_id)
        ranks = [item.normalized_midrank for item in ordered]
        mean_rank = sum(ranks, Fraction(0)) / len(ranks)
        worst_rank = min(ranks)
        disagreement = mean_rank - worst_rank
        any_degenerate = any(
            item.context_ranking_degenerate for item in ordered
        )
        mean_gain = sum(
            (item.mean_gain_per_draw for item in ordered),
            Fraction(0),
        ) / len(ordered)
        disposition = (
            FeatureConsensusDispositionV2.INSUFFICIENT_CONTEXTS
            if len(ordered) < MIN_SOURCE_CONTEXTS_PER_FEATURE
            else (
                FeatureConsensusDispositionV2
                .DEGENERATE_CONTEXT_RANKING
                if any_degenerate
                else (
                    FeatureConsensusDispositionV2
                    .NONPOSITIVE_SOURCE_GAIN
                    if mean_gain <= 0
                    else (
                        FeatureConsensusDispositionV2
                        .HIGH_DISAGREEMENT
                        if disagreement > MAX_MIDRANK_DISAGREEMENT
                        else FeatureConsensusDispositionV2.APPLIED
                    )
                )
            )
        )
        multiplier = (
            MIN_PRIOR_MULTIPLIER
            + (
                MAX_PRIOR_MULTIPLIER - MIN_PRIOR_MULTIPLIER
            )
            * mean_rank
            if disposition is FeatureConsensusDispositionV2.APPLIED
            else NEUTRAL_PRIOR_MULTIPLIER
        )
        consensus.append(
            NonrectangularFeatureConsensusV2(
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


def freeze_verified_source_acquisition_archive_v2(
    *,
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: (
        campaign_v1.ObservationSupportCampaignVerificationV1
    ),
) -> VerifiedSourceAcquisitionArchiveV2:
    """Freeze the seven registered source transitions and derived prior."""

    if (
        type(source_campaign)
        is not campaign_v1.ObservationSupportCampaignV1
        or type(source_verification)
        is not campaign_v1.ObservationSupportCampaignVerificationV1
        or source_verification.campaign_id != source_campaign.campaign_id
        or source_verification.replayed_campaign_id
        != source_campaign.campaign_id
        or source_verification.valid is not True
        or source_verification.same_implementation_full_replay is not True
        or source_verification.role_manifest.campaign_id
        != source_campaign.campaign_id
    ):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source archive requires the matching full V0-068 verification"
        )
    results = {
        item.context.context_key: item
        for item in source_campaign.context_results
    }
    if tuple(results) != campaign_v1.REGISTERED_CONTEXT_ORDER:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "source campaign context chronology changed"
        )
    pair_results: list[VerifiedAdjacentCheckpointPairV2] = []
    trial_results: list[VerifiedSourceLocalTrialV2] = []
    for context_key in campaign_v1.REGISTERED_CONTEXT_ORDER:
        result = results[context_key]
        by_checkpoint = {
            item.checkpoint: item for item in result.executions
        }
        expected_checkpoints = {
            checkpoint
            for pair in REGISTERED_ADJACENT_PAIRS[context_key]
            for checkpoint in pair
        }
        if not expected_checkpoints.issubset(by_checkpoint):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "source campaign omits a registered checkpoint"
            )
        for before_checkpoint, after_checkpoint in (
            REGISTERED_ADJACENT_PAIRS[context_key]
        ):
            pair, trials = _derive_pair(
                source_context_id=result.context.context_id,
                source_context_key=context_key,
                before=by_checkpoint[before_checkpoint],
                after=by_checkpoint[after_checkpoint],
            )
            pair_results.append(pair)
            trial_results.extend(trials)
    pairs = tuple(sorted(pair_results, key=lambda item: item.pair_id))
    trials = tuple(sorted(trial_results, key=lambda item: item.trial_id))
    replayed_source_rows = set(source_verification.replayed_row_ids)
    required_prefix_rows = {
        row_id
        for trial in trials
        for row_id in (
            trial.local_snapshot.raw_prefix_extension.before_partial_row_id,
            trial.local_snapshot.raw_prefix_extension.after_partial_row_id,
        )
    }
    if not required_prefix_rows.issubset(replayed_source_rows):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "raw-prefix source rows were not semantically replayed"
        )
    aggregates, consensus = _derive_nonrectangular_consensus(trials)
    context_ids = tuple(
        item.context.context_id
        for item in source_campaign.context_results
    )
    source_family_id = _content_id(
        "source-family",
        {
            "schema": "acfqp.v0068_source_family.v2",
            "campaign_id": source_campaign.campaign_id,
            "registered_context_ids": list(context_ids),
        },
    )
    source_training_split_id = _content_id(
        "source-training-split",
        {
            "schema": "acfqp.v0068_source_training_split.v2",
            "source_family_id": source_family_id,
            "context_checkpoint_pairs": [
                {
                    "context_key": context,
                    "pairs": [list(pair) for pair in pairs_for_context],
                }
                for context, pairs_for_context in (
                    REGISTERED_ADJACENT_PAIRS.items()
                )
            ],
        },
    )
    return VerifiedSourceAcquisitionArchiveV2(
        source_campaign.campaign_id,
        source_verification.verification_id,
        source_family_id,
        source_training_split_id,
        pairs,
        trials,
        aggregates,
        consensus,
    )


@dataclass(frozen=True, slots=True)
class VerifiedSourceAcquisitionArchiveVerificationV2:
    archive_id: str
    replayed_archive_id: str
    source_campaign_id: str
    source_campaign_verification_id: str
    registered_adjacent_pair_count: int
    trial_count: int
    feature_count: int
    same_implementation_archive_replay: bool = True
    independent_fraction_recurrence_verified: bool = True
    independent_source_campaign_verifier_claimed: bool = False
    valid: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.archive_id, "verified archive"),
            (self.replayed_archive_id, "replayed archive"),
            (self.source_campaign_id, "verified source campaign"),
            (
                self.source_campaign_verification_id,
                "verified source campaign verification",
            ),
        ):
            _cid(value, field)
        if (
            self.archive_id != self.replayed_archive_id
            or self.registered_adjacent_pair_count != 7
            or type(self.trial_count) is not int
            or self.trial_count <= 0
            or type(self.feature_count) is not int
            or self.feature_count <= 0
            or self.same_implementation_archive_replay is not True
            or self.independent_fraction_recurrence_verified is not True
            or self.independent_source_campaign_verifier_claimed is not False
            or self.valid is not True
        ):
            raise VerifiedSourceAcquisitionArchiveInvariantViolation(
                "source archive verification is incomplete or overstated"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.verified_source_acquisition_archive_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "archive_id": self.archive_id,
            "replayed_archive_id": self.replayed_archive_id,
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "registered_adjacent_pair_count": (
                self.registered_adjacent_pair_count
            ),
            "trial_count": self.trial_count,
            "feature_count": self.feature_count,
            "same_implementation_archive_replay": True,
            "independent_fraction_recurrence_verified": True,
            "independent_source_campaign_verifier_claimed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("archive-verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_verified_source_acquisition_archive_v2(
    *,
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: (
        campaign_v1.ObservationSupportCampaignVerificationV1
    ),
    claimed: VerifiedSourceAcquisitionArchiveV2,
) -> VerifiedSourceAcquisitionArchiveVerificationV2:
    """Rebuild the archive and replay every independent source recurrence."""

    if type(claimed) is not VerifiedSourceAcquisitionArchiveV2:
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "archive verifier requires the concrete V2 artifact"
        )
    replayed = freeze_verified_source_acquisition_archive_v2(
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    if (
        replayed != claimed
        or replayed.archive_id != claimed.archive_id
        or canonical_json_bytes(replayed.to_document())
        != canonical_json_bytes(claimed.to_document())
    ):
        raise VerifiedSourceAcquisitionArchiveInvariantViolation(
            "claimed source archive differs from complete replay"
        )
    return VerifiedSourceAcquisitionArchiveVerificationV2(
        claimed.archive_id,
        replayed.archive_id,
        claimed.source_campaign_id,
        claimed.source_campaign_verification_id,
        len(claimed.adjacent_pairs),
        len(claimed.trials),
        len(claimed.consensus),
    )


__all__ = [
    "FEATURE_SCHEMA_ID",
    "FeatureConsensusDispositionV2",
    "IdentityBoundLocalSnapshotV2",
    "IdentityBoundMassIntervalV2",
    "IndependentFixedPolicyMetricsV2",
    "MAX_MIDRANK_DISAGREEMENT",
    "MIN_SOURCE_CONTEXTS_PER_FEATURE",
    "NEUTRAL_PRIOR_MULTIPLIER",
    "NonrectangularFeatureConsensusV2",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PortableAcquisitionCoreFeatureV2",
    "RawPrefixExtensionProofV2",
    "REGISTERED_ADJACENT_PAIRS",
    "SCHEMA_VERSION",
    "SourceContextFeatureAggregateV2",
    "VerifiedAdjacentCheckpointPairV2",
    "VerifiedSourceAcquisitionArchiveInvariantViolation",
    "VerifiedSourceAcquisitionArchiveV2",
    "VerifiedSourceAcquisitionArchiveVerificationV2",
    "VerifiedSourceLocalTrialV2",
    "freeze_verified_source_acquisition_archive_v2",
    "independent_fixed_policy_metrics_v2",
    "verify_verified_source_acquisition_archive_v2",
]
