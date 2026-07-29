"""Development-only certificate-boundary value-of-information scorer.

This module is the first V0-073 construction slice.  It deliberately stops
before target observation, materialization, confidence-authority mutation, or
certificate emission.

For every OTHER-positive row on the current failed selected-policy frontier,
the scorer:

* consumes the row's current, already charged count vector;
* enumerates a preregistered finite next block under an exact Jeffreys/KT
  Dirichlet-multinomial predictive law;
* keeps every unobserved outcome inside the existing typed OTHER event;
* replaces only the candidate row by the exact posterior-predictive point row
  for each fantasy count vector;
* calls the existing exact H=2 robust planner and measures exact proof-gap
  contraction; and
* averages that contraction using ``Fraction`` arithmetic.

The predictive law and every fantasy are proposal-only.  They are not a
confidence sequence and cannot authorize a plan.  A source-frozen prior may
only multiply the completed target-only base VOI.  It is absent from all
fantasy models, planner calls, proof gaps, and candidate base-score identities.

Registered V0-072/V0-073 target execution remains locked.  The included
fixture is source/target-disjoint development evidence with two genuine
candidate rows and different one-block stopping opportunities.  It is not a
sample-saving result.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
import math
from typing import Any, Iterable, Mapping, Sequence

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.37.0"
PROFILE_KEY = "v073_development_certificate_boundary_voi_v1"

REGISTERED_EXECUTION_ALLOWED = False
REGISTERED_TARGET_OBSERVATIONS = 0
SAMPLE_EFFICIENCY_GATE_STATUS = "NOT_RUN"
SAMPLE_SAVING_CLAIMED = False
DEVELOPMENT_ONLY = True

JEFFREYS_ALPHA = Fraction(1, 2)
MAX_DEVELOPMENT_NEXT_BLOCK_SIZE = 8


class V073CertificateBoundaryVOIInvariantViolation(ValueError):
    """A VOI input, fantasy, source prior, or identity is invalid."""


class RegisteredV073CertificateBoundaryVOILocked(RuntimeError):
    """The registered target scorer remains unavailable."""


class DevelopmentVOIArmV1(str, Enum):
    NO_PRIOR = "NO_PRIOR"
    SOURCE_META_PRIOR = "SOURCE_META_PRIOR"


DOMAIN_TAGS = {
    "atom": "acfqp:v073-development-atom:v1",
    "portable_feature": "acfqp:v073-portable-voi-feature:v1",
    "source_trial": "acfqp:v073-source-voi-trial:v1",
    "source_entry": "acfqp:v073-source-voi-prior-entry:v1",
    "source_prior": "acfqp:v073-source-voi-prior:v1",
    "row_evidence": "acfqp:v073-current-row-count-evidence:v1",
    "dag_risk": "acfqp:v073-failed-proof-risk-node:v1",
    "dag_regret": "acfqp:v073-failed-proof-regret-node:v1",
    "dag_root": "acfqp:v073-failed-proof-gap-node:v1",
    "dag": "acfqp:v073-failed-proof-dag:v1",
    "candidate": "acfqp:v073-certificate-boundary-voi-candidate:v1",
    "fantasy": "acfqp:v073-kt-proof-gap-fantasy:v1",
    "base": "acfqp:v073-target-only-base-voi:v1",
    "arm_score": "acfqp:v073-proposal-only-arm-voi-score:v1",
    "schedule": "acfqp:v073-voi-candidate-schedule:v1",
    "result": "acfqp:v073-development-voi-result:v1",
    "control": "acfqp:v073-development-voi-opportunity-control:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-073 content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V073CertificateBoundaryVOIInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V073CertificateBoundaryVOIInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "V0-073 arithmetic must remain exact Fraction"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _atom(label: str) -> str:
    if type(label) is not str or not label:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "development atom label must be nonempty text"
        )
    return _content_id(
        "atom",
        {
            "schema": "acfqp.v073_development_atom.v1",
            "schema_version": SCHEMA_VERSION,
            "label": label,
        },
    )


def _sorted_cids(
    values: Sequence[str],
    field_name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise V073CertificateBoundaryVOIInvariantViolation(
            f"{field_name} must be an immutable tuple"
        )
    parsed = tuple(_cid(value, field_name) for value in values)
    if (
        (not allow_empty and not parsed)
        or parsed != tuple(sorted(set(parsed)))
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            f"{field_name} must be sorted and distinct"
        )
    return parsed


def _proof_gap(
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> Fraction:
    return max(
        Fraction(0),
        audit.root_failure_upper - threshold.risk_tolerance,
        (
            audit.normalized_regret_upper
            - threshold.normalized_regret_tolerance
        ),
    )


def _portable_feature_key(
    *,
    remaining_horizon: int,
    selected_row_category: robust.SelectedRowCategory,
) -> str:
    if (
        remaining_horizon not in (1, 2)
        or type(selected_row_category) is not robust.SelectedRowCategory
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "portable VOI feature semantics are invalid"
        )
    return _content_id(
        "portable_feature",
        {
            "schema": "acfqp.v073_portable_voi_feature.v1",
            "schema_version": SCHEMA_VERSION,
            "remaining_horizon": remaining_horizon,
            "selected_row_category": selected_row_category.value,
            "context_id_absent": True,
            "row_id_absent": True,
            "sample_count_absent": True,
            "probability_absent": True,
            "target_role_absent": True,
        },
    )


@dataclass(frozen=True, slots=True)
class DevelopmentSourceVOITrialV1:
    """One source-only, target-free proposal-ranking trial."""

    source_context_id: str
    feature_key: str
    source_utility: Fraction
    target_context_id: None = None
    target_model_id: None = None
    target_audit_id: None = None
    target_outcome_used: bool = False

    def __post_init__(self) -> None:
        _cid(self.source_context_id, "source trial context")
        _cid(self.feature_key, "source trial feature")
        if (
            type(self.source_utility) is not Fraction
            or self.target_context_id is not None
            or self.target_model_id is not None
            or self.target_audit_id is not None
            or self.target_outcome_used is not False
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "source trial contains target evidence or inexact utility"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_source_voi_trial.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "feature_key": self.feature_key,
            "source_utility": _fdoc(self.source_utility),
            "target_context_id": None,
            "target_model_id": None,
            "target_audit_id": None,
            "target_outcome_used": False,
            "proposal_only": True,
        }

    @property
    def trial_id(self) -> str:
        return _content_id("source_trial", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trial_id": self.trial_id}


@dataclass(frozen=True, slots=True)
class DevelopmentSourceVOIPriorEntryV1:
    feature_key: str
    q: Fraction
    worst_midrank: Fraction
    source_context_count: int
    source_trial_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.feature_key, "source prior feature")
        _sorted_cids(self.source_trial_ids, "source prior trials")
        if (
            type(self.q) is not Fraction
            or type(self.worst_midrank) is not Fraction
            or not 0 <= self.worst_midrank <= self.q <= 1
            or type(self.source_context_count) is not int
            or self.source_context_count < 2
            or len(self.source_trial_ids) != self.source_context_count
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "source prior entry is not an exact multi-context midrank"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_source_voi_prior_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "feature_key": self.feature_key,
            "q": _fdoc(self.q),
            "worst_midrank": _fdoc(self.worst_midrank),
            "source_context_count": self.source_context_count,
            "source_trial_ids": list(self.source_trial_ids),
            "may_certify": False,
        }

    @property
    def entry_id(self) -> str:
        return _content_id("source_entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


@dataclass(frozen=True, slots=True)
class DevelopmentSourceVOIPriorV1:
    source_context_ids: tuple[str, ...]
    source_trial_ids: tuple[str, ...]
    entries: tuple[DevelopmentSourceVOIPriorEntryV1, ...]
    target_context_ids: tuple[str, ...] = ()
    may_certify: bool = False
    may_narrow_confidence: bool = False

    def __post_init__(self) -> None:
        _sorted_cids(self.source_context_ids, "source prior contexts")
        _sorted_cids(self.source_trial_ids, "source prior trial IDs")
        if (
            type(self.entries) is not tuple
            or len(self.entries) < 2
            or any(
                type(item) is not DevelopmentSourceVOIPriorEntryV1
                for item in self.entries
            )
            or tuple(item.feature_key for item in self.entries)
            != tuple(sorted({item.feature_key for item in self.entries}))
            or set(self.source_trial_ids)
            != {
                trial_id
                for item in self.entries
                for trial_id in item.source_trial_ids
            }
            or self.target_context_ids != ()
            or self.may_certify is not False
            or self.may_narrow_confidence is not False
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "source VOI prior is not frozen proposal-only evidence"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_source_voi_prior.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_ids": list(self.source_context_ids),
            "source_trial_ids": list(self.source_trial_ids),
            "entry_ids": [item.entry_id for item in self.entries],
            "target_context_ids": [],
            "target_quantities_used": [],
            "may_certify": False,
            "may_narrow_confidence": False,
        }

    @property
    def prior_id(self) -> str:
        return _content_id("source_prior", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [item.to_document() for item in self.entries],
            "prior_id": self.prior_id,
        }


def _normalized_midranks(
    utilities: Mapping[str, Fraction],
) -> dict[str, Fraction]:
    if len(utilities) < 2 or any(
        type(value) is not Fraction for value in utilities.values()
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "source context requires at least two exact utilities"
        )
    ordered_values = sorted(set(utilities.values()))
    n = len(utilities)
    output: dict[str, Fraction] = {}
    for utility in ordered_values:
        tied = sorted(
            key for key, value in utilities.items() if value == utility
        )
        positions = sorted(
            index
            for index, (_, value) in enumerate(
                sorted(utilities.items(), key=lambda item: (item[1], item[0]))
            )
            if value == utility
        )
        rank = sum((Fraction(item) for item in positions), Fraction(0))
        rank /= len(positions)
        normalized = rank / (n - 1)
        for feature_key in tied:
            output[feature_key] = normalized
    return output


def build_development_source_voi_prior_v1(
    trials: Iterable[DevelopmentSourceVOITrialV1],
) -> DevelopmentSourceVOIPriorV1:
    trial_tuple = tuple(sorted(trials, key=lambda item: item.trial_id))
    if (
        len(trial_tuple) < 4
        or any(type(item) is not DevelopmentSourceVOITrialV1 for item in trial_tuple)
        or len({item.trial_id for item in trial_tuple}) != len(trial_tuple)
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "source prior requires distinct typed trials"
        )
    contexts = tuple(
        sorted({item.source_context_id for item in trial_tuple})
    )
    features = tuple(sorted({item.feature_key for item in trial_tuple}))
    if len(contexts) < 2 or len(features) < 2:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "source prior lacks multi-context, multi-candidate support"
        )
    by_context: dict[str, dict[str, Fraction]] = {}
    trial_by_pair: dict[tuple[str, str], DevelopmentSourceVOITrialV1] = {}
    for trial in trial_tuple:
        pair = trial.source_context_id, trial.feature_key
        if pair in trial_by_pair:
            raise V073CertificateBoundaryVOIInvariantViolation(
                "source trial context/feature pair is duplicated"
            )
        trial_by_pair[pair] = trial
        by_context.setdefault(trial.source_context_id, {})[
            trial.feature_key
        ] = trial.source_utility
    if any(tuple(sorted(values)) != features for values in by_context.values()):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "development source prior requires rectangular feature coverage"
        )
    midranks = {
        context_id: _normalized_midranks(utilities)
        for context_id, utilities in by_context.items()
    }
    entries = []
    for feature_key in features:
        values = tuple(
            midranks[context_id][feature_key] for context_id in contexts
        )
        entries.append(
            DevelopmentSourceVOIPriorEntryV1(
                feature_key=feature_key,
                q=sum(values, Fraction(0)) / len(values),
                worst_midrank=min(values),
                source_context_count=len(contexts),
                source_trial_ids=tuple(
                    sorted(
                        trial_by_pair[(context_id, feature_key)].trial_id
                        for context_id in contexts
                    )
                ),
            )
        )
    return DevelopmentSourceVOIPriorV1(
        source_context_ids=contexts,
        source_trial_ids=tuple(item.trial_id for item in trial_tuple),
        entries=tuple(sorted(entries, key=lambda item: item.feature_key)),
    )


@dataclass(frozen=True, slots=True)
class CurrentRowCountEvidenceV1:
    """Already charged current count/support evidence for one model row."""

    context_id: str
    model_id: str
    row_id: str
    evidence_epoch_id: str
    destination_ids: tuple[str, ...]
    counts: tuple[int, ...]
    other_destination_id: str
    unobserved_outcomes_aggregated_into_other: bool = True
    future_child_support_enumerated: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.context_id, "row-evidence context"),
            (self.model_id, "row-evidence model"),
            (self.row_id, "row-evidence row"),
            (self.evidence_epoch_id, "row-evidence epoch"),
            (self.other_destination_id, "row-evidence OTHER"),
        ):
            _cid(value, field_name)
        _sorted_cids(self.destination_ids, "row-evidence destinations")
        if (
            type(self.counts) is not tuple
            or len(self.counts) != len(self.destination_ids)
            or any(type(value) is not int or value < 0 for value in self.counts)
            or sum(self.counts) <= 0
            or self.destination_ids.count(self.other_destination_id) != 1
            or self.unobserved_outcomes_aggregated_into_other is not True
            or self.future_child_support_enumerated is not False
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "current count evidence is incomplete or leaks future support"
            )

    @property
    def draw_count(self) -> int:
        return sum(self.counts)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_current_row_count_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "model_id": self.model_id,
            "row_id": self.row_id,
            "evidence_epoch_id": self.evidence_epoch_id,
            "destination_ids": list(self.destination_ids),
            "counts": list(self.counts),
            "draw_count": self.draw_count,
            "other_destination_id": self.other_destination_id,
            "unobserved_outcomes_aggregated_into_other": True,
            "future_child_support_enumerated": False,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("row_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class DevelopmentFailedProofDAGV1:
    """Minimal exact dependency snapshot for the failed proof gap."""

    model_id: str
    threshold_profile_id: str
    audit_id: str
    frontier_id: str
    selected_row_ids: tuple[str, ...]
    risk_node_id: str
    regret_node_id: str
    gap_node_id: str
    current_proof_gap: Fraction

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.model_id, "DAG model"),
            (self.threshold_profile_id, "DAG threshold"),
            (self.audit_id, "DAG audit"),
            (self.frontier_id, "DAG frontier"),
            (self.risk_node_id, "DAG risk node"),
            (self.regret_node_id, "DAG regret node"),
            (self.gap_node_id, "DAG gap node"),
        ):
            _cid(value, field_name)
        _sorted_cids(self.selected_row_ids, "DAG selected rows")
        if (
            type(self.current_proof_gap) is not Fraction
            or self.current_proof_gap <= 0
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "DAG does not bind one positive failed-proof gap"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_failed_proof_dag.v1",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "selected_row_ids": list(self.selected_row_ids),
            "risk_node_id": self.risk_node_id,
            "regret_node_id": self.regret_node_id,
            "gap_node_id": self.gap_node_id,
            "current_proof_gap": _fdoc(self.current_proof_gap),
            "source_prior_inputs": [],
        }

    @property
    def dag_id(self) -> str:
        return _content_id("dag", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "dag_id": self.dag_id}


def freeze_development_failed_proof_dag_v1(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    audit: robust.RobustPlanAuditV1,
) -> DevelopmentFailedProofDAGV1:
    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(audit) is not robust.RobustPlanAuditV1
        or audit.model_id != model.model_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or audit.failed_frontier is None
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "failed-proof DAG requires one exact failed robust audit"
        )
    robust.verify_robust_plan_audit_v1(model, threshold, audit)
    risk_payload = {
        "schema": "acfqp.v073_failed_proof_risk_node.v1",
        "schema_version": SCHEMA_VERSION,
        "model_id": model.model_id,
        "audit_id": audit.audit_id,
        "selected_row_bound_ids": [
            item.row_bound_id for item in audit.selected_row_bounds
        ],
        "root_failure_upper": _fdoc(audit.root_failure_upper),
        "risk_tolerance": _fdoc(threshold.risk_tolerance),
        "source_prior_inputs": [],
    }
    regret_payload = {
        "schema": "acfqp.v073_failed_proof_regret_node.v1",
        "schema_version": SCHEMA_VERSION,
        "model_id": model.model_id,
        "audit_id": audit.audit_id,
        "selected_row_bound_ids": [
            item.row_bound_id for item in audit.selected_row_bounds
        ],
        "normalized_regret_upper": _fdoc(
            audit.normalized_regret_upper
        ),
        "normalized_regret_tolerance": _fdoc(
            threshold.normalized_regret_tolerance
        ),
        "source_prior_inputs": [],
    }
    risk_node_id = _content_id("dag_risk", risk_payload)
    regret_node_id = _content_id("dag_regret", regret_payload)
    current_gap = _proof_gap(audit, threshold)
    gap_node_id = _content_id(
        "dag_root",
        {
            "schema": "acfqp.v073_failed_proof_gap_node.v1",
            "schema_version": SCHEMA_VERSION,
            "ordered_parent_ids": [risk_node_id, regret_node_id],
            "current_proof_gap": _fdoc(current_gap),
            "source_prior_inputs": [],
        },
    )
    return DevelopmentFailedProofDAGV1(
        model_id=model.model_id,
        threshold_profile_id=threshold.threshold_profile_id,
        audit_id=audit.audit_id,
        frontier_id=audit.failed_frontier.frontier_id,
        selected_row_ids=audit.failed_frontier.selected_row_ids,
        risk_node_id=risk_node_id,
        regret_node_id=regret_node_id,
        gap_node_id=gap_node_id,
        current_proof_gap=current_gap,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentVOICandidateV1:
    row_id: str
    state_id: str
    action_id: str
    remaining_horizon: int
    selected_row_category: robust.SelectedRowCategory
    feature_key: str
    row_evidence_id: str
    other_destination_id: str

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.row_id, "VOI candidate row"),
            (self.state_id, "VOI candidate state"),
            (self.action_id, "VOI candidate action"),
            (self.feature_key, "VOI candidate feature"),
            (self.row_evidence_id, "VOI candidate evidence"),
            (self.other_destination_id, "VOI candidate OTHER"),
        ):
            _cid(value, field_name)
        if (
            self.remaining_horizon not in (1, 2)
            or type(self.selected_row_category)
            is not robust.SelectedRowCategory
            or self.feature_key
            != _portable_feature_key(
                remaining_horizon=self.remaining_horizon,
                selected_row_category=self.selected_row_category,
            )
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "candidate portable feature was caller-supplied or changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_certificate_boundary_voi_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "row_id": self.row_id,
            "state_id": self.state_id,
            "action_id": self.action_id,
            "remaining_horizon": self.remaining_horizon,
            "selected_row_category": self.selected_row_category.value,
            "feature_key": self.feature_key,
            "row_evidence_id": self.row_evidence_id,
            "other_destination_id": self.other_destination_id,
            "derived_from_failed_frontier": True,
            "future_child_support_enumerated": False,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class DevelopmentKTFantasyV1:
    candidate_id: str
    row_evidence_id: str
    next_block_size: int
    destination_ids: tuple[str, ...]
    additional_counts: tuple[int, ...]
    predictive_probability: Fraction
    posterior_predictive_masses: tuple[Fraction, ...]
    fantasy_model_id: str
    fantasy_audit_id: str
    proof_gap_after: Fraction
    proof_gap_reduction: Fraction
    would_certify_in_proposal_fantasy: bool
    other_destination_id: str
    unknown_child_destination_ids: tuple[str, ...] = ()
    source_prior_inputs: tuple[str, ...] = ()
    certificate_authority: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.candidate_id, "fantasy candidate"),
            (self.row_evidence_id, "fantasy row evidence"),
            (self.fantasy_model_id, "fantasy model"),
            (self.fantasy_audit_id, "fantasy audit"),
            (self.other_destination_id, "fantasy OTHER"),
        ):
            _cid(value, field_name)
        _sorted_cids(self.destination_ids, "fantasy destinations")
        if (
            type(self.next_block_size) is not int
            or not 1 <= self.next_block_size <= MAX_DEVELOPMENT_NEXT_BLOCK_SIZE
            or type(self.additional_counts) is not tuple
            or len(self.additional_counts) != len(self.destination_ids)
            or any(
                type(value) is not int or value < 0
                for value in self.additional_counts
            )
            or sum(self.additional_counts) != self.next_block_size
            or type(self.predictive_probability) is not Fraction
            or not 0 < self.predictive_probability <= 1
            or type(self.posterior_predictive_masses) is not tuple
            or len(self.posterior_predictive_masses)
            != len(self.destination_ids)
            or any(
                type(value) is not Fraction or not 0 <= value <= 1
                for value in self.posterior_predictive_masses
            )
            or sum(self.posterior_predictive_masses, Fraction(0)) != 1
            or type(self.proof_gap_after) is not Fraction
            or type(self.proof_gap_reduction) is not Fraction
            or min(self.proof_gap_after, self.proof_gap_reduction) < 0
            or type(self.would_certify_in_proposal_fantasy) is not bool
            or self.destination_ids.count(self.other_destination_id) != 1
            or self.unknown_child_destination_ids != ()
            or self.source_prior_inputs != ()
            or self.certificate_authority is not False
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "KT fantasy is inexact, introduces support, or claims authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_kt_proof_gap_fantasy.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "row_evidence_id": self.row_evidence_id,
            "next_block_size": self.next_block_size,
            "destination_ids": list(self.destination_ids),
            "additional_counts": list(self.additional_counts),
            "predictive_probability": _fdoc(self.predictive_probability),
            "posterior_predictive_masses": [
                _fdoc(value) for value in self.posterior_predictive_masses
            ],
            "fantasy_model_id": self.fantasy_model_id,
            "fantasy_audit_id": self.fantasy_audit_id,
            "proof_gap_after": _fdoc(self.proof_gap_after),
            "proof_gap_reduction": _fdoc(self.proof_gap_reduction),
            "would_certify_in_proposal_fantasy": (
                self.would_certify_in_proposal_fantasy
            ),
            "other_destination_id": self.other_destination_id,
            "unknown_child_destination_ids": [],
            "source_prior_inputs": [],
            "certificate_authority": False,
        }

    @property
    def fantasy_id(self) -> str:
        return _content_id("fantasy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "fantasy_id": self.fantasy_id}


@dataclass(frozen=True, slots=True)
class DevelopmentTargetOnlyBoundaryVOIV1:
    candidate: DevelopmentVOICandidateV1
    proof_dag_id: str
    next_block_size: int
    fantasies: tuple[DevelopmentKTFantasyV1, ...]
    current_proof_gap: Fraction
    expected_gap_reduction: Fraction
    base_voi_per_draw: Fraction
    certifying_fantasy_probability: Fraction
    predictive_kind: str = "JEFFREYS_KT_DIRICHLET_MULTINOMIAL"
    source_prior_inputs: tuple[str, ...] = ()
    certificate_authority: bool = False

    def __post_init__(self) -> None:
        _cid(self.proof_dag_id, "base VOI proof DAG")
        if (
            type(self.candidate) is not DevelopmentVOICandidateV1
            or type(self.next_block_size) is not int
            or not 1 <= self.next_block_size <= MAX_DEVELOPMENT_NEXT_BLOCK_SIZE
            or type(self.fantasies) is not tuple
            or not self.fantasies
            or any(
                type(item) is not DevelopmentKTFantasyV1
                for item in self.fantasies
            )
            or tuple(item.fantasy_id for item in self.fantasies)
            != tuple(sorted({item.fantasy_id for item in self.fantasies}))
            or any(
                item.candidate_id != self.candidate.candidate_id
                or item.row_evidence_id != self.candidate.row_evidence_id
                or item.next_block_size != self.next_block_size
                for item in self.fantasies
            )
            or sum(
                (item.predictive_probability for item in self.fantasies),
                Fraction(0),
            )
            != 1
            or type(self.current_proof_gap) is not Fraction
            or self.current_proof_gap <= 0
            or type(self.expected_gap_reduction) is not Fraction
            or self.expected_gap_reduction
            != sum(
                (
                    item.predictive_probability
                    * item.proof_gap_reduction
                    for item in self.fantasies
                ),
                Fraction(0),
            )
            or self.base_voi_per_draw
            != self.expected_gap_reduction / self.next_block_size
            or self.certifying_fantasy_probability
            != sum(
                (
                    item.predictive_probability
                    for item in self.fantasies
                    if item.would_certify_in_proposal_fantasy
                ),
                Fraction(0),
            )
            or self.predictive_kind
            != "JEFFREYS_KT_DIRICHLET_MULTINOMIAL"
            or self.source_prior_inputs != ()
            or self.certificate_authority is not False
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "target-only base VOI is stale or source-contaminated"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_target_only_base_voi.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate.candidate_id,
            "proof_dag_id": self.proof_dag_id,
            "next_block_size": self.next_block_size,
            "fantasy_ids": [item.fantasy_id for item in self.fantasies],
            "current_proof_gap": _fdoc(self.current_proof_gap),
            "expected_gap_reduction": _fdoc(
                self.expected_gap_reduction
            ),
            "base_voi_per_draw": _fdoc(self.base_voi_per_draw),
            "certifying_fantasy_probability": _fdoc(
                self.certifying_fantasy_probability
            ),
            "predictive_kind": self.predictive_kind,
            "source_prior_inputs": [],
            "certificate_authority": False,
        }

    @property
    def base_voi_id(self) -> str:
        return _content_id("base", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidate": self.candidate.to_document(),
            "fantasies": [item.to_document() for item in self.fantasies],
            "base_voi_id": self.base_voi_id,
        }


@dataclass(frozen=True, slots=True)
class DevelopmentVOIArmScoreV1:
    arm: DevelopmentVOIArmV1
    base_voi_id: str
    candidate_id: str
    feature_key: str
    base_voi_per_draw: Fraction
    multiplier: Fraction
    score: Fraction
    source_q: Fraction | None
    source_prior_id: str | None
    proposal_only: bool = True
    certificate_authority: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.base_voi_id, "arm-score base"),
            (self.candidate_id, "arm-score candidate"),
            (self.feature_key, "arm-score feature"),
        ):
            _cid(value, field_name)
        if (
            type(self.arm) is not DevelopmentVOIArmV1
            or type(self.base_voi_per_draw) is not Fraction
            or type(self.multiplier) is not Fraction
            or type(self.score) is not Fraction
            or self.score != self.base_voi_per_draw * self.multiplier
            or self.proposal_only is not True
            or self.certificate_authority is not False
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "arm score arithmetic or authority is invalid"
            )
        if self.arm is DevelopmentVOIArmV1.NO_PRIOR:
            if (
                self.source_q is not None
                or self.source_prior_id is not None
                or self.multiplier != 1
            ):
                raise V073CertificateBoundaryVOIInvariantViolation(
                    "NO_PRIOR arm contains source inputs"
                )
        else:
            if (
                type(self.source_q) is not Fraction
                or not 0 <= self.source_q <= 1
                or self.source_prior_id is None
                or _cid(self.source_prior_id, "arm-score source prior")
                != self.source_prior_id
                or self.multiplier
                != Fraction(1, 2) + Fraction(3, 2) * self.source_q
            ):
                raise V073CertificateBoundaryVOIInvariantViolation(
                    "source multiplier was not applied outside the base VOI"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_proposal_only_arm_voi_score.v1",
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm.value,
            "base_voi_id": self.base_voi_id,
            "candidate_id": self.candidate_id,
            "feature_key": self.feature_key,
            "base_voi_per_draw": _fdoc(self.base_voi_per_draw),
            "multiplier": _fdoc(self.multiplier),
            "score": _fdoc(self.score),
            "source_q": (
                None if self.source_q is None else _fdoc(self.source_q)
            ),
            "source_prior_id": self.source_prior_id,
            "source_enters_base_voi": False,
            "source_enters_fantasy_model": False,
            "source_enters_certificate": False,
            "proposal_only": True,
            "certificate_authority": False,
        }

    @property
    def arm_score_id(self) -> str:
        return _content_id("arm_score", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "arm_score_id": self.arm_score_id}


@dataclass(frozen=True, slots=True)
class DevelopmentVOIScheduleV1:
    arm: DevelopmentVOIArmV1
    ordered_arm_score_ids: tuple[str, ...]
    ordered_candidate_ids: tuple[str, ...]
    selected_candidate_id: str
    ordering_rule: str = (
        "-score,-base_voi_per_draw,next_block_size,"
        "-remaining_horizon,candidate_id"
    )

    def __post_init__(self) -> None:
        _sorted_cids(self.ordered_arm_score_ids, "schedule score IDs")
        if (
            type(self.arm) is not DevelopmentVOIArmV1
            or type(self.ordered_candidate_ids) is not tuple
            or not self.ordered_candidate_ids
            or any(
                _cid(value, "schedule candidate") != value
                for value in self.ordered_candidate_ids
            )
            or len(set(self.ordered_candidate_ids))
            != len(self.ordered_candidate_ids)
            or _cid(
                self.selected_candidate_id,
                "schedule selected candidate",
            )
            != self.selected_candidate_id
            or self.selected_candidate_id != self.ordered_candidate_ids[0]
            or self.ordering_rule
            != (
                "-score,-base_voi_per_draw,next_block_size,"
                "-remaining_horizon,candidate_id"
            )
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "VOI schedule is empty, duplicated, or noncanonical"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_voi_candidate_schedule.v1",
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm.value,
            "ordered_arm_score_ids": list(self.ordered_arm_score_ids),
            "ordered_candidate_ids": list(self.ordered_candidate_ids),
            "selected_candidate_id": self.selected_candidate_id,
            "ordering_rule": self.ordering_rule,
            "authorization_emitted": False,
            "target_access_permitted": False,
        }

    @property
    def schedule_id(self) -> str:
        return _content_id("schedule", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "schedule_id": self.schedule_id}


@dataclass(frozen=True, slots=True)
class DevelopmentCertificateBoundaryVOIResultV1:
    arm: DevelopmentVOIArmV1
    context_id: str
    model_id: str
    threshold_profile_id: str
    failed_audit_id: str
    proof_dag_id: str
    row_evidence_ids: tuple[str, ...]
    base_vois: tuple[DevelopmentTargetOnlyBoundaryVOIV1, ...]
    arm_scores: tuple[DevelopmentVOIArmScoreV1, ...]
    schedule: DevelopmentVOIScheduleV1
    source_prior_id: str | None
    next_block_size: int
    target_observer_calls: int = 0
    target_draws: int = 0
    kernel_calls: int = 0
    materializer_calls: int = 0
    registered_target_evidence: bool = False
    sample_saving_claimed: bool = False
    sample_efficiency_gate_status: str = SAMPLE_EFFICIENCY_GATE_STATUS

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.context_id, "VOI result context"),
            (self.model_id, "VOI result model"),
            (self.threshold_profile_id, "VOI result threshold"),
            (self.failed_audit_id, "VOI result audit"),
            (self.proof_dag_id, "VOI result DAG"),
        ):
            _cid(value, field_name)
        _sorted_cids(self.row_evidence_ids, "VOI result evidence")
        if (
            type(self.arm) is not DevelopmentVOIArmV1
            or type(self.base_vois) is not tuple
            or len(self.base_vois) < 2
            or any(
                type(item) is not DevelopmentTargetOnlyBoundaryVOIV1
                for item in self.base_vois
            )
            or tuple(item.base_voi_id for item in self.base_vois)
            != tuple(sorted({item.base_voi_id for item in self.base_vois}))
            or set(self.row_evidence_ids)
            != {
                item.candidate.row_evidence_id for item in self.base_vois
            }
            or type(self.arm_scores) is not tuple
            or len(self.arm_scores) != len(self.base_vois)
            or any(
                type(item) is not DevelopmentVOIArmScoreV1
                or item.arm is not self.arm
                for item in self.arm_scores
            )
            or tuple(item.arm_score_id for item in self.arm_scores)
            != tuple(sorted({item.arm_score_id for item in self.arm_scores}))
            or {
                item.base_voi_id for item in self.arm_scores
            }
            != {item.base_voi_id for item in self.base_vois}
            or type(self.schedule) is not DevelopmentVOIScheduleV1
            or self.schedule.arm is not self.arm
            or type(self.next_block_size) is not int
            or any(
                item.next_block_size != self.next_block_size
                for item in self.base_vois
            )
            or any(
                value != 0
                for value in (
                    self.target_observer_calls,
                    self.target_draws,
                    self.kernel_calls,
                    self.materializer_calls,
                )
            )
            or self.registered_target_evidence is not False
            or self.sample_saving_claimed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "development VOI result accessed target evidence or is stale"
            )
        if self.arm is DevelopmentVOIArmV1.NO_PRIOR:
            if self.source_prior_id is not None:
                raise V073CertificateBoundaryVOIInvariantViolation(
                    "NO_PRIOR result binds a source prior"
                )
        elif (
            self.source_prior_id is None
            or _cid(self.source_prior_id, "VOI result source prior")
            != self.source_prior_id
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "source result lacks its proposal-only prior"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_development_voi_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "arm": self.arm.value,
            "context_id": self.context_id,
            "model_id": self.model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "failed_audit_id": self.failed_audit_id,
            "proof_dag_id": self.proof_dag_id,
            "row_evidence_ids": list(self.row_evidence_ids),
            "base_voi_ids": [item.base_voi_id for item in self.base_vois],
            "arm_score_ids": [
                item.arm_score_id for item in self.arm_scores
            ],
            "schedule_id": self.schedule.schedule_id,
            "source_prior_id": self.source_prior_id,
            "next_block_size": self.next_block_size,
            "target_observer_calls": 0,
            "target_draws": 0,
            "kernel_calls": 0,
            "materializer_calls": 0,
            "registered_target_evidence": False,
            "registered_execution_allowed": False,
            "sample_saving_claimed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "base_vois": [item.to_document() for item in self.base_vois],
            "arm_scores": [item.to_document() for item in self.arm_scores],
            "schedule": self.schedule.to_document(),
            "result_id": self.result_id,
        }


def _compositions(total: int, width: int) -> tuple[tuple[int, ...], ...]:
    if total < 0 or width <= 0:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "fantasy composition dimensions are invalid"
        )
    if width == 1:
        return ((total,),)
    output = []
    for first in range(total + 1):
        for suffix in _compositions(total - first, width - 1):
            output.append((first, *suffix))
    return tuple(output)


def _rising_fraction(start: Fraction, count: int) -> Fraction:
    value = Fraction(1)
    for offset in range(count):
        value *= start + offset
    return value


def _kt_fantasy_probability(
    current_counts: tuple[int, ...],
    additional_counts: tuple[int, ...],
) -> Fraction:
    if (
        len(current_counts) != len(additional_counts)
        or not current_counts
        or any(type(value) is not int or value < 0 for value in current_counts)
        or any(
            type(value) is not int or value < 0
            for value in additional_counts
        )
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "KT count vectors are malformed"
        )
    n = sum(additional_counts)
    coefficient = Fraction(math.factorial(n))
    for value in additional_counts:
        coefficient /= math.factorial(value)
    numerator = coefficient
    for current, additional in zip(current_counts, additional_counts):
        numerator *= _rising_fraction(
            Fraction(current) + JEFFREYS_ALPHA,
            additional,
        )
    denominator = _rising_fraction(
        Fraction(sum(current_counts))
        + len(current_counts) * JEFFREYS_ALPHA,
        n,
    )
    return numerator / denominator


def _posterior_predictive_masses(
    current_counts: tuple[int, ...],
    additional_counts: tuple[int, ...],
) -> tuple[Fraction, ...]:
    denominator = (
        sum(current_counts)
        + sum(additional_counts)
        + len(current_counts) * JEFFREYS_ALPHA
    )
    return tuple(
        (current + additional + JEFFREYS_ALPHA) / denominator
        for current, additional in zip(
            current_counts,
            additional_counts,
        )
    )


def _replace_candidate_row_with_point_masses(
    model: robust.PartialSupportIntervalModelV1,
    row_id: str,
    destination_ids: tuple[str, ...],
    masses: tuple[Fraction, ...],
) -> robust.PartialSupportIntervalModelV1:
    row_by_id = {item.row_id: item for item in model.rows}
    row = row_by_id.get(row_id)
    if row is None or tuple(item.destination_id for item in row.masses) != (
        destination_ids
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "fantasy row support differs from the current model"
        )
    replacement = replace(
        row,
        masses=tuple(
            robust.IntervalDestinationMassV1(
                destination_id,
                mass,
                mass,
            )
            for destination_id, mass in zip(
                destination_ids,
                masses,
            )
        ),
    )
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=(
            replacement if item.row_id == row_id else item
            for item in model.rows
        ),
        concretizer_entries=model.concretizer_entries,
    )


def _solve_like_current_audit(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
) -> robust.RobustPlanAuditV1:
    return (
        robust.solve_ground_direct_robust_h2_v1(model, threshold)
        if solver_kind is robust.RobustSolverKind.GROUND_DIRECT
        else robust.solve_quotient_robust_h2_v1(model, threshold)
    )


def _derive_candidates(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    row_evidence: tuple[CurrentRowCountEvidenceV1, ...],
) -> tuple[DevelopmentVOICandidateV1, ...]:
    if audit.failed_frontier is None:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "candidate derivation requires a failed frontier"
        )
    expected_rows = audit.failed_frontier.other_positive_row_ids
    evidence_by_row = {item.row_id: item for item in row_evidence}
    if (
        len(evidence_by_row) != len(row_evidence)
        or tuple(sorted(evidence_by_row)) != expected_rows
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "row evidence is not exactly the OTHER-positive failed frontier"
        )
    row_by_id = {item.row_id: item for item in model.rows}
    provenance_by_row = {
        item.row_id: item for item in audit.selected_row_provenance
    }
    candidates = []
    for row_id in expected_rows:
        row = row_by_id[row_id]
        evidence = evidence_by_row[row_id]
        provenance = provenance_by_row[row_id]
        destination_ids = tuple(item.destination_id for item in row.masses)
        if (
            evidence.context_id != model.context_id
            or evidence.model_id != model.model_id
            or evidence.destination_ids != destination_ids
            or evidence.other_destination_id != row.other_destination_id
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "current counts/support do not bind the candidate row"
            )
        feature_key = _portable_feature_key(
            remaining_horizon=row.remaining_horizon,
            selected_row_category=provenance.category,
        )
        candidates.append(
            DevelopmentVOICandidateV1(
                row_id=row.row_id,
                state_id=row.state_id,
                action_id=row.action_id,
                remaining_horizon=row.remaining_horizon,
                selected_row_category=provenance.category,
                feature_key=feature_key,
                row_evidence_id=evidence.evidence_id,
                other_destination_id=row.other_destination_id,
            )
        )
    return tuple(sorted(candidates, key=lambda item: item.candidate_id))


def _candidate_base_voi(
    *,
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    current_audit: robust.RobustPlanAuditV1,
    proof_dag: DevelopmentFailedProofDAGV1,
    candidate: DevelopmentVOICandidateV1,
    evidence: CurrentRowCountEvidenceV1,
    next_block_size: int,
) -> DevelopmentTargetOnlyBoundaryVOIV1:
    fantasies = []
    for additional in _compositions(
        next_block_size,
        len(evidence.destination_ids),
    ):
        probability = _kt_fantasy_probability(evidence.counts, additional)
        point_masses = _posterior_predictive_masses(
            evidence.counts,
            additional,
        )
        fantasy_model = _replace_candidate_row_with_point_masses(
            model,
            candidate.row_id,
            evidence.destination_ids,
            point_masses,
        )
        fantasy_audit = _solve_like_current_audit(
            fantasy_model,
            threshold,
            current_audit.solver_kind,
        )
        gap_after = _proof_gap(fantasy_audit, threshold)
        reduction = max(
            Fraction(0),
            proof_dag.current_proof_gap - gap_after,
        )
        fantasies.append(
            DevelopmentKTFantasyV1(
                candidate_id=candidate.candidate_id,
                row_evidence_id=evidence.evidence_id,
                next_block_size=next_block_size,
                destination_ids=evidence.destination_ids,
                additional_counts=additional,
                predictive_probability=probability,
                posterior_predictive_masses=point_masses,
                fantasy_model_id=fantasy_model.model_id,
                fantasy_audit_id=fantasy_audit.audit_id,
                proof_gap_after=gap_after,
                proof_gap_reduction=reduction,
                would_certify_in_proposal_fantasy=(
                    fantasy_audit.status
                    is robust.RobustAuditStatus.CERTIFIED
                    and gap_after == 0
                ),
                other_destination_id=evidence.other_destination_id,
            )
        )
    fantasy_tuple = tuple(
        sorted(fantasies, key=lambda item: item.fantasy_id)
    )
    expected = sum(
        (
            item.predictive_probability * item.proof_gap_reduction
            for item in fantasy_tuple
        ),
        Fraction(0),
    )
    certifying = sum(
        (
            item.predictive_probability
            for item in fantasy_tuple
            if item.would_certify_in_proposal_fantasy
        ),
        Fraction(0),
    )
    return DevelopmentTargetOnlyBoundaryVOIV1(
        candidate=candidate,
        proof_dag_id=proof_dag.dag_id,
        next_block_size=next_block_size,
        fantasies=fantasy_tuple,
        current_proof_gap=proof_dag.current_proof_gap,
        expected_gap_reduction=expected,
        base_voi_per_draw=expected / next_block_size,
        certifying_fantasy_probability=certifying,
    )


def score_development_certificate_boundary_voi_v1(
    *,
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    failed_audit: robust.RobustPlanAuditV1,
    proof_dag: DevelopmentFailedProofDAGV1,
    row_evidence: tuple[CurrentRowCountEvidenceV1, ...],
    next_block_size: int,
    arm: DevelopmentVOIArmV1,
    source_prior: DevelopmentSourceVOIPriorV1 | None = None,
) -> DevelopmentCertificateBoundaryVOIResultV1:
    """Score the current failed frontier without any target access."""

    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(failed_audit) is not robust.RobustPlanAuditV1
        or type(proof_dag) is not DevelopmentFailedProofDAGV1
        or type(row_evidence) is not tuple
        or any(
            type(item) is not CurrentRowCountEvidenceV1
            for item in row_evidence
        )
        or type(next_block_size) is not int
        or not 1 <= next_block_size <= MAX_DEVELOPMENT_NEXT_BLOCK_SIZE
        or type(arm) is not DevelopmentVOIArmV1
    ):
        raise V073CertificateBoundaryVOIInvariantViolation(
            "VOI scorer inputs are not exact development authorities"
        )
    robust.verify_robust_plan_audit_v1(model, threshold, failed_audit)
    expected_dag = freeze_development_failed_proof_dag_v1(
        model,
        threshold,
        failed_audit,
    )
    if proof_dag != expected_dag or proof_dag.dag_id != expected_dag.dag_id:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "failed-proof DAG is stale or transplanted"
        )
    if arm is DevelopmentVOIArmV1.NO_PRIOR:
        if source_prior is not None:
            raise V073CertificateBoundaryVOIInvariantViolation(
                "NO_PRIOR scorer cannot receive source evidence"
            )
    elif type(source_prior) is not DevelopmentSourceVOIPriorV1:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "SOURCE_META_PRIOR scorer requires one exact frozen prior"
        )
    assert failed_audit.failed_frontier is not None
    candidates = _derive_candidates(model, failed_audit, row_evidence)
    if len(candidates) < 2:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "development VOI slice requires a real multi-candidate frontier"
        )
    evidence_by_id = {item.evidence_id: item for item in row_evidence}
    base_vois = tuple(
        sorted(
            (
                _candidate_base_voi(
                    model=model,
                    threshold=threshold,
                    current_audit=failed_audit,
                    proof_dag=proof_dag,
                    candidate=candidate,
                    evidence=evidence_by_id[candidate.row_evidence_id],
                    next_block_size=next_block_size,
                )
                for candidate in candidates
            ),
            key=lambda item: item.base_voi_id,
        )
    )
    prior_by_feature = (
        {}
        if source_prior is None
        else {item.feature_key: item for item in source_prior.entries}
    )
    arm_scores = []
    for base in base_vois:
        if arm is DevelopmentVOIArmV1.NO_PRIOR:
            q = None
            multiplier = Fraction(1)
            prior_id = None
        else:
            entry = prior_by_feature.get(base.candidate.feature_key)
            if entry is None:
                raise V073CertificateBoundaryVOIInvariantViolation(
                    "source prior lacks a target portable feature"
                )
            q = entry.q
            multiplier = Fraction(1, 2) + Fraction(3, 2) * q
            assert source_prior is not None
            prior_id = source_prior.prior_id
        arm_scores.append(
            DevelopmentVOIArmScoreV1(
                arm=arm,
                base_voi_id=base.base_voi_id,
                candidate_id=base.candidate.candidate_id,
                feature_key=base.candidate.feature_key,
                base_voi_per_draw=base.base_voi_per_draw,
                multiplier=multiplier,
                score=base.base_voi_per_draw * multiplier,
                source_q=q,
                source_prior_id=prior_id,
            )
        )
    score_tuple = tuple(
        sorted(arm_scores, key=lambda item: item.arm_score_id)
    )
    base_by_id = {item.base_voi_id: item for item in base_vois}
    candidate_by_id = {
        item.candidate.candidate_id: item.candidate for item in base_vois
    }
    ordered_scores = tuple(
        sorted(
            score_tuple,
            key=lambda item: (
                -item.score,
                -item.base_voi_per_draw,
                next_block_size,
                -candidate_by_id[item.candidate_id].remaining_horizon,
                item.candidate_id,
            ),
        )
    )
    schedule = DevelopmentVOIScheduleV1(
        arm=arm,
        ordered_arm_score_ids=tuple(
            sorted(item.arm_score_id for item in ordered_scores)
        ),
        ordered_candidate_ids=tuple(
            item.candidate_id for item in ordered_scores
        ),
        selected_candidate_id=ordered_scores[0].candidate_id,
    )
    if schedule.selected_candidate_id not in {
        item.candidate.candidate_id for item in base_by_id.values()
    }:
        raise V073CertificateBoundaryVOIInvariantViolation(
            "schedule selected an unknown base VOI candidate"
        )
    return DevelopmentCertificateBoundaryVOIResultV1(
        arm=arm,
        context_id=model.context_id,
        model_id=model.model_id,
        threshold_profile_id=threshold.threshold_profile_id,
        failed_audit_id=failed_audit.audit_id,
        proof_dag_id=proof_dag.dag_id,
        row_evidence_ids=tuple(
            sorted(item.evidence_id for item in row_evidence)
        ),
        base_vois=base_vois,
        arm_scores=score_tuple,
        schedule=schedule,
        source_prior_id=(
            None if source_prior is None else source_prior.prior_id
        ),
        next_block_size=next_block_size,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentVOIOpportunityControlV1:
    """Source-disjoint development fixture; never a target-savings result."""

    source_trials: tuple[DevelopmentSourceVOITrialV1, ...]
    source_prior: DevelopmentSourceVOIPriorV1
    target_model: robust.PartialSupportIntervalModelV1
    threshold: robust.RobustThresholdProfileV1
    failed_audit: robust.RobustPlanAuditV1
    proof_dag: DevelopmentFailedProofDAGV1
    row_evidence: tuple[CurrentRowCountEvidenceV1, ...]
    no_prior_result: DevelopmentCertificateBoundaryVOIResultV1
    source_result: DevelopmentCertificateBoundaryVOIResultV1
    next_block_size: int
    registered_execution_allowed: bool = False
    registered_target_evidence: bool = False
    sample_saving_claimed: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        if (
            type(self.source_trials) is not tuple
            or any(
                type(item) is not DevelopmentSourceVOITrialV1
                for item in self.source_trials
            )
            or type(self.source_prior) is not DevelopmentSourceVOIPriorV1
            or type(self.target_model)
            is not robust.PartialSupportIntervalModelV1
            or type(self.threshold) is not robust.RobustThresholdProfileV1
            or type(self.failed_audit) is not robust.RobustPlanAuditV1
            or type(self.proof_dag) is not DevelopmentFailedProofDAGV1
            or type(self.row_evidence) is not tuple
            or any(
                type(item) is not CurrentRowCountEvidenceV1
                for item in self.row_evidence
            )
            or type(self.no_prior_result)
            is not DevelopmentCertificateBoundaryVOIResultV1
            or type(self.source_result)
            is not DevelopmentCertificateBoundaryVOIResultV1
            or self.no_prior_result.arm is not DevelopmentVOIArmV1.NO_PRIOR
            or self.source_result.arm
            is not DevelopmentVOIArmV1.SOURCE_META_PRIOR
            or self.no_prior_result.base_vois
            != self.source_result.base_vois
            or self.no_prior_result.schedule.selected_candidate_id
            == self.source_result.schedule.selected_candidate_id
            or self.registered_execution_allowed is not False
            or self.registered_target_evidence is not False
            or self.sample_saving_claimed is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "development opportunity control is incomplete or overclaims"
            )
        source_contexts = set(self.source_prior.source_context_ids)
        if self.target_model.context_id in source_contexts:
            raise V073CertificateBoundaryVOIInvariantViolation(
                "development source and target contexts overlap"
            )
        base_by_candidate = {
            item.candidate.candidate_id: item
            for item in self.no_prior_result.base_vois
        }
        no_prior_selected = base_by_candidate[
            self.no_prior_result.schedule.selected_candidate_id
        ]
        source_selected = base_by_candidate[
            self.source_result.schedule.selected_candidate_id
        ]
        if (
            no_prior_selected.certifying_fantasy_probability
            == source_selected.certifying_fantasy_probability
            or max(
                item.certifying_fantasy_probability
                for item in base_by_candidate.values()
            )
            <= 0
        ):
            raise V073CertificateBoundaryVOIInvariantViolation(
                "fixture lacks distinct one-block stopping opportunities"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v073_development_voi_opportunity_control.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_trial_ids": [
                item.trial_id for item in self.source_trials
            ],
            "source_prior_id": self.source_prior.prior_id,
            "target_context_id": self.target_model.context_id,
            "target_model_id": self.target_model.model_id,
            "threshold_profile_id": self.threshold.threshold_profile_id,
            "failed_audit_id": self.failed_audit.audit_id,
            "proof_dag_id": self.proof_dag.dag_id,
            "row_evidence_ids": [
                item.evidence_id for item in self.row_evidence
            ],
            "no_prior_result_id": self.no_prior_result.result_id,
            "source_result_id": self.source_result.result_id,
            "next_block_size": self.next_block_size,
            "selected_candidates_differ": True,
            "one_block_stopping_opportunity_differs": True,
            "registered_execution_allowed": False,
            "registered_target_evidence": False,
            "sample_saving_claimed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def control_id(self) -> str:
        return _content_id("control", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def build_development_voi_opportunity_control_v1(
) -> DevelopmentVOIOpportunityControlV1:
    """Build the deterministic source-disjoint two-candidate control."""

    target_context_id = _atom("v073-target-context")
    root_state_id = _atom("v073-target-root-state")
    child_state_id = _atom("v073-target-child-state")
    root_action_id = _atom("v073-target-root-action")
    child_action_id = _atom("v073-target-child-action")
    root_action_key = _atom("v073-target-root-action-key")
    child_action_key = _atom("v073-target-child-action-key")
    root_state_key = _atom("v073-target-root-state-key")
    child_state_key = _atom("v073-target-child-state-key")
    active_destination_id = _atom("v073-target-active-child-destination")
    success_destination_id = _atom("v073-target-success-destination")
    other_destination_id = _atom("v073-target-other-destination")

    root_catalogue = robust.StateActionCatalogueV1(
        root_state_id,
        root_state_key,
        (robust.CatalogueActionV1(root_action_id, root_action_key),),
    )
    child_catalogue = robust.StateActionCatalogueV1(
        child_state_id,
        child_state_key,
        (robust.CatalogueActionV1(child_action_id, child_action_key),),
    )
    destinations = (
        robust.RegisteredDestinationV1(
            active_destination_id,
            robust.DestinationCategory.ACTIVE_STATE,
            child_state_id,
        ),
        robust.RegisteredDestinationV1(
            success_destination_id,
            robust.DestinationCategory.SUCCESS_TERMINAL,
        ),
        robust.RegisteredDestinationV1(
            other_destination_id,
            robust.DestinationCategory.OTHER,
        ),
    )
    root_row = robust.IntervalSimplexRowV1(
        root_state_id,
        2,
        root_action_id,
        Fraction(1),
        Fraction(1),
        other_destination_id,
        tuple(
            sorted(
                (
                    robust.IntervalDestinationMassV1(
                        active_destination_id,
                        Fraction(4, 5),
                        Fraction(1),
                    ),
                    robust.IntervalDestinationMassV1(
                        other_destination_id,
                        Fraction(0),
                        Fraction(1, 5),
                    ),
                ),
                key=lambda item: item.destination_id,
            )
        ),
    )
    child_row = robust.IntervalSimplexRowV1(
        child_state_id,
        1,
        child_action_id,
        Fraction(0),
        Fraction(0),
        other_destination_id,
        tuple(
            sorted(
                (
                    robust.IntervalDestinationMassV1(
                        success_destination_id,
                        Fraction(4, 5),
                        Fraction(1),
                    ),
                    robust.IntervalDestinationMassV1(
                        other_destination_id,
                        Fraction(0),
                        Fraction(1, 5),
                    ),
                ),
                key=lambda item: item.destination_id,
            )
        ),
    )
    model = robust.build_partial_support_model_v1(
        context_id=target_context_id,
        root_state_id=root_state_id,
        catalogues=(root_catalogue, child_catalogue),
        destinations=destinations,
        rows=(root_row, child_row),
    )
    threshold = robust.RobustThresholdProfileV1(
        context_id=target_context_id,
        risk_tolerance=Fraction(7, 20),
        reward_ceiling=Fraction(1),
    )
    failed_audit = robust.solve_ground_direct_robust_h2_v1(
        model,
        threshold,
    )
    proof_dag = freeze_development_failed_proof_dag_v1(
        model,
        threshold,
        failed_audit,
    )
    count_specs = {
        root_row.row_id: {
            active_destination_id: 9,
            other_destination_id: 1,
        },
        child_row.row_id: {
            success_destination_id: 8,
            other_destination_id: 2,
        },
    }
    row_evidence = []
    for row in (root_row, child_row):
        destination_ids = tuple(item.destination_id for item in row.masses)
        row_evidence.append(
            CurrentRowCountEvidenceV1(
                context_id=target_context_id,
                model_id=model.model_id,
                row_id=row.row_id,
                evidence_epoch_id=_atom(
                    f"v073-target-current-count-epoch:{row.row_id}"
                ),
                destination_ids=destination_ids,
                counts=tuple(
                    count_specs[row.row_id][destination_id]
                    for destination_id in destination_ids
                ),
                other_destination_id=other_destination_id,
            )
        )
    evidence_tuple = tuple(
        sorted(row_evidence, key=lambda item: item.evidence_id)
    )

    provenance_by_row = {
        item.row_id: item for item in failed_audit.selected_row_provenance
    }
    root_feature = _portable_feature_key(
        remaining_horizon=2,
        selected_row_category=provenance_by_row[
            root_row.row_id
        ].category,
    )
    child_feature = _portable_feature_key(
        remaining_horizon=1,
        selected_row_category=provenance_by_row[
            child_row.row_id
        ].category,
    )
    source_contexts = (
        _atom("v073-source-context-a"),
        _atom("v073-source-context-b"),
    )
    source_trials = tuple(
        sorted(
            (
                DevelopmentSourceVOITrialV1(
                    source_context_id,
                    root_feature,
                    Fraction(0),
                )
                for source_context_id in source_contexts
            ),
            key=lambda item: item.trial_id,
        )
    ) + tuple(
        sorted(
            (
                DevelopmentSourceVOITrialV1(
                    source_context_id,
                    child_feature,
                    Fraction(1),
                )
                for source_context_id in source_contexts
            ),
            key=lambda item: item.trial_id,
        )
    )
    source_trials = tuple(
        sorted(source_trials, key=lambda item: item.trial_id)
    )
    source_prior = build_development_source_voi_prior_v1(source_trials)
    next_block_size = 2
    no_prior = score_development_certificate_boundary_voi_v1(
        model=model,
        threshold=threshold,
        failed_audit=failed_audit,
        proof_dag=proof_dag,
        row_evidence=evidence_tuple,
        next_block_size=next_block_size,
        arm=DevelopmentVOIArmV1.NO_PRIOR,
    )
    source = score_development_certificate_boundary_voi_v1(
        model=model,
        threshold=threshold,
        failed_audit=failed_audit,
        proof_dag=proof_dag,
        row_evidence=evidence_tuple,
        next_block_size=next_block_size,
        arm=DevelopmentVOIArmV1.SOURCE_META_PRIOR,
        source_prior=source_prior,
    )
    return DevelopmentVOIOpportunityControlV1(
        source_trials=source_trials,
        source_prior=source_prior,
        target_model=model,
        threshold=threshold,
        failed_audit=failed_audit,
        proof_dag=proof_dag,
        row_evidence=evidence_tuple,
        no_prior_result=no_prior,
        source_result=source,
        next_block_size=next_block_size,
    )


def run_registered_v073_certificate_boundary_voi_v1(
    *_: object,
    **__: object,
) -> None:
    """Fail closed until a later final preregistration explicitly unlocks it."""

    raise RegisteredV073CertificateBoundaryVOILocked(
        "V0-073 registered target execution is locked; only the "
        "source-disjoint development control is available"
    )


__all__ = [
    "build_development_source_voi_prior_v1",
    "build_development_voi_opportunity_control_v1",
    "CurrentRowCountEvidenceV1",
    "DevelopmentCertificateBoundaryVOIResultV1",
    "DevelopmentFailedProofDAGV1",
    "DevelopmentKTFantasyV1",
    "DevelopmentSourceVOIPriorEntryV1",
    "DevelopmentSourceVOIPriorV1",
    "DevelopmentSourceVOITrialV1",
    "DevelopmentTargetOnlyBoundaryVOIV1",
    "DevelopmentVOIArmScoreV1",
    "DevelopmentVOIArmV1",
    "DevelopmentVOICandidateV1",
    "DevelopmentVOIOpportunityControlV1",
    "DevelopmentVOIScheduleV1",
    "freeze_development_failed_proof_dag_v1",
    "REGISTERED_EXECUTION_ALLOWED",
    "run_registered_v073_certificate_boundary_voi_v1",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "score_development_certificate_boundary_voi_v1",
    "V073CertificateBoundaryVOIInvariantViolation",
]
