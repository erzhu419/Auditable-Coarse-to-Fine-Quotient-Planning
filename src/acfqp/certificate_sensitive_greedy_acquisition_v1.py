"""Certificate-sensitive, source-frozen greedy acquisition mechanics.

V0-071 is deliberately retrospective and non-confirmatory.  A V0-070
selected-policy registry is reconstructed into context-free feature
descriptors.  Target-local *single-row* zero-OTHER counterfactuals are used
only to rank proposals by exact certificate-slack gain per registered draw.
They are never treated as observations, model epochs, audits, or
certificates.

Every selected proposal is frozen before any target acquisition.  Continuing
past that boundary requires a typed post-authorization target-evidence receipt
and its immutable materialized model.  A complete robust replan on that
materialized model is the sole certificate authority.  The implementation
contains only a deterministic synthetic exact-support materializer for the
positive mechanics fixture; real K6 therefore stops at AUTHORIZATION_READY
unless an independently implemented materializer is supplied in a later
contract.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

import acfqp.observation_support_joint_pair_recovery_v1 as joint
import acfqp.partial_support_robust_planner_v1 as robust
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.35.0"
PROFILE_KEY = "source_frozen_certificate_sensitive_greedy_acquisition_v0"

FEATURE_SCHEMA_ID = hashlib.sha256(
    b"acfqp:certificate-sensitive-portable-row-feature:v1\x00"
    b'{"ids_stripped":true,"selected_category":true,'
    b'"state_action_support_documents":true,"support_novel_other":true}'
).hexdigest()
SYNTHETIC_MATERIALIZER_ID = hashlib.sha256(
    b"acfqp:synthetic-exact-support-materializer:v1\x00"
    b'{"test_fixture_only":true}'
).hexdigest()

MAX_ELIGIBLE_ROWS = 64
MAX_ROUNDS = 2
MAX_SINGLE_ZERO_EVALUATIONS_PER_ROUND = 64
MAX_TOTAL_SINGLE_ZERO_EVALUATIONS = 128
MAX_AUTHORIZED_ROWS = 2
MAX_INCREMENTAL_DRAW_UPPER = 160_960
H1_ROW_DRAW_UPPER = 80_480
H2_ROW_DRAW_UPPER = 160_960
MIN_PRIOR_MULTIPLIER = Fraction(1, 2)
MAX_PRIOR_MULTIPLIER = Fraction(2)
MIN_SOURCE_CONTEXTS_PER_FEATURE = 2
MAX_SOURCE_MIDRANK_DISAGREEMENT = Fraction(1, 4)
MAX_PROCESS_WORKERS = 16

CERTIFICATE_AUTHORITY = "COMPLETE_ROBUST_REPLAN_ON_MATERIALIZED_TARGET_MODEL"
RETROSPECTIVE_SCOPE = (
    "RETROSPECTIVE_MECHANICS_ONLY_NOT_CONFIRMATORY_NOT_SAMPLE_EFFICIENCY"
)


class CertificateSensitiveGreedyInvariantViolation(ValueError):
    """An identity, authority, cap, or access-order invariant failed."""


class MatchedArm(str, Enum):
    SOURCE_CONSENSUS_PRIOR = "SOURCE_CONSENSUS_PRIOR"
    NO_PRIOR = "NO_PRIOR"
    OOD_ABSTENTION = "OOD_ABSTENTION"
    WRONG_CONSENSUS_PRIOR = "WRONG_CONSENSUS_PRIOR"


class PriorDisposition(str, Enum):
    APPLIED = "APPLIED"
    NO_PRIOR = "NO_PRIOR"
    OOD_ABSTAINED = "OOD_ABSTAINED"


class CandidateEvaluationStatus(str, Enum):
    EVALUATED = "EVALUATED"
    INFEASIBLE_SIMPLEX = "INFEASIBLE_SIMPLEX"


class GreedyAcquisitionOutcome(str, Enum):
    AUTHORIZATION_READY = "AUTHORIZATION_READY"
    SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_1 = (
        "SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_1"
    )
    SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_2 = (
        "SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_2"
    )
    FAILED_AFTER_TWO_ROUNDS = "FAILED_AFTER_TWO_ROUNDS"
    DRAW_CAP_EXHAUSTED = "DRAW_CAP_EXHAUSTED"
    NO_POSITIVE_GAIN = "NO_POSITIVE_GAIN"


DOMAIN_TAGS = {
    "caps": "acfqp:certificate-sensitive-caps:v1",
    "feature": "acfqp:portable-certificate-row-feature:v1",
    "vote": "acfqp:source-local-certificate-trial:v1",
    "consensus": "acfqp:source-feature-consensus:v1",
    "prior": "acfqp:source-frozen-certificate-prior:v1",
    "candidate": "acfqp:target-local-certificate-candidate:v1",
    "registry": "acfqp:fresh-target-local-candidate-registry:v1",
    "score": "acfqp:target-single-zero-ranking-score:v1",
    "access": "acfqp:certificate-acquisition-access:v1",
    "authorization": "acfqp:certificate-acquisition-authorization:v1",
    "prepared": "acfqp:certificate-acquisition-prepared-round:v1",
    "synthetic_evidence": "acfqp:synthetic-exact-support-evidence:v1",
    "receipt": "acfqp:postauthorization-target-evidence-receipt:v1",
    "certificate": "acfqp:materialized-model-robust-certificate:v1",
    "consumed": "acfqp:certificate-acquisition-consumed-round:v1",
    "schedule": "acfqp:certificate-acquisition-schedule:v1",
    "trace": "acfqp:certificate-acquisition-target-trace:v1",
    "run": "acfqp:certificate-sensitive-greedy-run:v1",
    "campaign": "acfqp:certificate-sensitive-matched-campaign:v1",
    "verification": "acfqp:certificate-sensitive-verification:v1",
    "k6": "acfqp:k6-certificate-sensitive-retrospective:v1",
}


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode() + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise CertificateSensitiveGreedyInvariantViolation(str(error)) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise CertificateSensitiveGreedyInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _ids(
    values: Any,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or values != tuple(sorted(set(values)))
        or (not allow_empty and not values)
    ):
        raise CertificateSensitiveGreedyInvariantViolation(
            f"{field} must be a canonical distinct ID tuple"
        )
    for value in values:
        _cid(value, field)
    return values


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise CertificateSensitiveGreedyInvariantViolation(
            "decision arithmetic must be exact Fraction"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _maybe(value: Fraction | None) -> dict[str, int] | None:
    return None if value is None else _fdoc(value)


def _json_value(value: Any) -> Any:
    if type(value) is tuple:
        return [_json_value(item) for item in value]
    if type(value) is list:
        return [_json_value(item) for item in value]
    if type(value) is dict:
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _workers(value: Any) -> int:
    if (
        type(value) is not int
        or isinstance(value, bool)
        or not 1 <= value <= MAX_PROCESS_WORKERS
    ):
        raise CertificateSensitiveGreedyInvariantViolation(
            "max_workers is outside the registered range"
        )
    return value


@dataclass(frozen=True, slots=True)
class CertificateSensitiveGreedyCapsV1:
    max_eligible_rows: int = MAX_ELIGIBLE_ROWS
    max_rounds: int = MAX_ROUNDS
    max_single_zero_evaluations_per_round: int = (
        MAX_SINGLE_ZERO_EVALUATIONS_PER_ROUND
    )
    max_total_single_zero_evaluations: int = (
        MAX_TOTAL_SINGLE_ZERO_EVALUATIONS
    )
    max_authorized_rows: int = MAX_AUTHORIZED_ROWS
    max_incremental_draw_upper: int = MAX_INCREMENTAL_DRAW_UPPER
    h1_row_draw_upper: int = H1_ROW_DRAW_UPPER
    h2_row_draw_upper: int = H2_ROW_DRAW_UPPER
    pair_subset_enumeration_cap: int = 0
    k3_subset_enumeration_cap: int = 0

    def __post_init__(self) -> None:
        if tuple(
            getattr(self, key) for key in self.__dataclass_fields__
        ) != (
            64, 2, 64, 128, 2, 160_960, 80_480, 160_960, 0, 0
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "registered finite cap profile changed"
            )

    @property
    def cap_profile_id(self) -> str:
        return _content_id(
            "caps",
            {
                "schema": "acfqp.certificate_sensitive_caps.v1",
                "contract_version": CONTRACT_VERSION,
                **{
                    key: getattr(self, key)
                    for key in self.__dataclass_fields__
                },
            },
        )


def registered_certificate_sensitive_caps_v1(
) -> CertificateSensitiveGreedyCapsV1:
    return CertificateSensitiveGreedyCapsV1()


@dataclass(frozen=True, slots=True)
class PortableCandidateFeatureV1:
    selected_row_category: str
    state_coordinate_document: tuple[tuple[str, Any], ...]
    action_coordinate_document: tuple[tuple[str, Any], ...]
    support_coordinate_document: tuple[tuple[str, Any], ...]
    support_count: int
    novel_count: int
    other_mass_upper: Fraction
    ids_stripped: bool = True

    def __post_init__(self) -> None:
        valid_categories = {item.value for item in robust.SelectedRowCategory}
        if (
            self.selected_row_category not in valid_categories
            or not self.state_coordinate_document
            or not self.action_coordinate_document
            or not self.support_coordinate_document
            or type(self.support_count) is not int
            or self.support_count < 0
            or type(self.novel_count) is not int
            or self.novel_count < 0
            or type(self.other_mass_upper) is not Fraction
            or not 0 <= self.other_mass_upper <= 1
            or self.ids_stripped is not True
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "portable candidate feature is malformed"
            )
        document = self._document()
        if any(
            isinstance(value, str)
            and len(value) == 64
            and all(char in "0123456789abcdef" for char in value)
            for value in _walk_values(document)
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "portable feature document leaked a content ID"
            )

    def _document(self) -> dict[str, Any]:
        return {
            "selected_row_category": self.selected_row_category,
            "state_coordinate_document": _json_value(
                dict(self.state_coordinate_document)
            ),
            "action_coordinate_document": _json_value(
                dict(self.action_coordinate_document)
            ),
            "support_coordinate_document": _json_value(
                dict(self.support_coordinate_document)
            ),
            "support_count": self.support_count,
            "novel_count": self.novel_count,
            "other_mass_upper": _fdoc(self.other_mass_upper),
            "ids_stripped": True,
        }

    @property
    def feature_key(self) -> str:
        return _content_id(
            "feature",
            {
                "schema": "acfqp.portable_candidate_feature.v1",
                "feature_schema_id": FEATURE_SCHEMA_ID,
                **self._document(),
            },
        )


def _walk_values(value: Any) -> Iterable[Any]:
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from _walk_values(getattr(value, field.name))
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


@dataclass(frozen=True, slots=True)
class SourceLocalTrialV1:
    source_context_id: str
    source_model_id: str
    source_audit_id: str
    raw_roll_forward_evidence_id: str
    feature_key: str
    source_gain_per_draw: Fraction

    def __post_init__(self) -> None:
        for value, field in (
            (self.source_context_id, "source context"),
            (self.source_model_id, "source model"),
            (self.source_audit_id, "source audit"),
            (
                self.raw_roll_forward_evidence_id,
                "source raw roll-forward evidence",
            ),
            (self.feature_key, "source portable feature"),
        ):
            _cid(value, field)
        if (
            type(self.source_gain_per_draw) is not Fraction
            or self.source_gain_per_draw < 0
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "source trial score must be a nonnegative exact Fraction"
            )

    @property
    def trial_id(self) -> str:
        return _content_id(
            "vote",
            {
                "schema": "acfqp.source_local_certificate_trial.v1",
                "source_context_id": self.source_context_id,
                "source_model_id": self.source_model_id,
                "source_audit_id": self.source_audit_id,
                "raw_roll_forward_evidence_id": (
                    self.raw_roll_forward_evidence_id
                ),
                "feature_key": self.feature_key,
                "source_gain_per_draw": _fdoc(
                    self.source_gain_per_draw
                ),
            },
        )


# Compatibility name retained for the focused contract API.
SourcePriorVoteV1 = SourceLocalTrialV1


@dataclass(frozen=True, slots=True)
class SourceFeatureConsensusV1:
    feature_key: str
    source_context_ids: tuple[str, ...]
    mean_gain_per_draw: Fraction
    mean_midrank: Fraction
    worst_midrank: Fraction
    disagreement: Fraction
    normalized_midrank: Fraction
    multiplier: Fraction

    def __post_init__(self) -> None:
        _cid(self.feature_key, "consensus feature")
        _ids(self.source_context_ids, "consensus source contexts")
        if (
            len(self.source_context_ids) < MIN_SOURCE_CONTEXTS_PER_FEATURE
            or any(
                type(item) is not Fraction
                for item in (
                    self.mean_gain_per_draw,
                    self.mean_midrank,
                    self.worst_midrank,
                    self.disagreement,
                    self.normalized_midrank,
                    self.multiplier,
                )
            )
            or self.mean_gain_per_draw < 0
            or not 0 <= self.mean_midrank <= 1
            or not 0 <= self.worst_midrank <= self.mean_midrank
            or self.disagreement < 0
            or self.disagreement > 1
            or self.disagreement != self.mean_midrank - self.worst_midrank
            or not 0 <= self.normalized_midrank <= 1
            or self.normalized_midrank != self.mean_midrank
            or self.multiplier
            != MIN_PRIOR_MULTIPLIER
            + (
                MAX_PRIOR_MULTIPLIER - MIN_PRIOR_MULTIPLIER
            )
            * self.normalized_midrank
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "source consensus/midrank/disagreement is inconsistent"
            )

    @property
    def consensus_id(self) -> str:
        return _content_id(
            "consensus",
            {
                "schema": "acfqp.source_feature_consensus.v1",
                "feature_key": self.feature_key,
                "source_context_ids": list(self.source_context_ids),
                "mean_gain_per_draw": _fdoc(self.mean_gain_per_draw),
                "mean_midrank": _fdoc(self.mean_midrank),
                "worst_midrank": _fdoc(self.worst_midrank),
                "disagreement": _fdoc(self.disagreement),
                "normalized_midrank": _fdoc(self.normalized_midrank),
                "multiplier": _fdoc(self.multiplier),
                "applicable": (
                    self.disagreement
                    <= MAX_SOURCE_MIDRANK_DISAGREEMENT
                ),
            },
        )


@dataclass(frozen=True, slots=True)
class SourceFrozenConsensusPriorV1:
    source_family_id: str
    source_training_split_id: str
    applicable_feature_schema_id: str
    trials: tuple[SourceLocalTrialV1, ...]
    consensus: tuple[SourceFeatureConsensusV1, ...]
    source_frozen: bool = True
    proposal_only: bool = True
    may_certify: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.source_family_id, "source family"),
            (self.source_training_split_id, "source split"),
            (
                self.applicable_feature_schema_id,
                "applicable feature schema",
            ),
        ):
            _cid(value, field)
        if (
            not self.trials
            or tuple(item.trial_id for item in self.trials)
            != tuple(sorted({item.trial_id for item in self.trials}))
            or tuple(item.consensus_id for item in self.consensus)
            != tuple(sorted({item.consensus_id for item in self.consensus}))
            or self.source_frozen is not True
            or self.proposal_only is not True
            or self.may_certify is not False
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "source prior archive is noncanonical or authoritative"
            )
        rebuilt = _derive_consensus(self.trials)
        if self.consensus != rebuilt:
            raise CertificateSensitiveGreedyInvariantViolation(
                "source consensus was not derived from source-local trials"
            )

    @property
    def source_context_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted({item.source_context_id for item in self.trials})
        )

    def multiplier_for(self, feature_key: str) -> Fraction | None:
        item = {
            value.feature_key: value for value in self.consensus
        }.get(feature_key)
        if (
            item is None
            or item.disagreement > MAX_SOURCE_MIDRANK_DISAGREEMENT
        ):
            return None
        return item.multiplier

    @property
    def prior_id(self) -> str:
        return _content_id(
            "prior",
            {
                "schema": "acfqp.source_frozen_consensus_prior.v1",
                "contract_version": CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "source_family_id": self.source_family_id,
                "source_training_split_id": self.source_training_split_id,
                "applicable_feature_schema_id": (
                    self.applicable_feature_schema_id
                ),
                "trial_ids": [item.trial_id for item in self.trials],
                "consensus_ids": [
                    item.consensus_id for item in self.consensus
                ],
                "source_frozen": True,
                "proposal_only": True,
                "may_certify": False,
                "target_identity_fields_absent": True,
            },
        )


def _derive_consensus(
    trials: tuple[SourceLocalTrialV1, ...],
) -> tuple[SourceFeatureConsensusV1, ...]:
    grouped: dict[str, list[SourceLocalTrialV1]] = {}
    for trial in trials:
        grouped.setdefault(trial.feature_key, []).append(trial)
    contexts = tuple(
        sorted({item.source_context_id for item in trials})
    )
    features = tuple(sorted(grouped))
    if len(contexts) < MIN_SOURCE_CONTEXTS_PER_FEATURE or not features:
        raise CertificateSensitiveGreedyInvariantViolation(
            "source archive lacks the registered rectangular support"
        )
    by_context: dict[
        str, dict[str, SourceLocalTrialV1]
    ] = {context: {} for context in contexts}
    for trial in trials:
        rows = by_context[trial.source_context_id]
        if trial.feature_key in rows:
            raise CertificateSensitiveGreedyInvariantViolation(
                "source context duplicated a portable feature"
            )
        rows[trial.feature_key] = trial
    if any(tuple(sorted(rows)) != features for rows in by_context.values()):
        raise CertificateSensitiveGreedyInvariantViolation(
            "every source context must cover the same portable features"
        )

    context_midranks: dict[tuple[str, str], Fraction] = {}
    for context, rows in by_context.items():
        values = sorted(
            (item.source_gain_per_draw, feature)
            for feature, item in rows.items()
        )
        denominator = len(values) - 1
        cursor = 0
        while cursor < len(values):
            end = cursor + 1
            while end < len(values) and values[end][0] == values[cursor][0]:
                end += 1
            midrank = (
                Fraction(1, 2)
                if denominator == 0
                else Fraction(cursor + end - 1, 2 * denominator)
            )
            for _, feature in values[cursor:end]:
                context_midranks[(context, feature)] = midrank
            cursor = end

    for feature, items in grouped.items():
        feature_contexts = tuple(
            sorted(item.source_context_id for item in items)
        )
        if (
            feature_contexts != contexts
            or len(feature_contexts) != len(set(feature_contexts))
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "each feature needs distinct source-local trials"
            )
    result = []
    for feature in features:
        items = grouped[feature]
        gains = [item.source_gain_per_draw for item in items]
        ranks = [
            context_midranks[(context, feature)]
            for context in contexts
        ]
        mean_gain = sum(gains, Fraction(0)) / len(gains)
        mean_midrank = sum(ranks, Fraction(0)) / len(ranks)
        worst_midrank = min(ranks)
        disagreement = mean_midrank - worst_midrank
        result.append(
            SourceFeatureConsensusV1(
                feature,
                contexts,
                mean_gain,
                mean_midrank,
                worst_midrank,
                disagreement,
                mean_midrank,
                MIN_PRIOR_MULTIPLIER
                + (MAX_PRIOR_MULTIPLIER - MIN_PRIOR_MULTIPLIER)
                * mean_midrank,
            )
        )
    return tuple(sorted(result, key=lambda item: item.consensus_id))


def freeze_source_consensus_prior_v1(
    *,
    source_family_id: str,
    source_training_split_id: str,
    applicable_feature_schema_id: str,
    votes: Iterable[SourceLocalTrialV1],
) -> SourceFrozenConsensusPriorV1:
    trials = tuple(sorted(votes, key=lambda item: item.trial_id))
    return SourceFrozenConsensusPriorV1(
        source_family_id,
        source_training_split_id,
        applicable_feature_schema_id,
        trials,
        _derive_consensus(trials),
    )


@dataclass(frozen=True, slots=True)
class TargetLocalAcquisitionCandidateV1:
    source_candidate: joint.JointPairCandidateRowV1
    feature: PortableCandidateFeatureV1
    incremental_draw_upper: int

    def __post_init__(self) -> None:
        expected = (
            H1_ROW_DRAW_UPPER
            if self.source_candidate.remaining_horizon == 1
            else H2_ROW_DRAW_UPPER
        )
        if (
            type(self.source_candidate)
            is not joint.JointPairCandidateRowV1
            or type(self.feature) is not PortableCandidateFeatureV1
            or self.incremental_draw_upper != expected
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "target candidate feature or cost is invalid"
            )

    @property
    def target_candidate_id(self) -> str:
        return _content_id(
            "candidate",
            {
                "schema": "acfqp.target_local_candidate.v1",
                "source_candidate_id": self.source_candidate.candidate_id,
                "planner_row_id": self.source_candidate.planner_row_id,
                "feature_key": self.feature.feature_key,
                "incremental_draw_upper": self.incremental_draw_upper,
                "target_probability_fields_used_for_prior": False,
            },
        )


@dataclass(frozen=True, slots=True)
class TargetLocalCandidateRegistryV1:
    source_registry: joint.JointPairCandidateRegistryV1
    current_model_id: str
    current_audit_id: str
    threshold_profile_id: str
    round_index: int
    excluded_source_candidate_ids: tuple[str, ...]
    candidates: tuple[TargetLocalAcquisitionCandidateV1, ...]
    feature_schema_id: str = FEATURE_SCHEMA_ID
    fresh_target_local_reconstruction: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.current_model_id, "registry current model"),
            (self.current_audit_id, "registry current audit"),
            (self.threshold_profile_id, "registry threshold"),
        ):
            _cid(value, field)
        _ids(
            self.excluded_source_candidate_ids,
            "excluded source candidates",
            allow_empty=True,
        )
        if (
            type(self.source_registry)
            is not joint.JointPairCandidateRegistryV1
            or self.round_index not in (1, 2)
            or not self.candidates
            or len(self.candidates) > MAX_ELIGIBLE_ROWS
            or tuple(item.target_candidate_id for item in self.candidates)
            != tuple(
                sorted({item.target_candidate_id for item in self.candidates})
            )
            or self.feature_schema_id != FEATURE_SCHEMA_ID
            or self.fresh_target_local_reconstruction is not True
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "fresh target registry is malformed"
            )
        expected = {
            item.candidate_id
            for item in self.source_registry.candidates
            if item.candidate_id not in self.excluded_source_candidate_ids
        }
        actual = {
            item.source_candidate.candidate_id for item in self.candidates
        }
        if actual != expected:
            raise CertificateSensitiveGreedyInvariantViolation(
                "target registry omitted or added a V0-070 candidate"
            )

    @property
    def registry_id(self) -> str:
        return _content_id(
            "registry",
            {
                "schema": "acfqp.target_local_candidate_registry.v1",
                "contract_version": CONTRACT_VERSION,
                "source_v0070_registry_id": self.source_registry.registry_id,
                "current_model_id": self.current_model_id,
                "current_audit_id": self.current_audit_id,
                "threshold_profile_id": self.threshold_profile_id,
                "round_index": self.round_index,
                "excluded_source_candidate_ids": list(
                    self.excluded_source_candidate_ids
                ),
                "candidate_ids": [
                    item.target_candidate_id for item in self.candidates
                ],
                "feature_schema_id": FEATURE_SCHEMA_ID,
                "fresh_target_local_reconstruction": True,
            },
        )


def _portable_feature(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    candidate: joint.JointPairCandidateRowV1,
) -> PortableCandidateFeatureV1:
    row = {item.row_id: item for item in model.rows}.get(
        candidate.planner_row_id
    )
    if row is None:
        raise CertificateSensitiveGreedyInvariantViolation(
            "candidate row is absent from current target model"
        )
    provenance = {
        item.row_id: item for item in audit.selected_row_provenance
    }.get(row.row_id)
    if provenance is None:
        raise CertificateSensitiveGreedyInvariantViolation(
            "candidate is not on the current selected-policy frontier"
        )
    catalogue = {
        item.state_id: item for item in model.catalogues
    }[row.state_id]
    action = {
        item.action_id: item for item in catalogue.actions
    }[row.action_id]
    concretizer_sizes = tuple(
        len(item.ground_action_ids)
        for item in model.concretizer_entries
        if (
            item.state_id == row.state_id
            and item.abstract_action_key == action.action_coordinate_key
        )
    )
    destination_category = {
        item.destination_id: item.category.value
        for item in model.destinations
    }
    support_shape = tuple(
        sorted(
            (
                destination_category[item.destination_id],
                item.lower.numerator,
                item.lower.denominator,
                item.upper.numerator,
                item.upper.denominator,
            )
            for item in row.masses
            if item.destination_id != row.other_destination_id
        )
    )
    return PortableCandidateFeatureV1(
        provenance.category.value,
        tuple(
            sorted(
                {
                    "stage_role": (
                        "root" if row.remaining_horizon == 2 else "continuation"
                    ),
                    "catalogue_action_count": len(catalogue.actions),
                    "state_coordinate_role": "portable_quotient_cell",
                }.items()
            )
        ),
        tuple(
            sorted(
                {
                    "action_coordinate_role": "portable_semantic_action",
                    "concretizer_support_count": (
                        sum(concretizer_sizes) if concretizer_sizes else 1
                    ),
                    "selected_policy_component": True,
                }.items()
            )
        ),
        tuple(
            sorted(
                {
                    "destination_category_interval_shape": support_shape,
                    "reward_lower": (
                        row.reward_lower.numerator,
                        row.reward_lower.denominator,
                    ),
                    "reward_upper": (
                        row.reward_upper.numerator,
                        row.reward_upper.denominator,
                    ),
                }.items()
            )
        ),
        sum(item.upper > 0 for item in row.masses)
        - int(row.other_mass.upper > 0),
        len(candidate.novel_outcome_ids),
        row.other_mass.upper,
    )


def freeze_target_local_candidate_registry_v1(
    source_registry: joint.JointPairCandidateRegistryV1,
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    round_index: int = 1,
    excluded_source_candidate_ids: tuple[str, ...] = (),
) -> TargetLocalCandidateRegistryV1:
    if (
        type(source_registry) is not joint.JointPairCandidateRegistryV1
        or type(model) is not robust.PartialSupportIntervalModelV1
        or type(audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or audit.model_id != model.model_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or audit.failed_frontier is None
    ):
        raise CertificateSensitiveGreedyInvariantViolation(
            "fresh registry parent chain is invalid"
        )
    if round_index == 1 and (
        source_registry.parent_model_id != model.model_id
        or source_registry.parent_audit_id != audit.audit_id
        or source_registry.threshold_profile_id
        != threshold.threshold_profile_id
    ):
        raise CertificateSensitiveGreedyInvariantViolation(
            "round-1 registry is stale relative to V0-070"
        )
    _ids(
        excluded_source_candidate_ids,
        "excluded candidates",
        allow_empty=True,
    )
    candidates = tuple(
        sorted(
            (
                TargetLocalAcquisitionCandidateV1(
                    item,
                    _portable_feature(
                        model=model,
                        audit=audit,
                        candidate=item,
                    ),
                    (
                        H1_ROW_DRAW_UPPER
                        if item.remaining_horizon == 1
                        else H2_ROW_DRAW_UPPER
                    ),
                )
                for item in source_registry.candidates
                if item.candidate_id not in excluded_source_candidate_ids
            ),
            key=lambda item: item.target_candidate_id,
        )
    )
    return TargetLocalCandidateRegistryV1(
        source_registry,
        model.model_id,
        audit.audit_id,
        threshold.threshold_profile_id,
        round_index,
        excluded_source_candidate_ids,
        candidates,
    )


@dataclass(frozen=True, slots=True)
class TargetLocalSingleZeroScoreV1:
    registry_id: str
    current_model_id: str
    current_audit_id: str
    round_index: int
    candidate_id: str
    source_candidate_id: str
    planner_row_id: str
    feature_key: str
    draw_upper: int
    prior_multiplier: Fraction
    status: CandidateEvaluationStatus
    counterfactual_model_id: str | None
    current_slack: Fraction
    counterfactual_slack: Fraction | None
    slack_gain: Fraction
    gain_per_draw: Fraction
    ranking_score: Fraction

    def __post_init__(self) -> None:
        for value, field in (
            (self.registry_id, "score registry"),
            (self.current_model_id, "score current model"),
            (self.current_audit_id, "score current audit"),
            (self.candidate_id, "score candidate"),
            (self.source_candidate_id, "score source candidate"),
            (self.planner_row_id, "score planner row"),
            (self.feature_key, "score feature"),
        ):
            _cid(value, field)
        if self.counterfactual_model_id is not None:
            _cid(self.counterfactual_model_id, "counterfactual model")
        exacts = (
            self.prior_multiplier,
            self.current_slack,
            self.slack_gain,
            self.gain_per_draw,
            self.ranking_score,
        )
        invalid = self.status is CandidateEvaluationStatus.INFEASIBLE_SIMPLEX
        if (
            self.round_index not in (1, 2)
            or self.draw_upper not in (H1_ROW_DRAW_UPPER, H2_ROW_DRAW_UPPER)
            or any(type(item) is not Fraction for item in exacts)
            or not MIN_PRIOR_MULTIPLIER
            <= self.prior_multiplier
            <= MAX_PRIOR_MULTIPLIER
            or (
                invalid
                and (
                    self.counterfactual_model_id is not None
                    or self.counterfactual_slack is not None
                    or any(
                        item != 0
                        for item in (
                            self.slack_gain,
                            self.gain_per_draw,
                            self.ranking_score,
                        )
                    )
                )
            )
            or (
                not invalid
                and (
                    type(self.counterfactual_slack) is not Fraction
                    or self.counterfactual_model_id is None
                    or self.slack_gain
                    != max(
                        Fraction(0),
                        self.counterfactual_slack - self.current_slack,
                    )
                    or self.gain_per_draw != self.slack_gain / self.draw_upper
                    or self.ranking_score
                    != self.gain_per_draw * self.prior_multiplier
                )
            )
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "single-zero proposal score is inconsistent"
            )

    @property
    def score_id(self) -> str:
        return _content_id(
            "score",
            {
                "schema": "acfqp.target_single_zero_score.v1",
                "registry_id": self.registry_id,
                "current_model_id": self.current_model_id,
                "current_audit_id": self.current_audit_id,
                "round_index": self.round_index,
                "candidate_id": self.candidate_id,
                "source_candidate_id": self.source_candidate_id,
                "planner_row_id": self.planner_row_id,
                "feature_key": self.feature_key,
                "draw_upper": self.draw_upper,
                "prior_multiplier": _fdoc(self.prior_multiplier),
                "status": self.status.value,
                "counterfactual_model_id": self.counterfactual_model_id,
                "current_slack": _fdoc(self.current_slack),
                "counterfactual_slack": _maybe(
                    self.counterfactual_slack
                ),
                "slack_gain": _fdoc(self.slack_gain),
                "gain_per_draw": _fdoc(self.gain_per_draw),
                "ranking_score": _fdoc(self.ranking_score),
                "ranking_only": True,
                "may_certify": False,
                "observer_calls": 0,
                "promotion_calls": 0,
                "full_policy_replans": 0,
                "exact_calls": 0,
            },
        )


@dataclass(frozen=True, slots=True)
class PreAuthorizationAccessDisciplineV1:
    round_index: int
    single_zero_model_evaluations: int
    observer_calls: int = 0
    promotion_calls: int = 0
    full_policy_replans: int = 0
    exact_evaluation_calls: int = 0
    pair_subset_enumerations: int = 0
    k3_subset_enumerations: int = 0

    def __post_init__(self) -> None:
        if (
            self.round_index not in (1, 2)
            or not 0
            <= self.single_zero_model_evaluations
            <= MAX_SINGLE_ZERO_EVALUATIONS_PER_ROUND
            or any(
                getattr(self, field) != 0
                for field in self.__dataclass_fields__
                if field
                not in ("round_index", "single_zero_model_evaluations")
            )
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "forbidden access occurred before authorization"
            )

    @property
    def access_id(self) -> str:
        return _content_id(
            "access",
            {
                "schema": "acfqp.preauthorization_access.v1",
                **{
                    key: getattr(self, key)
                    for key in self.__dataclass_fields__
                },
            },
        )


@dataclass(frozen=True, slots=True)
class GreedyRoundAuthorizationV1:
    registry_id: str
    current_model_id: str
    current_audit_id: str
    cap_profile_id: str
    access_id: str
    round_index: int
    score_ids: tuple[str, ...]
    selected_score_id: str
    selected_candidate_id: str
    selected_source_candidate_id: str
    selected_planner_row_id: str
    selected_draw_upper: int
    cumulative_draw_upper_after_selection: int
    authorization_sequence: int
    target_access_sequence_minimum: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.registry_id, "authorization registry"),
            (self.current_model_id, "authorization model"),
            (self.current_audit_id, "authorization audit"),
            (self.cap_profile_id, "authorization caps"),
            (self.access_id, "authorization access"),
            (self.selected_score_id, "selected score"),
            (self.selected_candidate_id, "selected candidate"),
            (
                self.selected_source_candidate_id,
                "selected source candidate",
            ),
            (self.selected_planner_row_id, "selected row"),
        ):
            _cid(value, field)
        _ids(self.score_ids, "authorization scores")
        if (
            self.round_index not in (1, 2)
            or self.selected_score_id not in self.score_ids
            or self.selected_draw_upper
            not in (H1_ROW_DRAW_UPPER, H2_ROW_DRAW_UPPER)
            or not 0
            < self.cumulative_draw_upper_after_selection
            <= MAX_INCREMENTAL_DRAW_UPPER
            or self.authorization_sequence != 2 * self.round_index - 1
            or self.target_access_sequence_minimum
            != self.authorization_sequence + 1
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "authorization identity/cap/order is invalid"
            )

    @property
    def authorization_id(self) -> str:
        return _content_id(
            "authorization",
            {
                "schema": "acfqp.greedy_round_authorization.v1",
                **{
                    key: (
                        list(getattr(self, key))
                        if key == "score_ids"
                        else getattr(self, key)
                    )
                    for key in self.__dataclass_fields__
                },
                "frozen_before_target_access": True,
            },
        )


@dataclass(frozen=True, slots=True)
class PreparedAcquisitionRoundV1:
    registry: TargetLocalCandidateRegistryV1
    scores: tuple[TargetLocalSingleZeroScoreV1, ...]
    access: PreAuthorizationAccessDisciplineV1
    authorization: GreedyRoundAuthorizationV1

    def __post_init__(self) -> None:
        score_by_id = {item.score_id: item for item in self.scores}
        selected = score_by_id.get(self.authorization.selected_score_id)
        cumulative_before = (
            self.authorization.cumulative_draw_upper_after_selection
            - self.authorization.selected_draw_upper
        )
        admissible = tuple(
            item
            for item in self.scores
            if (
                item.status is CandidateEvaluationStatus.EVALUATED
                and item.slack_gain > 0
                and item.draw_upper
                <= MAX_INCREMENTAL_DRAW_UPPER - cumulative_before
            )
        )
        if (
            tuple(item.score_id for item in self.scores)
            != tuple(sorted({item.score_id for item in self.scores}))
            or self.authorization.registry_id != self.registry.registry_id
            or self.authorization.score_ids
            != tuple(item.score_id for item in self.scores)
            or self.authorization.access_id != self.access.access_id
            or self.authorization.current_model_id
            != self.registry.current_model_id
            or self.authorization.current_audit_id
            != self.registry.current_audit_id
            or self.authorization.cap_profile_id
            != registered_certificate_sensitive_caps_v1().cap_profile_id
            or self.authorization.round_index != self.registry.round_index
            or self.access.round_index != self.registry.round_index
            or self.access.single_zero_model_evaluations != len(self.scores)
            or selected is None
            or not admissible
            or selected != min(admissible, key=_ranking_key)
            or self.authorization.selected_candidate_id
            != selected.candidate_id
            or self.authorization.selected_source_candidate_id
            != selected.source_candidate_id
            or self.authorization.selected_planner_row_id
            != selected.planner_row_id
            or self.authorization.selected_draw_upper != selected.draw_upper
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "prepared round does not bind its complete ordered decision"
            )

    @property
    def prepared_round_id(self) -> str:
        return _content_id(
            "prepared",
            {
                "schema": "acfqp.prepared_acquisition_round.v1",
                "registry_id": self.registry.registry_id,
                "score_ids": [item.score_id for item in self.scores],
                "access_id": self.access.access_id,
                "authorization_id": self.authorization.authorization_id,
                "target_access_performed": False,
                "certificate_emitted": False,
            },
        )


@dataclass(frozen=True, slots=True)
class PostAuthorizationTargetEvidenceReceiptV1:
    authorization_id: str
    parent_model_id: str
    selected_planner_row_id: str
    target_evidence_id: str
    materialized_model_id: str
    materializer_id: str
    charged_draws: int
    evidence_sequence: int
    synthetic_fixture_only: bool

    def __post_init__(self) -> None:
        for value, field in (
            (self.authorization_id, "receipt authorization"),
            (self.parent_model_id, "receipt parent model"),
            (self.selected_planner_row_id, "receipt selected row"),
            (self.target_evidence_id, "receipt target evidence"),
            (self.materialized_model_id, "receipt materialized model"),
            (self.materializer_id, "receipt materializer"),
        ):
            _cid(value, field)
        if (
            self.materializer_id != SYNTHETIC_MATERIALIZER_ID
            or self.charged_draws
            not in (H1_ROW_DRAW_UPPER, H2_ROW_DRAW_UPPER)
            or self.evidence_sequence not in (2, 4)
            or self.synthetic_fixture_only is not True
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "only the typed post-authorization synthetic fixture receipt exists"
            )

    @property
    def receipt_id(self) -> str:
        return _content_id(
            "receipt",
            {
                "schema": "acfqp.postauthorization_target_evidence_receipt.v1",
                **{
                    key: getattr(self, key)
                    for key in self.__dataclass_fields__
                },
                "ranking_counterfactual_reused_as_evidence": False,
            },
        )


@dataclass(frozen=True, slots=True)
class MaterializedModelRobustCertificateV1:
    receipt_id: str
    model_id: str
    audit_id: str
    threshold_profile_id: str
    assignment_ids: tuple[str, ...]
    root_reward_lower: Fraction
    root_failure_upper: Fraction
    normalized_regret_upper: Fraction
    authority: str = CERTIFICATE_AUTHORITY
    prior_certificate_calls: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.receipt_id, "certificate receipt"),
            (self.model_id, "certificate model"),
            (self.audit_id, "certificate audit"),
            (self.threshold_profile_id, "certificate threshold"),
        ):
            _cid(value, field)
        _ids(self.assignment_ids, "certificate assignments")
        if (
            any(
                type(item) is not Fraction
                for item in (
                    self.root_reward_lower,
                    self.root_failure_upper,
                    self.normalized_regret_upper,
                )
            )
            or self.authority != CERTIFICATE_AUTHORITY
            or self.prior_certificate_calls != 0
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "certificate lacks complete materialized-model audit authority"
            )

    @property
    def certificate_id(self) -> str:
        return _content_id(
            "certificate",
            {
                "schema": "acfqp.materialized_model_robust_certificate.v1",
                "receipt_id": self.receipt_id,
                "model_id": self.model_id,
                "audit_id": self.audit_id,
                "threshold_profile_id": self.threshold_profile_id,
                "assignment_ids": list(self.assignment_ids),
                "root_reward_lower": _fdoc(self.root_reward_lower),
                "root_failure_upper": _fdoc(self.root_failure_upper),
                "normalized_regret_upper": _fdoc(
                    self.normalized_regret_upper
                ),
                "authority": self.authority,
                "prior_certificate_calls": 0,
            },
        )


@dataclass(frozen=True, slots=True)
class ConsumedAcquisitionRoundV1:
    prepared: PreparedAcquisitionRoundV1
    receipt: PostAuthorizationTargetEvidenceReceiptV1
    materialized_model: robust.PartialSupportIntervalModelV1
    robust_audit: robust.RobustPlanAuditV1
    certificate: MaterializedModelRobustCertificateV1 | None

    def __post_init__(self) -> None:
        auth = self.prepared.authorization
        if (
            self.receipt.authorization_id != auth.authorization_id
            or self.receipt.parent_model_id != auth.current_model_id
            or self.receipt.selected_planner_row_id
            != auth.selected_planner_row_id
            or self.receipt.materialized_model_id
            != self.materialized_model.model_id
            or self.receipt.charged_draws != auth.selected_draw_upper
            or self.receipt.evidence_sequence
            < auth.target_access_sequence_minimum
            or self.robust_audit.model_id != self.materialized_model.model_id
            or self.robust_audit.threshold_profile_id
            != self.prepared.registry.threshold_profile_id
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "consumed round receipt/model/audit chain is invalid"
            )
        if self.robust_audit.certified is not (self.certificate is not None):
            raise CertificateSensitiveGreedyInvariantViolation(
                "certificate does not match complete robust replan"
            )
        if self.certificate is not None and (
            self.certificate.receipt_id != self.receipt.receipt_id
            or self.certificate.model_id != self.materialized_model.model_id
            or self.certificate.audit_id != self.robust_audit.audit_id
            or self.certificate.threshold_profile_id
            != self.robust_audit.threshold_profile_id
            or self.certificate.assignment_ids
            != tuple(
                sorted(
                    item.assignment_id
                    for item in self.robust_audit.assignments
                )
            )
            or self.certificate.root_reward_lower
            != self.robust_audit.root_reward_lower
            or self.certificate.root_failure_upper
            != self.robust_audit.root_failure_upper
            or self.certificate.normalized_regret_upper
            != self.robust_audit.normalized_regret_upper
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "materialized-model certificate was transplanted"
            )

    @property
    def consumed_round_id(self) -> str:
        return _content_id(
            "consumed",
            {
                "schema": "acfqp.consumed_acquisition_round.v1",
                "prepared_round_id": self.prepared.prepared_round_id,
                "receipt_id": self.receipt.receipt_id,
                "materialized_model_id": self.materialized_model.model_id,
                "robust_audit_id": self.robust_audit.audit_id,
                "certificate_id": (
                    None
                    if self.certificate is None
                    else self.certificate.certificate_id
                ),
            },
        )


@dataclass(frozen=True, slots=True)
class _ScoreTaskV1:
    model: robust.PartialSupportIntervalModelV1
    audit: robust.RobustPlanAuditV1
    threshold: robust.RobustThresholdProfileV1
    registry_id: str
    candidate: TargetLocalAcquisitionCandidateV1
    multiplier: Fraction
    round_index: int
    current_slack: Fraction


def _audit_slack(
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> Fraction:
    return min(
        threshold.risk_tolerance - audit.root_failure_upper,
        threshold.normalized_regret_tolerance
        - audit.normalized_regret_upper,
    )


def _score_one(task: _ScoreTaskV1) -> TargetLocalSingleZeroScoreV1:
    common = (
        task.registry_id,
        task.model.model_id,
        task.audit.audit_id,
        task.round_index,
        task.candidate.target_candidate_id,
        task.candidate.source_candidate.candidate_id,
        task.candidate.source_candidate.planner_row_id,
        task.candidate.feature.feature_key,
        task.candidate.incremental_draw_upper,
        task.multiplier,
    )
    try:
        counterfactual = joint._joint_zero_other_model(
            task.model,
            (task.candidate.source_candidate.planner_row_id,),
        )
        _, _, _, slack = joint._fixed_policy_metrics_operational(
            counterfactual,
            task.audit,
            task.threshold,
        )
    except robust.PartialSupportRobustPlannerInvariantViolation:
        return TargetLocalSingleZeroScoreV1(
            *common,
            CandidateEvaluationStatus.INFEASIBLE_SIMPLEX,
            None,
            task.current_slack,
            None,
            Fraction(0),
            Fraction(0),
            Fraction(0),
        )
    gain = max(Fraction(0), slack - task.current_slack)
    per_draw = gain / task.candidate.incremental_draw_upper
    return TargetLocalSingleZeroScoreV1(
        *common,
        CandidateEvaluationStatus.EVALUATED,
        counterfactual.model_id,
        task.current_slack,
        slack,
        gain,
        per_draw,
        per_draw * task.multiplier,
    )


def _score_all(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetLocalCandidateRegistryV1,
    multipliers: Mapping[str, Fraction],
    max_workers: int,
) -> tuple[TargetLocalSingleZeroScoreV1, ...]:
    tasks = tuple(
        _ScoreTaskV1(
            model,
            audit,
            threshold,
            registry.registry_id,
            candidate,
            multipliers.get(candidate.feature.feature_key, Fraction(1)),
            registry.round_index,
            _audit_slack(audit, threshold),
        )
        for candidate in registry.candidates
    )
    # This is pre-authorization trusted model-only preparation.  The frozen
    # access contract forbids launching a target-attributable worker before
    # the authorization artifact exists.  A larger scheduling hint therefore
    # preserves the same in-process exact replay.
    _workers(max_workers)
    scores = tuple(_score_one(item) for item in tasks)
    return tuple(sorted(scores, key=lambda item: item.score_id))


def _target_ids(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetLocalCandidateRegistryV1,
) -> set[str]:
    values = set()
    for value in _walk_values((model, audit, threshold, registry)):
        if (
            type(value) is str
            and len(value) == 64
            and all(
                character in "0123456789abcdef"
                for character in value
            )
        ):
            values.add(value)
    values.update(
        (
            model.model_id,
            audit.audit_id,
            threshold.threshold_profile_id,
            registry.registry_id,
            registry.source_registry.registry_id,
        )
    )
    return values


def _resolve_prior(
    *,
    arm: MatchedArm,
    prior: SourceFrozenConsensusPriorV1 | None,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetLocalCandidateRegistryV1,
) -> tuple[PriorDisposition, str | None, dict[str, Fraction]]:
    if arm is MatchedArm.NO_PRIOR:
        if prior is not None:
            raise CertificateSensitiveGreedyInvariantViolation(
                "no-prior arm received a prior"
            )
        return PriorDisposition.NO_PRIOR, None, {}
    if type(prior) is not SourceFrozenConsensusPriorV1:
        raise CertificateSensitiveGreedyInvariantViolation(
            "prior arm lacks a source-frozen archive"
        )
    source_ids = {
        prior.source_family_id,
        prior.source_training_split_id,
        *prior.source_context_ids,
        *(item.source_model_id for item in prior.trials),
        *(item.source_audit_id for item in prior.trials),
        *(item.raw_roll_forward_evidence_id for item in prior.trials),
        *(item.trial_id for item in prior.trials),
    }
    if source_ids & _target_ids(model, audit, threshold, registry):
        raise CertificateSensitiveGreedyInvariantViolation(
            "source archive leaked or aliased a target identity"
        )
    target_features = {
        item.feature.feature_key for item in registry.candidates
    }
    consensus = {
        item.feature_key: item for item in prior.consensus
    }
    ood = (
        prior.applicable_feature_schema_id != FEATURE_SCHEMA_ID
        or not target_features.issubset(consensus)
    )
    if arm is MatchedArm.OOD_ABSTENTION:
        if not ood:
            raise CertificateSensitiveGreedyInvariantViolation(
                "OOD arm received an in-domain archive"
            )
        return PriorDisposition.OOD_ABSTAINED, None, {}
    if ood:
        raise CertificateSensitiveGreedyInvariantViolation(
            "in-domain prior arm received OOD evidence"
        )
    values = {
        feature: (
            Fraction(1)
            if item.disagreement > MAX_SOURCE_MIDRANK_DISAGREEMENT
            else (
                MIN_PRIOR_MULTIPLIER
                + MAX_PRIOR_MULTIPLIER
                - item.multiplier
                if arm is MatchedArm.WRONG_CONSENSUS_PRIOR
                else item.multiplier
            )
        )
        for feature, item in consensus.items()
    }
    return PriorDisposition.APPLIED, prior.prior_id, values


def _ranking_key(
    score: TargetLocalSingleZeroScoreV1,
) -> tuple[Fraction, Fraction, int, str]:
    return (
        -score.ranking_score,
        -score.slack_gain,
        score.draw_upper,
        score.candidate_id,
    )


def prepare_certificate_sensitive_round_v1(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetLocalCandidateRegistryV1,
    arm: MatchedArm,
    prior: SourceFrozenConsensusPriorV1 | None,
    cumulative_draws: int,
    max_workers: int = 1,
) -> tuple[
    PreparedAcquisitionRoundV1 | None,
    PriorDisposition,
    str | None,
    GreedyAcquisitionOutcome | None,
]:
    max_workers = _workers(max_workers)
    if (
        registry.current_model_id != model.model_id
        or registry.current_audit_id != audit.audit_id
        or registry.threshold_profile_id != threshold.threshold_profile_id
        or audit.model_id != model.model_id
        or audit.certified
    ):
        raise CertificateSensitiveGreedyInvariantViolation(
            "prepare inputs are stale or already certified"
        )
    disposition, effective_id, multipliers = _resolve_prior(
        arm=arm,
        prior=prior,
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
    )
    remaining = MAX_INCREMENTAL_DRAW_UPPER - cumulative_draws
    if not any(
        item.incremental_draw_upper <= remaining
        for item in registry.candidates
    ):
        return (
            None,
            disposition,
            effective_id,
            GreedyAcquisitionOutcome.DRAW_CAP_EXHAUSTED,
        )
    scores = _score_all(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        multipliers=multipliers,
        max_workers=max_workers,
    )
    access = PreAuthorizationAccessDisciplineV1(
        registry.round_index,
        len(scores),
    )
    admissible = tuple(
        item
        for item in scores
        if (
            item.status is CandidateEvaluationStatus.EVALUATED
            and item.slack_gain > 0
            and item.draw_upper <= remaining
        )
    )
    if not admissible:
        return (
            None,
            disposition,
            effective_id,
            GreedyAcquisitionOutcome.NO_POSITIVE_GAIN,
        )
    selected = min(admissible, key=_ranking_key)
    authorization = GreedyRoundAuthorizationV1(
        registry.registry_id,
        model.model_id,
        audit.audit_id,
        registered_certificate_sensitive_caps_v1().cap_profile_id,
        access.access_id,
        registry.round_index,
        tuple(item.score_id for item in scores),
        selected.score_id,
        selected.candidate_id,
        selected.source_candidate_id,
        selected.planner_row_id,
        selected.draw_upper,
        cumulative_draws + selected.draw_upper,
        2 * registry.round_index - 1,
        2 * registry.round_index,
    )
    return (
        PreparedAcquisitionRoundV1(
            registry,
            scores,
            access,
            authorization,
        ),
        disposition,
        effective_id,
        None,
    )


def materialize_synthetic_exact_support_absence_v1(
    *,
    prepared: PreparedAcquisitionRoundV1,
    parent_model: robust.PartialSupportIntervalModelV1,
) -> tuple[
    PostAuthorizationTargetEvidenceReceiptV1,
    robust.PartialSupportIntervalModelV1,
]:
    """Deterministic exact-support materializer for the synthetic fixture only."""

    auth = prepared.authorization
    if parent_model.model_id != auth.current_model_id:
        raise CertificateSensitiveGreedyInvariantViolation(
            "synthetic materializer parent model is stale"
        )
    materialized = joint._joint_zero_other_model(
        parent_model,
        (auth.selected_planner_row_id,),
    )
    evidence_id = _content_id(
        "synthetic_evidence",
        {
            "schema": "acfqp.synthetic_exact_support_evidence.v1",
            "authorization_id": auth.authorization_id,
            "parent_model_id": parent_model.model_id,
            "selected_planner_row_id": auth.selected_planner_row_id,
            "materialized_model_id": materialized.model_id,
            "support_absence_exactly_observed": True,
            "synthetic_fixture_only": True,
        },
    )
    receipt = PostAuthorizationTargetEvidenceReceiptV1(
        auth.authorization_id,
        parent_model.model_id,
        auth.selected_planner_row_id,
        evidence_id,
        materialized.model_id,
        SYNTHETIC_MATERIALIZER_ID,
        auth.selected_draw_upper,
        auth.target_access_sequence_minimum,
        True,
    )
    return receipt, materialized


def consume_authorized_target_evidence_v1(
    *,
    prepared: PreparedAcquisitionRoundV1,
    parent_model: robust.PartialSupportIntervalModelV1,
    receipt: PostAuthorizationTargetEvidenceReceiptV1,
    materialized_model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
) -> ConsumedAcquisitionRoundV1:
    auth = prepared.authorization
    if (
        receipt.authorization_id != auth.authorization_id
        or parent_model.model_id != auth.current_model_id
        or receipt.parent_model_id != parent_model.model_id
        or receipt.materialized_model_id != materialized_model.model_id
        or receipt.materializer_id != SYNTHETIC_MATERIALIZER_ID
    ):
        raise CertificateSensitiveGreedyInvariantViolation(
            "target evidence is unauthorized or unsupported"
        )
    expected = joint._joint_zero_other_model(
        parent_model,
        (auth.selected_planner_row_id,),
    )
    if expected.model_id != materialized_model.model_id:
        raise CertificateSensitiveGreedyInvariantViolation(
            "synthetic target materialization changed more than authorized"
        )
    audit = robust.solve_quotient_robust_h2_v1(
        materialized_model,
        threshold,
    )
    certificate = (
        MaterializedModelRobustCertificateV1(
            receipt.receipt_id,
            materialized_model.model_id,
            audit.audit_id,
            threshold.threshold_profile_id,
            tuple(sorted(item.assignment_id for item in audit.assignments)),
            audit.root_reward_lower,
            audit.root_failure_upper,
            audit.normalized_regret_upper,
        )
        if audit.certified
        else None
    )
    return ConsumedAcquisitionRoundV1(
        prepared,
        receipt,
        materialized_model,
        audit,
        certificate,
    )


@dataclass(frozen=True, slots=True)
class CertificateSensitiveGreedyRunV1:
    arm: MatchedArm
    source_registry_id: str
    cap_profile_id: str
    requested_prior_id: str | None
    effective_prior_id: str | None
    prior_disposition: PriorDisposition
    base_model_id: str
    base_audit_id: str
    threshold_profile_id: str
    consumed_rounds: tuple[ConsumedAcquisitionRoundV1, ...]
    pending_prepared_round: PreparedAcquisitionRoundV1 | None
    outcome: GreedyAcquisitionOutcome
    cumulative_draw_upper: int
    effective_schedule_id: str
    target_trace_id: str
    pair_subset_enumerations: int = 0
    k3_subset_enumerations: int = 0
    retrospective_mechanics_only: bool = True
    confirmatory_result: bool = False
    k6_positive_result_preassumed: bool = False
    sample_efficiency_claimed: bool = False
    source_semantic_replay_claimed: bool = False
    fresh_round2_frontier_claimed: bool = False
    independent_verifier_claimed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.arm) is not MatchedArm
            or type(self.prior_disposition) is not PriorDisposition
            or type(self.outcome) is not GreedyAcquisitionOutcome
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "run enum fields are untyped"
            )
        for value, field in (
            (self.source_registry_id, "run source registry"),
            (self.cap_profile_id, "run caps"),
            (self.base_model_id, "run base model"),
            (self.base_audit_id, "run base audit"),
            (self.threshold_profile_id, "run threshold"),
            (self.effective_schedule_id, "run schedule"),
            (self.target_trace_id, "run target trace"),
        ):
            _cid(value, field)
        if self.requested_prior_id is not None:
            _cid(self.requested_prior_id, "requested prior")
        if self.effective_prior_id is not None:
            _cid(self.effective_prior_id, "effective prior")
        prior_shape = {
            PriorDisposition.APPLIED: (
                self.requested_prior_id is not None
                and self.effective_prior_id == self.requested_prior_id
            ),
            PriorDisposition.NO_PRIOR: (
                self.requested_prior_id is None
                and self.effective_prior_id is None
            ),
            PriorDisposition.OOD_ABSTAINED: (
                self.requested_prior_id is not None
                and self.effective_prior_id is None
            ),
        }[self.prior_disposition]
        if (
            not prior_shape
            or (self.arm is MatchedArm.NO_PRIOR)
            is not (self.prior_disposition is PriorDisposition.NO_PRIOR)
            or (self.arm is MatchedArm.OOD_ABSTENTION)
            is not (
                self.prior_disposition is PriorDisposition.OOD_ABSTAINED
            )
            or len(self.consumed_rounds) > 2
            or tuple(
                item.prepared.registry.round_index
                for item in self.consumed_rounds
            )
            != tuple(range(1, len(self.consumed_rounds) + 1))
            or self.cumulative_draw_upper
            != sum(
                item.receipt.charged_draws
                for item in self.consumed_rounds
            )
            or self.cumulative_draw_upper > MAX_INCREMENTAL_DRAW_UPPER
            or self.pair_subset_enumerations != 0
            or self.k3_subset_enumerations != 0
            or self.retrospective_mechanics_only is not True
            or self.confirmatory_result is not False
            or self.k6_positive_result_preassumed is not False
            or self.sample_efficiency_claimed is not False
            or self.source_semantic_replay_claimed is not False
            or self.fresh_round2_frontier_claimed is not False
            or self.independent_verifier_claimed is not False
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "run cap or claim boundary changed"
            )
        if self.outcome is GreedyAcquisitionOutcome.AUTHORIZATION_READY:
            if self.pending_prepared_round is None:
                raise CertificateSensitiveGreedyInvariantViolation(
                    "authorization-ready run lacks pending authorization"
                )
        elif self.pending_prepared_round is not None:
            raise CertificateSensitiveGreedyInvariantViolation(
                "terminal run retained a pending authorization"
            )
        certified = self.outcome in (
            GreedyAcquisitionOutcome
            .SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_1,
            GreedyAcquisitionOutcome
            .SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_2,
        )
        certificate = self.certificate
        if certified is not (certificate is not None):
            raise CertificateSensitiveGreedyInvariantViolation(
                "run outcome and complete robust certificate disagree"
            )
        prepared = tuple(
            item.prepared for item in self.consumed_rounds
        ) + (
            ()
            if self.pending_prepared_round is None
            else (self.pending_prepared_round,)
        )
        if (
            any(
                item.registry.source_registry.registry_id
                != self.source_registry_id
                for item in prepared
            )
            or self.effective_schedule_id != _schedule_id(prepared)
            or self.target_trace_id
            != _trace_id(self.base_model_id, self.consumed_rounds)
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "run schedule/trace or source registry was tampered"
            )

    @property
    def certificate(self) -> MaterializedModelRobustCertificateV1 | None:
        return (
            None
            if not self.consumed_rounds
            else self.consumed_rounds[-1].certificate
        )

    @property
    def selected_candidate_ids(self) -> tuple[str, ...]:
        items = [
            item.prepared.authorization.selected_candidate_id
            for item in self.consumed_rounds
        ]
        if self.pending_prepared_round is not None:
            items.append(
                self.pending_prepared_round.authorization.selected_candidate_id
            )
        return tuple(items)

    @property
    def run_id(self) -> str:
        return _content_id(
            "run",
            {
                "schema": "acfqp.certificate_sensitive_greedy_run.v1",
                "contract_version": CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "arm": self.arm.value,
                "source_registry_id": self.source_registry_id,
                "cap_profile_id": self.cap_profile_id,
                "requested_prior_id": self.requested_prior_id,
                "effective_prior_id": self.effective_prior_id,
                "prior_disposition": self.prior_disposition.value,
                "base_model_id": self.base_model_id,
                "base_audit_id": self.base_audit_id,
                "threshold_profile_id": self.threshold_profile_id,
                "consumed_round_ids": [
                    item.consumed_round_id
                    for item in self.consumed_rounds
                ],
                "pending_prepared_round_id": (
                    None
                    if self.pending_prepared_round is None
                    else self.pending_prepared_round.prepared_round_id
                ),
                "outcome": self.outcome.value,
                "cumulative_draw_upper": self.cumulative_draw_upper,
                "effective_schedule_id": self.effective_schedule_id,
                "target_trace_id": self.target_trace_id,
                "pair_subset_enumerations": 0,
                "k3_subset_enumerations": 0,
                "retrospective_scope": RETROSPECTIVE_SCOPE,
                "confirmatory_result": False,
                "k6_positive_result_preassumed": False,
                "sample_efficiency_claimed": False,
                "synthetic_fixture_only": self.synthetic_fixture_only,
                "source_semantic_replay_claimed": False,
                "fresh_round2_frontier_claimed": False,
                "independent_verifier_claimed": False,
            },
        )

    @property
    def synthetic_fixture_only(self) -> bool:
        return bool(self.consumed_rounds) and all(
            item.receipt.synthetic_fixture_only
            for item in self.consumed_rounds
        )


def _schedule_id(
    prepared: tuple[PreparedAcquisitionRoundV1, ...],
) -> str:
    return _content_id(
        "schedule",
        {
            "schema": "acfqp.certificate_acquisition_schedule.v1",
            "selections": [
                {
                    "candidate_id": item.authorization.selected_candidate_id,
                    "score_id": item.authorization.selected_score_id,
                    "draw_upper": item.authorization.selected_draw_upper,
                }
                for item in prepared
            ],
        },
    )


def _trace_id(
    base_model_id: str,
    consumed: tuple[ConsumedAcquisitionRoundV1, ...],
) -> str:
    return _content_id(
        "trace",
        {
            "schema": "acfqp.certificate_acquisition_target_trace.v1",
            "base_model_id": base_model_id,
            "receipt_ids": [item.receipt.receipt_id for item in consumed],
            "materialized_model_ids": [
                item.materialized_model.model_id for item in consumed
            ],
            "robust_audit_ids": [
                item.robust_audit.audit_id for item in consumed
            ],
            "certificate_id": (
                None
                if not consumed or consumed[-1].certificate is None
                else consumed[-1].certificate.certificate_id
            ),
            "prior_identity_included": False,
        },
    )


def run_certificate_sensitive_greedy_acquisition_v1(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetLocalCandidateRegistryV1,
    arm: MatchedArm,
    prior: SourceFrozenConsensusPriorV1 | None,
    synthetic_materializer: bool = False,
    max_workers: int = 1,
) -> CertificateSensitiveGreedyRunV1:
    """Run one authorization-only real path or the synthetic two-round path."""

    _workers(max_workers)
    current_model = model
    current_audit = audit
    current_registry = registry
    consumed: list[ConsumedAcquisitionRoundV1] = []
    prepared_all: list[PreparedAcquisitionRoundV1] = []
    excluded: list[str] = []
    cumulative = 0
    disposition: PriorDisposition | None = None
    effective_prior_id: str | None = None
    pending: PreparedAcquisitionRoundV1 | None = None
    outcome: GreedyAcquisitionOutcome | None = None

    for round_index in range(1, MAX_ROUNDS + 1):
        prepared, round_disposition, effective, stop = (
            prepare_certificate_sensitive_round_v1(
                model=current_model,
                audit=current_audit,
                threshold=threshold,
                registry=current_registry,
                arm=arm,
                prior=prior,
                cumulative_draws=cumulative,
                max_workers=max_workers,
            )
        )
        if disposition is None:
            disposition = round_disposition
            effective_prior_id = effective
        elif (disposition, effective_prior_id) != (
            round_disposition,
            effective,
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "prior disposition changed across rounds"
            )
        if stop is not None:
            outcome = stop
            break
        assert prepared is not None
        prepared_all.append(prepared)
        if not synthetic_materializer:
            pending = prepared
            outcome = GreedyAcquisitionOutcome.AUTHORIZATION_READY
            break
        receipt, materialized = (
            materialize_synthetic_exact_support_absence_v1(
                prepared=prepared,
                parent_model=current_model,
            )
        )
        consumed_round = consume_authorized_target_evidence_v1(
            prepared=prepared,
            parent_model=current_model,
            receipt=receipt,
            materialized_model=materialized,
            threshold=threshold,
        )
        consumed.append(consumed_round)
        cumulative += receipt.charged_draws
        excluded.append(
            prepared.authorization.selected_source_candidate_id
        )
        if consumed_round.certificate is not None:
            outcome = (
                GreedyAcquisitionOutcome
                .SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_1
                if round_index == 1
                else GreedyAcquisitionOutcome
                .SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_2
            )
            break
        current_model = materialized
        current_audit = consumed_round.robust_audit
        if round_index < MAX_ROUNDS:
            current_registry = freeze_target_local_candidate_registry_v1(
                registry.source_registry,
                model=current_model,
                audit=current_audit,
                threshold=threshold,
                round_index=round_index + 1,
                excluded_source_candidate_ids=tuple(sorted(excluded)),
            )
    if outcome is None:
        outcome = GreedyAcquisitionOutcome.FAILED_AFTER_TWO_ROUNDS
    assert disposition is not None
    return CertificateSensitiveGreedyRunV1(
        arm,
        registry.source_registry.registry_id,
        registered_certificate_sensitive_caps_v1().cap_profile_id,
        None if prior is None else prior.prior_id,
        effective_prior_id,
        disposition,
        model.model_id,
        audit.audit_id,
        threshold.threshold_profile_id,
        tuple(consumed),
        pending,
        outcome,
        cumulative,
        _schedule_id(tuple(prepared_all)),
        _trace_id(model.model_id, tuple(consumed)),
    )


@dataclass(frozen=True, slots=True)
class CertificateSensitiveMatchedCampaignV1:
    source_prior: SourceFrozenConsensusPriorV1
    ood_prior: SourceFrozenConsensusPriorV1
    wrong_prior: SourceFrozenConsensusPriorV1
    source_run: CertificateSensitiveGreedyRunV1
    no_prior_run: CertificateSensitiveGreedyRunV1
    ood_run: CertificateSensitiveGreedyRunV1
    wrong_run: CertificateSensitiveGreedyRunV1
    ood_exactly_matches_no_prior: bool
    confirmatory_result: bool = False
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        runs = (
            self.source_run,
            self.no_prior_run,
            self.ood_run,
            self.wrong_run,
        )
        if (
            tuple(item.arm for item in runs)
            != tuple(MatchedArm)
            or len({item.source_registry_id for item in runs}) != 1
            or self.source_prior.prior_id
            != self.source_run.requested_prior_id
            or self.ood_prior.prior_id != self.ood_run.requested_prior_id
            or self.wrong_prior.prior_id
            != self.wrong_run.requested_prior_id
            or self.wrong_prior.prior_id != self.source_prior.prior_id
            or self.source_prior.applicable_feature_schema_id
            != FEATURE_SCHEMA_ID
            or self.wrong_prior.applicable_feature_schema_id
            != FEATURE_SCHEMA_ID
            or self.ood_prior.applicable_feature_schema_id
            == FEATURE_SCHEMA_ID
            or self.ood_exactly_matches_no_prior
            is not (
                self.ood_run.effective_schedule_id
                == self.no_prior_run.effective_schedule_id
                and self.ood_run.target_trace_id
                == self.no_prior_run.target_trace_id
                and self.ood_run.outcome == self.no_prior_run.outcome
            )
            or self.ood_exactly_matches_no_prior is not True
            or self.confirmatory_result is not False
            or self.sample_efficiency_claimed is not False
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "matched campaign is invalid"
            )

    @property
    def campaign_id(self) -> str:
        return _content_id(
            "campaign",
            {
                "schema": "acfqp.certificate_sensitive_campaign.v1",
                "source_prior_id": self.source_prior.prior_id,
                "ood_prior_id": self.ood_prior.prior_id,
                "wrong_prior_id": self.wrong_prior.prior_id,
                "run_ids": [item.run_id for item in (
                    self.source_run,
                    self.no_prior_run,
                    self.ood_run,
                    self.wrong_run,
                )],
                "ood_exactly_matches_no_prior": True,
                "retrospective_scope": RETROSPECTIVE_SCOPE,
                "confirmatory_result": False,
                "sample_efficiency_claimed": False,
            },
        )


def run_certificate_sensitive_matched_campaign_v1(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetLocalCandidateRegistryV1,
    source_prior: SourceFrozenConsensusPriorV1,
    ood_prior: SourceFrozenConsensusPriorV1,
    wrong_prior: SourceFrozenConsensusPriorV1,
    synthetic_materializer: bool = False,
    max_workers: int = 1,
) -> CertificateSensitiveMatchedCampaignV1:
    if wrong_prior.prior_id != source_prior.prior_id:
        raise CertificateSensitiveGreedyInvariantViolation(
            "wrong control must reverse the same frozen source prior"
        )
    def run(
        arm: MatchedArm,
        prior: SourceFrozenConsensusPriorV1 | None,
    ) -> CertificateSensitiveGreedyRunV1:
        return run_certificate_sensitive_greedy_acquisition_v1(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=arm,
            prior=prior,
            synthetic_materializer=synthetic_materializer,
            max_workers=max_workers,
        )

    source = run(MatchedArm.SOURCE_CONSENSUS_PRIOR, source_prior)
    no_prior = run(MatchedArm.NO_PRIOR, None)
    ood = run(MatchedArm.OOD_ABSTENTION, ood_prior)
    wrong = run(MatchedArm.WRONG_CONSENSUS_PRIOR, wrong_prior)
    return CertificateSensitiveMatchedCampaignV1(
        source_prior,
        ood_prior,
        wrong_prior,
        source,
        no_prior,
        ood,
        wrong,
        True,
    )


@dataclass(frozen=True, slots=True)
class CertificateSensitiveGreedyVerificationV1:
    claimed_run_id: str
    replayed_run_id: str | None
    valid: bool
    reason: str
    same_implementation_replay: bool = True
    independent_verifier: bool = False

    def __post_init__(self) -> None:
        _cid(self.claimed_run_id, "claimed run")
        if self.replayed_run_id is not None:
            _cid(self.replayed_run_id, "replayed run")
        if (
            self.valid is not (
                self.replayed_run_id == self.claimed_run_id
            )
            or self.same_implementation_replay is not True
            or self.independent_verifier is not False
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "verification result is inconsistent"
            )

    @property
    def verification_id(self) -> str:
        return _content_id(
            "verification",
            {
                "schema": "acfqp.certificate_sensitive_verification.v1",
                "claimed_run_id": self.claimed_run_id,
                "replayed_run_id": self.replayed_run_id,
                "valid": self.valid,
                "reason": self.reason,
                "same_implementation_replay": True,
                "independent_verifier": False,
            },
        )


def verify_certificate_sensitive_greedy_run_v1(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetLocalCandidateRegistryV1,
    arm: MatchedArm,
    prior: SourceFrozenConsensusPriorV1 | None,
    claimed: CertificateSensitiveGreedyRunV1,
    synthetic_materializer: bool = False,
    max_workers: int = 1,
) -> CertificateSensitiveGreedyVerificationV1:
    try:
        replayed = run_certificate_sensitive_greedy_acquisition_v1(
            model=model,
            audit=audit,
            threshold=threshold,
            registry=registry,
            arm=arm,
            prior=prior,
            synthetic_materializer=synthetic_materializer,
            max_workers=max_workers,
        )
    except (
        CertificateSensitiveGreedyInvariantViolation,
        robust.PartialSupportRobustPlannerInvariantViolation,
        joint.ObservationSupportJointPairInvariantViolation,
    ) as error:
        return CertificateSensitiveGreedyVerificationV1(
            claimed.run_id,
            None,
            False,
            f"INVALID_INPUT:{type(error).__name__}",
        )
    return CertificateSensitiveGreedyVerificationV1(
        claimed.run_id,
        replayed.run_id,
        replayed.run_id == claimed.run_id,
        (
            "VALID"
            if replayed.run_id == claimed.run_id
            else "REPLAY_ID_MISMATCH"
        ),
    )


@dataclass(frozen=True, slots=True)
class K6RetrospectiveNonconfirmatoryV1:
    v0070_run_id: str
    v0070_registry_id: str
    observed_v0070_outcome: str
    operator_outcome: str
    operator_outcome_preassumed: bool = False
    retrospective_only: bool = True
    confirmatory_result: bool = False
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.v0070_run_id, "K6 V0-070 run")
        _cid(self.v0070_registry_id, "K6 V0-070 registry")
        if (
            self.operator_outcome
            not in (
                GreedyAcquisitionOutcome.AUTHORIZATION_READY.value,
                GreedyAcquisitionOutcome.DRAW_CAP_EXHAUSTED.value,
                GreedyAcquisitionOutcome.NO_POSITIVE_GAIN.value,
            )
            or self.operator_outcome_preassumed is not False
            or self.retrospective_only is not True
            or self.confirmatory_result is not False
            or self.sample_efficiency_claimed is not False
        ):
            raise CertificateSensitiveGreedyInvariantViolation(
                "K6 record crossed its retrospective boundary"
            )

    @property
    def record_id(self) -> str:
        return _content_id(
            "k6",
            {
                "schema": "acfqp.k6_retrospective_nonconfirmatory.v1",
                **{
                    key: getattr(self, key)
                    for key in self.__dataclass_fields__
                },
            },
        )


def freeze_k6_retrospective_nonconfirmatory_v1(
    *,
    v0070_run: joint.JointPairSupportRunV1,
    operator_run: CertificateSensitiveGreedyRunV1,
) -> K6RetrospectiveNonconfirmatoryV1:
    if (
        type(v0070_run) is not joint.JointPairSupportRunV1
        or type(operator_run) is not CertificateSensitiveGreedyRunV1
        or operator_run.source_registry_id
        != v0070_run.registry.registry_id
        or operator_run.certificate is not None
        or operator_run.outcome
        not in (
            GreedyAcquisitionOutcome.AUTHORIZATION_READY,
            GreedyAcquisitionOutcome.DRAW_CAP_EXHAUSTED,
            GreedyAcquisitionOutcome.NO_POSITIVE_GAIN,
        )
    ):
        raise CertificateSensitiveGreedyInvariantViolation(
            "real K6 may freeze only an authorization/cap/no-gain result"
        )
    return K6RetrospectiveNonconfirmatoryV1(
        v0070_run.run_id,
        v0070_run.registry.registry_id,
        v0070_run.outcome.value,
        operator_run.outcome.value,
    )


__all__ = [
    "CERTIFICATE_AUTHORITY",
    "CONTRACT_VERSION",
    "CertificateSensitiveGreedyInvariantViolation",
    "CertificateSensitiveGreedyRunV1",
    "CertificateSensitiveMatchedCampaignV1",
    "FEATURE_SCHEMA_ID",
    "GreedyAcquisitionOutcome",
    "MatchedArm",
    "PROFILE_KEY",
    "PriorDisposition",
    "SourceFrozenConsensusPriorV1",
    "SourceLocalTrialV1",
    "SourcePriorVoteV1",
    "freeze_k6_retrospective_nonconfirmatory_v1",
    "freeze_source_consensus_prior_v1",
    "freeze_target_local_candidate_registry_v1",
    "materialize_synthetic_exact_support_absence_v1",
    "prepare_certificate_sensitive_round_v1",
    "registered_certificate_sensitive_caps_v1",
    "run_certificate_sensitive_greedy_acquisition_v1",
    "run_certificate_sensitive_matched_campaign_v1",
    "verify_certificate_sensitive_greedy_run_v1",
]
