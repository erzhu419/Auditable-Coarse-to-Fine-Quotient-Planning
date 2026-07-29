"""Independent, archive-bound portable-feature consensus authority.

The sole public construction input is a verified source-archive component.
Context-feature means, normalized midranks, dispositions, and multipliers are
replayed internally from the component's immutable trials.  No caller may
supply a gain, rank, disposition, or multiplier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import verified_source_acquisition_archive_v2 as archive_v2
from acfqp import v072_verified_source_archive_component_v1 as source_component


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_portable_feature_consensus_authority_v1"
DOMAIN_TAG = "acfqp:v072-portable-feature-consensus-authority:v1"


class V072PortableFeatureConsensusAuthorityInvariantViolation(ValueError):
    """The verified archive and independently replayed consensus diverge."""


def _content_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        DOMAIN_TAG.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072PortableFeatureConsensusAuthorityInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _replay_nonrectangular_consensus(
    trials: tuple[archive_v2.VerifiedSourceLocalTrialV2, ...],
) -> tuple[
    tuple[archive_v2.SourceContextFeatureAggregateV2, ...],
    tuple[archive_v2.NonrectangularFeatureConsensusV2, ...],
]:
    if (
        type(trials) is not tuple
        or not trials
        or any(
            type(item) is not archive_v2.VerifiedSourceLocalTrialV2
            for item in trials
        )
    ):
        raise V072PortableFeatureConsensusAuthorityInvariantViolation(
            "consensus replay requires exact immutable source trials"
        )

    grouped: dict[
        tuple[str, str],
        list[archive_v2.VerifiedSourceLocalTrialV2],
    ] = {}
    for trial in trials:
        key = (
            _cid(trial.source_context_id, "trial source context"),
            _cid(trial.portable_feature.feature_key, "portable feature"),
        )
        if type(trial.gain_per_draw) is not Fraction:
            raise V072PortableFeatureConsensusAuthorityInvariantViolation(
                "source gain-per-draw must remain exact"
            )
        grouped.setdefault(key, []).append(trial)

    mean_by_key = {
        key: sum(
            (item.gain_per_draw for item in values),
            Fraction(0),
        )
        / len(values)
        for key, values in grouped.items()
    }
    features_by_context: dict[str, list[tuple[str, Fraction]]] = {}
    for (context_id, feature_key), mean in mean_by_key.items():
        features_by_context.setdefault(context_id, []).append(
            (feature_key, mean)
        )
    degenerate_by_context = {
        context_id: (
            len(entries) < 2
            or len({mean for _, mean in entries}) < 2
        )
        for context_id, entries in features_by_context.items()
    }

    midrank_by_key: dict[tuple[str, str], Fraction] = {}
    for context_id, entries in features_by_context.items():
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
            normalized_midrank = (
                Fraction(1, 2)
                if denominator == 0
                else Fraction(cursor + end - 1, 2 * denominator)
            )
            for feature_key, _ in ordered[cursor:end]:
                midrank_by_key[
                    (context_id, feature_key)
                ] = normalized_midrank
            cursor = end

    aggregates = tuple(
        sorted(
            (
                archive_v2.SourceContextFeatureAggregateV2(
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
                    midrank_by_key[(context_id, feature_key)],
                    degenerate_by_context[context_id],
                )
                for context_id, feature_key in sorted(grouped)
            ),
            key=lambda item: item.aggregate_id,
        )
    )

    aggregates_by_feature: dict[
        str,
        list[archive_v2.SourceContextFeatureAggregateV2],
    ] = {}
    for aggregate in aggregates:
        aggregates_by_feature.setdefault(
            aggregate.feature_key,
            [],
        ).append(aggregate)

    consensus_items: list[
        archive_v2.NonrectangularFeatureConsensusV2
    ] = []
    for feature_key, values in aggregates_by_feature.items():
        ordered = sorted(values, key=lambda item: item.source_context_id)
        ranks = [item.normalized_midrank for item in ordered]
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
            archive_v2.FeatureConsensusDispositionV2.INSUFFICIENT_CONTEXTS
            if len(ordered) < archive_v2.MIN_SOURCE_CONTEXTS_PER_FEATURE
            else (
                archive_v2.FeatureConsensusDispositionV2
                .DEGENERATE_CONTEXT_RANKING
                if any_degenerate
                else (
                    archive_v2.FeatureConsensusDispositionV2
                    .NONPOSITIVE_SOURCE_GAIN
                    if mean_gain <= 0
                    else (
                        archive_v2.FeatureConsensusDispositionV2
                        .HIGH_DISAGREEMENT
                        if (
                            disagreement
                            > archive_v2.MAX_MIDRANK_DISAGREEMENT
                        )
                        else archive_v2.FeatureConsensusDispositionV2.APPLIED
                    )
                )
            )
        )
        multiplier = (
            archive_v2.MIN_PRIOR_MULTIPLIER
            + (
                archive_v2.MAX_PRIOR_MULTIPLIER
                - archive_v2.MIN_PRIOR_MULTIPLIER
            )
            * mean_rank
            if disposition
            is archive_v2.FeatureConsensusDispositionV2.APPLIED
            else archive_v2.NEUTRAL_PRIOR_MULTIPLIER
        )
        consensus_items.append(
            archive_v2.NonrectangularFeatureConsensusV2(
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
        sorted(consensus_items, key=lambda item: item.consensus_id)
    )


@dataclass(frozen=True, slots=True)
class V072PortableFeatureConsensusAuthorityV1:
    """Consensus replay whose constructor accepts no score-like inputs."""

    source_archive_component: (
        source_component.V072VerifiedSourceArchiveComponentV1
    )
    context_feature_aggregates: tuple[
        archive_v2.SourceContextFeatureAggregateV2, ...
    ] = field(init=False)
    consensus: tuple[
        archive_v2.NonrectangularFeatureConsensusV2, ...
    ] = field(init=False)
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.source_archive_component)
            is not source_component.V072VerifiedSourceArchiveComponentV1
        ):
            raise V072PortableFeatureConsensusAuthorityInvariantViolation(
                "consensus authority requires the exact source component"
            )
        source = self.source_archive_component.archive
        aggregates, consensus = _replay_nonrectangular_consensus(
            source.trials
        )
        if (
            aggregates != source.context_feature_aggregates
            or consensus != source.consensus
        ):
            raise V072PortableFeatureConsensusAuthorityInvariantViolation(
                "archive aggregates or consensus differ from internal replay"
            )
        object.__setattr__(
            self,
            "context_feature_aggregates",
            aggregates,
        )
        object.__setattr__(self, "consensus", consensus)
        object.__setattr__(
            self,
            "_authority_id",
            _content_id(self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        source = self.source_archive_component
        return {
            "schema": (
                "acfqp.v072_portable_feature_consensus_authority.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_archive_component_id": source.component_id,
            "archive_id": source.archive.archive_id,
            "production_verification_id": (
                source.production_verification.verification_id
            ),
            "independent_archive_transform_attestation_id": (
                source.independent_attestation.verification_id
            ),
            "feature_schema_id": archive_v2.FEATURE_SCHEMA_ID,
            "aggregate_ids": [
                item.aggregate_id
                for item in self.context_feature_aggregates
            ],
            "consensus_ids": [
                item.consensus_id for item in self.consensus
            ],
            "nonrectangular_consensus": True,
            "internally_replayed_from_verified_trials": True,
            "caller_supplied_gain": False,
            "caller_supplied_rank": False,
            "caller_supplied_disposition": False,
            "caller_supplied_multiplier": False,
            "missing_feature_multiplier": {
                "numerator": (
                    archive_v2.NEUTRAL_PRIOR_MULTIPLIER.numerator
                ),
                "denominator": (
                    archive_v2.NEUTRAL_PRIOR_MULTIPLIER.denominator
                ),
            },
            "proposal_only": True,
            "may_certify": False,
            "target_observation_input_accepted": False,
            "environment_law_queries": 0,
            "outcome_enumeration_calls": 0,
            "new_draw_calls": 0,
        }

    @property
    def authority_id(self) -> str:
        return self._authority_id

    def multiplier_for(self, feature_key: str) -> Fraction:
        canonical = _cid(feature_key, "target portable feature")
        item = {
            value.feature_key: value for value in self.consensus
        }.get(canonical)
        return (
            archive_v2.NEUTRAL_PRIOR_MULTIPLIER
            if item is None
            else item.multiplier
        )

    def disposition_for(
        self,
        feature_key: str,
    ) -> archive_v2.FeatureConsensusDispositionV2 | None:
        canonical = _cid(feature_key, "target portable feature")
        item = {
            value.feature_key: value for value in self.consensus
        }.get(canonical)
        return None if item is None else item.disposition

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context_feature_aggregates": [
                item.to_document()
                for item in self.context_feature_aggregates
            ],
            "consensus": [
                item.to_document() for item in self.consensus
            ],
            "authority_id": self.authority_id,
        }


def replay_portable_feature_consensus_authority_v1(
    source_archive_component: (
        source_component.V072VerifiedSourceArchiveComponentV1
    ),
) -> V072PortableFeatureConsensusAuthorityV1:
    """Replay consensus from the verified source component only."""

    return V072PortableFeatureConsensusAuthorityV1(
        source_archive_component
    )


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V072PortableFeatureConsensusAuthorityInvariantViolation",
    "V072PortableFeatureConsensusAuthorityV1",
    "replay_portable_feature_consensus_authority_v1",
]
