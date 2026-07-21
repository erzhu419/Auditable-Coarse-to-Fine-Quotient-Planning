"""Held-out, prior-guided proposal with an exact target homomorphism audit.

V0-040 is deliberately a narrow control.  Offline source evidence and a
structural prior may propose a candidate from the already frozen V0-039 feature
grammar, but neither is an acceptance authority.  The target candidate is
accepted only after rebuilding its exact one-step state/action homomorphism;
an accepted candidate is then materialized as a reusable portable RAPM.

There is no sampling in this control.  Exact ground-kernel calls are recorded
as such and are never relabelled as interaction samples.  Query specifications,
values, policies, and J0 are not construction inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import combinations
from typing import Any, Iterable, Mapping

from acfqp.abstraction.partition import Partition
from acfqp.abstraction.quotient import QuotientModels, build_quotient_models
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.direct_feature_synthesis import (
    ACTION_FEATURE_SEMANTICS,
    STATE_FEATURE_SEMANTICS,
    DirectActionSemanticAdapterV1,
    DirectHomomorphismCandidateV1,
    DirectHomomorphismWitnessV1,
    DirectPredicateTreeV1,
    DirectSynthesisInvariantViolation,
    _compile_state_tree,
    _coverage_id,
    _partition_id,
    _portable,
    _singleton,
    _state_feature_rows,
    _states,
    _structural_id,
    _validate_feature_implementation_authority,
    _validate_quotient_graph,
    _validate_partition_graph,
    _validate_portable_graph,
    _verify_candidate_obligations,
    direct_action_feature_registry_v1,
    direct_state_feature_registry_v1,
)
from acfqp.domains.matching_buffer import LMBKernel, LMBState, LMBStatus
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.portable import PortableBuildResult


HYPOTHESIS_SCHEMA = "acfqp.feature_subset_hypothesis@v1"
SOURCE_EVIDENCE_SCHEMA = "acfqp.source_candidate_evidence@v1"
PRIOR_SCHEMA = "acfqp.structural_hypothesis_prior@v1"
PROPOSAL_SCHEMA = "acfqp.heldout_target_proposal@v1"
TARGET_AUDIT_SCHEMA = "acfqp.exact_target_candidate_audit@v1"
ACCOUNTING_SCHEMA = "acfqp.prior_guided_discovery_accounting@v1"
CERTIFICATE_SCHEMA = "acfqp.prior_guided_exact_certificate@v1"
RESULT_SCHEMA = "acfqp.prior_guided_discovery_result@v1"

HYPOTHESIS_DOMAIN = "acfqp:feature-subset-hypothesis:v1"
CATALOGUE_DOMAIN = "acfqp:feature-subset-hypothesis-catalogue:v1"
SOURCE_EVIDENCE_DOMAIN = "acfqp:source-candidate-evidence:v1"
PRIOR_DOMAIN = "acfqp:structural-hypothesis-prior:v1"
PROPOSAL_DOMAIN = "acfqp:heldout-target-proposal:v1"
TARGET_AUDIT_DOMAIN = "acfqp:exact-target-candidate-audit:v1"
CERTIFICATE_DOMAIN = "acfqp:prior-guided-exact-certificate:v1"
RESULT_DOMAIN = "acfqp:prior-guided-discovery-result:v1"

STRUCTURAL_FAMILY = "lmb_registered_state_action_feature_subsets_v1"
TARGET_ACCEPTANCE_AUTHORITY = "exact_target_ground_homomorphism_audit_v1"
EXACT_ACQUISITION_KIND = "EXACT_KERNEL_QUERY"
PRODUCTION_PRIOR_PROFILE = "source_unanimous_exact_v1"
CONTROL_PRIOR_PROFILE = "nonproduction_external_control_v1"
FALLBACK_CODE = "GROUND_DISCOVERY_OR_DIRECT_OPTIMIZATION_REQUIRED"
FORBIDDEN_TARGET_CHANNELS = (
    "J0",
    "Q_values",
    "QuerySpec",
    "ground_policy",
    "target_behavioral_signature",
    "value_function",
)
CLAIM_SCOPE = (
    "one source-unanimous exact candidate from the fixed V0-039 feature grammar was "
    "accepted by an exact held-out target homomorphism audit and materialized "
    "as a reusable portable RAPM; broad-support mass is metadata rather than an executed search schedule; no minimality, feature-invention, sampled-"
    "dynamics, sample-efficiency, or official-Gate claim"
)


class PriorGuidedDiscoveryInvariantViolation(ValueError):
    """A V0-040 authority, identity, or exact-audit invariant was violated."""


class PriorGuidedDiscoveryStatus(str, Enum):
    EXACT_HELDOUT_HOMOMORPHISM = "EXACT_HELDOUT_HOMOMORPHISM"
    PRIOR_MISMATCH_FALLBACK_REQUIRED = "PRIOR_MISMATCH_FALLBACK_REQUIRED"


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _exact(document: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != keys:
        raise PriorGuidedDiscoveryInvariantViolation(
            f"{label} must contain exactly {tuple(sorted(keys))!r}"
        )
    return document


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise PriorGuidedDiscoveryInvariantViolation(f"{label} must be nonempty text")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise PriorGuidedDiscoveryInvariantViolation(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PriorGuidedDiscoveryInvariantViolation(
            f"{label} must be a full lowercase SHA-256"
        )
    return value


def _fraction_doc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value: Any, label: str) -> Fraction:
    record = _exact(value, {"numerator", "denominator"}, label)
    if type(record["numerator"]) is not int:
        raise PriorGuidedDiscoveryInvariantViolation(
            f"{label}.numerator must be integer"
        )
    denominator = _integer(record["denominator"], f"{label}.denominator", 1)
    result = Fraction(record["numerator"], denominator)
    if record != _fraction_doc(result):
        raise PriorGuidedDiscoveryInvariantViolation(f"{label} must be reduced")
    return result


def _subsets(names: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        subset
        for size in range(len(names) + 1)
        for subset in combinations(names, size)
    )


@dataclass(frozen=True, order=True, slots=True)
class FeatureSubsetHypothesisV1:
    state_features: tuple[str, ...]
    action_features: tuple[str, ...]
    schema: str = HYPOTHESIS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != HYPOTHESIS_SCHEMA:
            raise PriorGuidedDiscoveryInvariantViolation("hypothesis schema substitution")
        if type(self.state_features) is not tuple or type(self.action_features) is not tuple:
            raise PriorGuidedDiscoveryInvariantViolation(
                "hypothesis feature subsets require exact tuple types"
            )
        if tuple(sorted(set(self.state_features))) != self.state_features:
            raise PriorGuidedDiscoveryInvariantViolation(
                "state hypothesis features must be unique and sorted"
            )
        if tuple(sorted(set(self.action_features))) != self.action_features:
            raise PriorGuidedDiscoveryInvariantViolation(
                "action hypothesis features must be unique and sorted"
            )
        if not set(self.state_features) <= set(STATE_FEATURE_SEMANTICS):
            raise PriorGuidedDiscoveryInvariantViolation("unknown state hypothesis feature")
        if not set(self.action_features) <= set(ACTION_FEATURE_SEMANTICS):
            raise PriorGuidedDiscoveryInvariantViolation("unknown action hypothesis feature")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "state_features": list(self.state_features),
            "action_features": list(self.action_features),
        }

    @property
    def hypothesis_id(self) -> str:
        return _content_id(HYPOTHESIS_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "hypothesis_id": self.hypothesis_id}

    @classmethod
    def from_document(cls, document: Any) -> "FeatureSubsetHypothesisV1":
        record = _exact(
            document,
            {"schema", "state_features", "action_features", "hypothesis_id"},
            "feature-subset hypothesis",
        )
        if type(record["state_features"]) is not list or type(record["action_features"]) is not list:
            raise PriorGuidedDiscoveryInvariantViolation(
                "hypothesis feature subsets must be lists"
            )
        result = cls(
            tuple(record["state_features"]),
            tuple(record["action_features"]),
            record["schema"],
        )
        if record["hypothesis_id"] != result.hypothesis_id or record != result.to_document():
            raise PriorGuidedDiscoveryInvariantViolation(
                "hypothesis ID/document mismatch"
            )
        return result


def feature_subset_hypothesis_v1(
    state_features: Iterable[str], action_features: Iterable[str]
) -> FeatureSubsetHypothesisV1:
    return FeatureSubsetHypothesisV1(
        tuple(sorted(set(state_features))), tuple(sorted(set(action_features)))
    )


def _catalogue() -> tuple[FeatureSubsetHypothesisV1, ...]:
    state_names = tuple(sorted(STATE_FEATURE_SEMANTICS))
    action_names = tuple(sorted(ACTION_FEATURE_SEMANTICS))
    return tuple(
        FeatureSubsetHypothesisV1(state_subset, action_subset)
        for state_subset in _subsets(state_names)
        for action_subset in _subsets(action_names)
    )


def _catalogue_id() -> str:
    return _content_id(
        CATALOGUE_DOMAIN,
        {
            "structural_family": STRUCTURAL_FAMILY,
            "state_registry_id": direct_state_feature_registry_v1().registry_id,
            "action_registry_id": direct_action_feature_registry_v1().registry_id,
            "hypothesis_ids": [item.hypothesis_id for item in _catalogue()],
        },
    )


@dataclass(frozen=True, slots=True)
class SourceOfflineAccountingV1:
    interaction_samples: int
    exact_ground_kernel_calls: int
    unique_ground_state_action_rows: int
    eligible_ground_state_action_rows: int
    candidate_hypothesis_evaluations: int = 1

    def __post_init__(self) -> None:
        if self.interaction_samples != 0:
            raise PriorGuidedDiscoveryInvariantViolation(
                "exact source audits have zero interaction samples"
            )
        _integer(self.exact_ground_kernel_calls, "source exact ground-kernel calls")
        _integer(self.unique_ground_state_action_rows, "source unique ground rows")
        _integer(self.eligible_ground_state_action_rows, "source eligible ground rows")
        if self.unique_ground_state_action_rows > self.eligible_ground_state_action_rows:
            raise PriorGuidedDiscoveryInvariantViolation("source actual rows exceed eligible rows")
        if self.candidate_hypothesis_evaluations != 1:
            raise PriorGuidedDiscoveryInvariantViolation(
                "each source evidence audits exactly one hypothesis"
            )

    def to_document(self) -> dict[str, int]:
        return {
            "interaction_samples": self.interaction_samples,
            "exact_ground_kernel_calls": self.exact_ground_kernel_calls,
            "unique_ground_state_action_rows": self.unique_ground_state_action_rows,
            "eligible_ground_state_action_rows": self.eligible_ground_state_action_rows,
            "candidate_hypothesis_evaluations": self.candidate_hypothesis_evaluations,
        }

    @classmethod
    def from_document(cls, document: Any) -> "SourceOfflineAccountingV1":
        return cls(
            **_exact(
                document,
                {
                    "interaction_samples",
                    "exact_ground_kernel_calls",
                    "unique_ground_state_action_rows",
                    "eligible_ground_state_action_rows",
                    "candidate_hypothesis_evaluations",
                },
                "source accounting",
            )
        )


@dataclass(frozen=True, slots=True)
class SourceCandidateEvidenceV1:
    source_task_id: str
    structural_id: str
    source_coverage_id: str
    hypothesis: FeatureSubsetHypothesisV1
    candidate: DirectHomomorphismCandidateV1
    witness: DirectHomomorphismWitnessV1 | None
    accounting: SourceOfflineAccountingV1
    schema: str = SOURCE_EVIDENCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SOURCE_EVIDENCE_SCHEMA:
            raise PriorGuidedDiscoveryInvariantViolation("source evidence schema substitution")
        _text(self.source_task_id, "source task ID")
        _sha(self.structural_id, "source structural ID")
        _sha(self.source_coverage_id, "source coverage ID")
        if type(self.hypothesis) is not FeatureSubsetHypothesisV1:
            raise PriorGuidedDiscoveryInvariantViolation("source hypothesis requires exact type")
        if type(self.candidate) is not DirectHomomorphismCandidateV1:
            raise PriorGuidedDiscoveryInvariantViolation("source candidate requires exact type")
        if self.witness is not None and type(self.witness) is not DirectHomomorphismWitnessV1:
            raise PriorGuidedDiscoveryInvariantViolation("source witness requires exact type")
        if type(self.accounting) is not SourceOfflineAccountingV1:
            raise PriorGuidedDiscoveryInvariantViolation("source accounting requires exact type")
        if (
            self.candidate.selected_state_features != self.hypothesis.state_features
            or self.candidate.selected_action_features != self.hypothesis.action_features
        ):
            raise PriorGuidedDiscoveryInvariantViolation(
                "source candidate does not implement its hypothesis"
            )
        expected_witness = None if self.witness is None else self.witness.witness_id
        if self.candidate.witness_id != expected_witness:
            raise PriorGuidedDiscoveryInvariantViolation("source witness binding mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_task_id": self.source_task_id,
            "structural_id": self.structural_id,
            "source_coverage_id": self.source_coverage_id,
            "hypothesis": self.hypothesis.to_document(),
            "candidate": self.candidate.to_document(),
            "witness": None if self.witness is None else self.witness.to_document(),
            "accounting": self.accounting.to_document(),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id(SOURCE_EVIDENCE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}

    @classmethod
    def from_document(cls, document: Any) -> "SourceCandidateEvidenceV1":
        record = _exact(
            document,
            {
                "schema",
                "source_task_id",
                "structural_id",
                "source_coverage_id",
                "hypothesis",
                "candidate",
                "witness",
                "accounting",
                "evidence_id",
            },
            "source candidate evidence",
        )
        result = cls(
            record["source_task_id"],
            record["structural_id"],
            record["source_coverage_id"],
            FeatureSubsetHypothesisV1.from_document(record["hypothesis"]),
            DirectHomomorphismCandidateV1.from_document(record["candidate"]),
            None
            if record["witness"] is None
            else DirectHomomorphismWitnessV1.from_document(record["witness"]),
            SourceOfflineAccountingV1.from_document(record["accounting"]),
            record["schema"],
        )
        if record["evidence_id"] != result.evidence_id or record != result.to_document():
            raise PriorGuidedDiscoveryInvariantViolation(
                "source evidence ID/document mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class StructuralHypothesisPriorV1:
    source_task_ids: tuple[str, ...]
    source_evidence_ids: tuple[str, ...]
    source_coverage_ids: tuple[str, ...]
    profile: str
    preferred_hypothesis: FeatureSubsetHypothesisV1
    wide_tail_base_mass: Fraction
    catalogue_id: str = ""
    catalogue_size: int = 4096
    structural_family: str = STRUCTURAL_FAMILY
    state_registry_id: str = ""
    action_registry_id: str = ""
    broad_support_metadata_only: bool = True
    executed_candidate_schedule: bool = False
    schema: str = PRIOR_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PRIOR_SCHEMA or self.structural_family != STRUCTURAL_FAMILY:
            raise PriorGuidedDiscoveryInvariantViolation("structural-prior profile substitution")
        if type(self.source_task_ids) is not tuple or type(self.source_evidence_ids) is not tuple or type(self.source_coverage_ids) is not tuple:
            raise PriorGuidedDiscoveryInvariantViolation("prior source identities require tuples")
        if not self.source_task_ids or len(self.source_task_ids) != len(self.source_evidence_ids) or len(self.source_task_ids) != len(self.source_coverage_ids):
            raise PriorGuidedDiscoveryInvariantViolation("prior requires paired source evidence")
        if tuple(sorted(self.source_task_ids)) != self.source_task_ids:
            raise PriorGuidedDiscoveryInvariantViolation("prior source task IDs must be sorted")
        if len(set(self.source_task_ids)) != len(self.source_task_ids):
            raise PriorGuidedDiscoveryInvariantViolation("prior source task IDs must be unique")
        if len(set(self.source_evidence_ids)) != len(self.source_evidence_ids):
            raise PriorGuidedDiscoveryInvariantViolation("prior source evidence IDs must be unique")
        if len(set(self.source_coverage_ids)) != len(self.source_coverage_ids):
            raise PriorGuidedDiscoveryInvariantViolation("prior source coverage IDs must be unique")
        for task_id in self.source_task_ids:
            _text(task_id, "prior source task ID")
        for evidence_id in self.source_evidence_ids:
            _sha(evidence_id, "prior source evidence ID")
        for coverage_id in self.source_coverage_ids:
            _sha(coverage_id, "prior source coverage ID")
        if self.profile not in {PRODUCTION_PRIOR_PROFILE, CONTROL_PRIOR_PROFILE}:
            raise PriorGuidedDiscoveryInvariantViolation("prior profile substitution")
        if type(self.preferred_hypothesis) is not FeatureSubsetHypothesisV1:
            raise PriorGuidedDiscoveryInvariantViolation("preferred hypothesis requires exact type")
        if type(self.wide_tail_base_mass) is not Fraction or not (
            Fraction(0) < self.wide_tail_base_mass < Fraction(1)
        ):
            raise PriorGuidedDiscoveryInvariantViolation(
                "wide-tail base mixture must be a nonzero proper Fraction"
            )
        if self.catalogue_id != _catalogue_id() or self.catalogue_size != len(_catalogue()):
            raise PriorGuidedDiscoveryInvariantViolation("prior catalogue substitution")
        if self.state_registry_id != direct_state_feature_registry_v1().registry_id:
            raise PriorGuidedDiscoveryInvariantViolation("prior state-registry substitution")
        if self.action_registry_id != direct_action_feature_registry_v1().registry_id:
            raise PriorGuidedDiscoveryInvariantViolation("prior action-registry substitution")
        if self.broad_support_metadata_only is not True or self.executed_candidate_schedule is not False:
            raise PriorGuidedDiscoveryInvariantViolation("wide-tail broad support is metadata, not an executed candidate schedule")

    @property
    def structural_prior_mass(self) -> Fraction:
        return Fraction(1) - self.wide_tail_base_mass

    @property
    def preferred_total_mass(self) -> Fraction:
        return self.structural_prior_mass + self.wide_tail_base_mass / self.catalogue_size

    @property
    def tail_hypothesis_mass(self) -> Fraction:
        return self.wide_tail_base_mass / self.catalogue_size

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_task_ids": list(self.source_task_ids),
            "source_evidence_ids": list(self.source_evidence_ids),
            "source_coverage_ids": list(self.source_coverage_ids),
            "profile": self.profile,
            "preferred_hypothesis": self.preferred_hypothesis.to_document(),
            "wide_tail_base_mass": _fraction_doc(self.wide_tail_base_mass),
            "structural_prior_mass": _fraction_doc(self.structural_prior_mass),
            "preferred_total_mass": _fraction_doc(self.preferred_total_mass),
            "tail_hypothesis_mass": _fraction_doc(self.tail_hypothesis_mass),
            "catalogue_id": self.catalogue_id,
            "catalogue_size": self.catalogue_size,
            "structural_family": self.structural_family,
            "state_registry_id": self.state_registry_id,
            "action_registry_id": self.action_registry_id,
            "broad_support_metadata_only": self.broad_support_metadata_only,
            "executed_candidate_schedule": self.executed_candidate_schedule,
        }

    @property
    def prior_id(self) -> str:
        return _content_id(PRIOR_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prior_id": self.prior_id}

    @classmethod
    def from_document(cls, document: Any) -> "StructuralHypothesisPriorV1":
        keys = {
            "schema",
            "source_task_ids",
            "source_evidence_ids",
            "source_coverage_ids",
            "profile",
            "preferred_hypothesis",
            "wide_tail_base_mass",
            "structural_prior_mass",
            "preferred_total_mass",
            "tail_hypothesis_mass",
            "catalogue_id",
            "catalogue_size",
            "structural_family",
            "state_registry_id",
            "action_registry_id",
            "broad_support_metadata_only",
            "executed_candidate_schedule",
            "prior_id",
        }
        record = _exact(document, keys, "structural hypothesis prior")
        if type(record["source_task_ids"]) is not list or type(record["source_evidence_ids"]) is not list or type(record["source_coverage_ids"]) is not list:
            raise PriorGuidedDiscoveryInvariantViolation("prior source IDs must be lists")
        result = cls(
            tuple(record["source_task_ids"]),
            tuple(record["source_evidence_ids"]),
            tuple(record["source_coverage_ids"]),
            record["profile"],
            FeatureSubsetHypothesisV1.from_document(record["preferred_hypothesis"]),
            _fraction(record["wide_tail_base_mass"], "wide-tail base mass"),
            record["catalogue_id"],
            record["catalogue_size"],
            record["structural_family"],
            record["state_registry_id"],
            record["action_registry_id"],
            record["broad_support_metadata_only"],
            record["executed_candidate_schedule"],
            record["schema"],
        )
        if (
            record["structural_prior_mass"] != _fraction_doc(result.structural_prior_mass)
            or record["preferred_total_mass"] != _fraction_doc(result.preferred_total_mass)
            or record["tail_hypothesis_mass"] != _fraction_doc(result.tail_hypothesis_mass)
            or record["prior_id"] != result.prior_id
            or record != result.to_document()
        ):
            raise PriorGuidedDiscoveryInvariantViolation("prior ID/document mismatch")
        return result


def build_structural_hypothesis_prior_v1(
    source_evidences: tuple[SourceCandidateEvidenceV1, ...],
    *,
    wide_tail_base_mass: Fraction = Fraction(1, 10),
) -> StructuralHypothesisPriorV1:
    """Build the production prior from unanimous exact source evidence."""

    ordered = _validated_source_evidences(source_evidences)
    hypotheses = {item.hypothesis for item in ordered}
    if any(not item.candidate.exact_homomorphism for item in ordered) or len(hypotheses) != 1:
        raise PriorGuidedDiscoveryInvariantViolation(
            "production prior requires unanimous exact source evidence"
        )
    return _build_prior(
        ordered,
        preferred_hypothesis=next(iter(hypotheses)),
        wide_tail_base_mass=wide_tail_base_mass,
        profile=PRODUCTION_PRIOR_PROFILE,
    )


def build_external_control_structural_prior_v1(
    source_evidences: tuple[SourceCandidateEvidenceV1, ...],
    *,
    preferred_hypothesis: FeatureSubsetHypothesisV1,
    wide_tail_base_mass: Fraction = Fraction(1, 10),
) -> StructuralHypothesisPriorV1:
    """Build explicit nonproduction provenance for prior-mismatch controls."""

    return _build_prior(
        _validated_source_evidences(source_evidences),
        preferred_hypothesis=preferred_hypothesis,
        wide_tail_base_mass=wide_tail_base_mass,
        profile=CONTROL_PRIOR_PROFILE,
    )


def _validated_source_evidences(
    source_evidences: tuple[SourceCandidateEvidenceV1, ...],
) -> tuple[SourceCandidateEvidenceV1, ...]:
    if type(source_evidences) is not tuple or any(
        type(item) is not SourceCandidateEvidenceV1 for item in source_evidences
    ):
        raise PriorGuidedDiscoveryInvariantViolation(
            "prior builder requires exact source-evidence tuple/types"
        )
    ordered = tuple(sorted(source_evidences, key=lambda item: item.source_task_id))
    if not ordered:
        raise PriorGuidedDiscoveryInvariantViolation("prior requires source evidence")
    if len({item.source_task_id for item in ordered}) != len(ordered):
        raise PriorGuidedDiscoveryInvariantViolation("source task IDs must be unique")
    if len({item.source_coverage_id for item in ordered}) != len(ordered):
        raise PriorGuidedDiscoveryInvariantViolation("source coverage IDs must be unique")
    return ordered


def _build_prior(
    ordered: tuple[SourceCandidateEvidenceV1, ...],
    *,
    preferred_hypothesis: FeatureSubsetHypothesisV1,
    wide_tail_base_mass: Fraction,
    profile: str,
) -> StructuralHypothesisPriorV1:
    if type(preferred_hypothesis) is not FeatureSubsetHypothesisV1:
        raise PriorGuidedDiscoveryInvariantViolation("prior rejects duck hypotheses")
    return StructuralHypothesisPriorV1(
        tuple(item.source_task_id for item in ordered),
        tuple(item.evidence_id for item in ordered),
        tuple(item.source_coverage_id for item in ordered),
        profile,
        preferred_hypothesis,
        Fraction(wide_tail_base_mass),
        _catalogue_id(),
        len(_catalogue()),
        STRUCTURAL_FAMILY,
        direct_state_feature_registry_v1().registry_id,
        direct_action_feature_registry_v1().registry_id,
    )


@dataclass(frozen=True, slots=True)
class HeldOutTargetProposalV1:
    target_task_id: str
    target_structural_id: str
    target_coverage_id: str
    prior_id: str
    hypothesis: FeatureSubsetHypothesisV1
    target_task_absent_from_sources: bool = True
    target_coverage_absent_from_sources: bool = True
    proposal_is_acceptance_authority: bool = False
    forbidden_target_channels: tuple[str, ...] = FORBIDDEN_TARGET_CHANNELS
    schema: str = PROPOSAL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROPOSAL_SCHEMA:
            raise PriorGuidedDiscoveryInvariantViolation("proposal schema substitution")
        _text(self.target_task_id, "target task ID")
        _sha(self.target_structural_id, "target structural ID")
        _sha(self.target_coverage_id, "target coverage ID")
        _sha(self.prior_id, "proposal prior ID")
        if type(self.hypothesis) is not FeatureSubsetHypothesisV1:
            raise PriorGuidedDiscoveryInvariantViolation("proposal hypothesis requires exact type")
        if self.target_task_absent_from_sources is not True or self.target_coverage_absent_from_sources is not True:
            raise PriorGuidedDiscoveryInvariantViolation("target task and coverage holdout were not enforced")
        if self.proposal_is_acceptance_authority is not False:
            raise PriorGuidedDiscoveryInvariantViolation("a prior proposal cannot accept itself")
        if self.forbidden_target_channels != FORBIDDEN_TARGET_CHANNELS:
            raise PriorGuidedDiscoveryInvariantViolation("target-channel contract substitution")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "target_task_id": self.target_task_id,
            "target_structural_id": self.target_structural_id,
            "target_coverage_id": self.target_coverage_id,
            "prior_id": self.prior_id,
            "hypothesis": self.hypothesis.to_document(),
            "target_task_absent_from_sources": self.target_task_absent_from_sources,
            "target_coverage_absent_from_sources": self.target_coverage_absent_from_sources,
            "proposal_is_acceptance_authority": self.proposal_is_acceptance_authority,
            "forbidden_target_channels": list(self.forbidden_target_channels),
        }

    @property
    def proposal_id(self) -> str:
        return _content_id(PROPOSAL_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}

    @classmethod
    def from_document(cls, document: Any) -> "HeldOutTargetProposalV1":
        record = _exact(
            document,
            {
                "schema",
                "target_task_id",
                "target_structural_id",
                "target_coverage_id",
                "prior_id",
                "hypothesis",
                "target_task_absent_from_sources",
                "target_coverage_absent_from_sources",
                "proposal_is_acceptance_authority",
                "forbidden_target_channels",
                "proposal_id",
            },
            "held-out target proposal",
        )
        if type(record["forbidden_target_channels"]) is not list:
            raise PriorGuidedDiscoveryInvariantViolation("proposal channels must be a list")
        result = cls(
            record["target_task_id"],
            record["target_structural_id"],
            record["target_coverage_id"],
            record["prior_id"],
            FeatureSubsetHypothesisV1.from_document(record["hypothesis"]),
            record["target_task_absent_from_sources"],
            record["target_coverage_absent_from_sources"],
            record["proposal_is_acceptance_authority"],
            tuple(record["forbidden_target_channels"]),
            record["schema"],
        )
        if record["proposal_id"] != result.proposal_id or record != result.to_document():
            raise PriorGuidedDiscoveryInvariantViolation("proposal ID/document mismatch")
        return result


@dataclass(frozen=True, slots=True)
class ExactTargetCandidateAuditV1:
    target_task_id: str
    structural_id: str
    target_coverage_id: str
    prior_id: str
    proposal_id: str
    hypothesis: FeatureSubsetHypothesisV1
    candidate: DirectHomomorphismCandidateV1
    witness: DirectHomomorphismWitnessV1 | None
    interaction_samples: int
    exact_ground_kernel_calls: int
    unique_ground_state_action_rows: int
    eligible_ground_state_action_rows: int
    candidate_hypothesis_evaluations: int = 1
    acquisition_kind: str = EXACT_ACQUISITION_KIND
    outcomes_counted_as_interaction_samples: bool = False
    acceptance_authority: str = TARGET_ACCEPTANCE_AUTHORITY
    schema: str = TARGET_AUDIT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != TARGET_AUDIT_SCHEMA or self.acceptance_authority != TARGET_ACCEPTANCE_AUTHORITY:
            raise PriorGuidedDiscoveryInvariantViolation("target audit authority substitution")
        _text(self.target_task_id, "audit target task ID")
        for value, label in (
            (self.structural_id, "audit structural ID"),
            (self.target_coverage_id, "audit coverage ID"),
            (self.prior_id, "audit prior ID"),
            (self.proposal_id, "audit proposal ID"),
        ):
            _sha(value, label)
        if type(self.hypothesis) is not FeatureSubsetHypothesisV1 or type(self.candidate) is not DirectHomomorphismCandidateV1:
            raise PriorGuidedDiscoveryInvariantViolation("target audit requires exact hypothesis/candidate types")
        if self.witness is not None and type(self.witness) is not DirectHomomorphismWitnessV1:
            raise PriorGuidedDiscoveryInvariantViolation("target audit witness requires exact type")
        if self.candidate.selected_state_features != self.hypothesis.state_features or self.candidate.selected_action_features != self.hypothesis.action_features:
            raise PriorGuidedDiscoveryInvariantViolation("target candidate/hypothesis mismatch")
        if self.candidate.witness_id != (None if self.witness is None else self.witness.witness_id):
            raise PriorGuidedDiscoveryInvariantViolation("target witness binding mismatch")
        if self.interaction_samples != 0:
            raise PriorGuidedDiscoveryInvariantViolation("exact target audit has zero interaction samples")
        if self.acquisition_kind != EXACT_ACQUISITION_KIND or self.outcomes_counted_as_interaction_samples is not False:
            raise PriorGuidedDiscoveryInvariantViolation("exact kernel queries and outcomes cannot be relabelled as samples")
        _integer(self.exact_ground_kernel_calls, "target exact ground-kernel calls")
        _integer(self.unique_ground_state_action_rows, "target unique ground rows")
        _integer(self.eligible_ground_state_action_rows, "target eligible ground rows")
        if self.unique_ground_state_action_rows > self.eligible_ground_state_action_rows:
            raise PriorGuidedDiscoveryInvariantViolation("target actual rows exceed eligible rows")
        if self.candidate_hypothesis_evaluations != 1:
            raise PriorGuidedDiscoveryInvariantViolation("target must audit one proposed hypothesis")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "target_task_id": self.target_task_id,
            "structural_id": self.structural_id,
            "target_coverage_id": self.target_coverage_id,
            "prior_id": self.prior_id,
            "proposal_id": self.proposal_id,
            "hypothesis": self.hypothesis.to_document(),
            "candidate": self.candidate.to_document(),
            "witness": None if self.witness is None else self.witness.to_document(),
            "interaction_samples": self.interaction_samples,
            "exact_ground_kernel_calls": self.exact_ground_kernel_calls,
            "unique_ground_state_action_rows": self.unique_ground_state_action_rows,
            "eligible_ground_state_action_rows": self.eligible_ground_state_action_rows,
            "candidate_hypothesis_evaluations": self.candidate_hypothesis_evaluations,
            "acquisition_kind": self.acquisition_kind,
            "outcomes_counted_as_interaction_samples": self.outcomes_counted_as_interaction_samples,
            "acceptance_authority": self.acceptance_authority,
        }

    @property
    def audit_id(self) -> str:
        return _content_id(TARGET_AUDIT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}

    @classmethod
    def from_document(cls, document: Any) -> "ExactTargetCandidateAuditV1":
        keys = {
            "schema",
            "target_task_id",
            "structural_id",
            "target_coverage_id",
            "prior_id",
            "proposal_id",
            "hypothesis",
            "candidate",
            "witness",
            "interaction_samples",
            "exact_ground_kernel_calls",
            "unique_ground_state_action_rows",
            "eligible_ground_state_action_rows",
            "candidate_hypothesis_evaluations",
            "acquisition_kind",
            "outcomes_counted_as_interaction_samples",
            "acceptance_authority",
            "audit_id",
        }
        record = _exact(document, keys, "exact target candidate audit")
        result = cls(
            record["target_task_id"],
            record["structural_id"],
            record["target_coverage_id"],
            record["prior_id"],
            record["proposal_id"],
            FeatureSubsetHypothesisV1.from_document(record["hypothesis"]),
            DirectHomomorphismCandidateV1.from_document(record["candidate"]),
            None
            if record["witness"] is None
            else DirectHomomorphismWitnessV1.from_document(record["witness"]),
            record["interaction_samples"],
            record["exact_ground_kernel_calls"],
            record["unique_ground_state_action_rows"],
            record["eligible_ground_state_action_rows"],
            record["candidate_hypothesis_evaluations"],
            record["acquisition_kind"],
            record["outcomes_counted_as_interaction_samples"],
            record["acceptance_authority"],
            record["schema"],
        )
        if record["audit_id"] != result.audit_id or record != result.to_document():
            raise PriorGuidedDiscoveryInvariantViolation("target audit ID/document mismatch")
        return result


@dataclass(frozen=True, slots=True)
class PriorGuidedDiscoveryAccountingV1:
    interaction_samples: int
    exact_ground_kernel_calls: int
    unique_ground_state_action_rows: int
    eligible_ground_state_action_rows: int
    candidate_hypothesis_evaluations: int
    source_task_count: int
    source_offline_interaction_samples: int
    source_offline_exact_ground_kernel_calls: int
    source_offline_unique_ground_state_action_rows: int
    source_offline_eligible_ground_state_action_rows: int
    source_offline_candidate_hypothesis_evaluations: int
    acquisition_kind: str
    outcomes_counted_as_interaction_samples: bool
    schema: str = ACCOUNTING_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != ACCOUNTING_SCHEMA:
            raise PriorGuidedDiscoveryInvariantViolation("accounting schema substitution")
        if self.interaction_samples != 0 or self.source_offline_interaction_samples != 0:
            raise PriorGuidedDiscoveryInvariantViolation("exact-control interaction samples must be zero")
        if self.acquisition_kind != EXACT_ACQUISITION_KIND or self.outcomes_counted_as_interaction_samples is not False:
            raise PriorGuidedDiscoveryInvariantViolation("exact kernel outcomes must remain separate from interaction samples")
        if self.candidate_hypothesis_evaluations != 1:
            raise PriorGuidedDiscoveryInvariantViolation("target evaluation count must equal one")
        for name in (
            "exact_ground_kernel_calls",
            "unique_ground_state_action_rows",
            "eligible_ground_state_action_rows",
            "source_task_count",
            "source_offline_exact_ground_kernel_calls",
            "source_offline_unique_ground_state_action_rows",
            "source_offline_eligible_ground_state_action_rows",
            "source_offline_candidate_hypothesis_evaluations",
        ):
            _integer(getattr(self, name), name)
        if self.unique_ground_state_action_rows > self.eligible_ground_state_action_rows or self.source_offline_unique_ground_state_action_rows > self.source_offline_eligible_ground_state_action_rows:
            raise PriorGuidedDiscoveryInvariantViolation("actual rows exceed eligible rows")
        if self.source_task_count < 1 or self.source_offline_candidate_hypothesis_evaluations != self.source_task_count:
            raise PriorGuidedDiscoveryInvariantViolation("source accounting count mismatch")

    def to_document(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }

    @classmethod
    def from_document(cls, document: Any) -> "PriorGuidedDiscoveryAccountingV1":
        return cls(**_exact(document, set(cls.__dataclass_fields__), "discovery accounting"))


@dataclass(frozen=True, slots=True)
class PriorGuidedExactCertificateV1:
    target_task_id: str
    structural_id: str
    target_coverage_id: str
    prior_id: str
    proposal_id: str
    target_audit_id: str
    hypothesis_id: str
    candidate_id: str
    predicate_tree_id: str
    partition_id: str
    portable_model_id: str
    selected_state_features: tuple[str, ...]
    selected_action_features: tuple[str, ...]
    state_thresholds: tuple[Fraction, ...]
    ground_state_count: int
    active_ground_state_count: int
    quotient_cell_count: int
    active_quotient_cell_count: int
    abstract_entry_count: int
    prior_profile: str
    envelope_is_singleton: bool = True
    exact_homomorphism_verified: bool = True
    global_minimality_verified: bool = False
    target_exact_audit_is_sole_acceptance_authority: bool = True
    reusable_portable_rapm: bool = True
    minimality_claim: bool = False
    feature_invention_claim: bool = False
    sampled_dynamics_claim: bool = False
    sample_efficiency_claim: bool = False
    official_gate_claim: bool = False
    claim_scope: str = CLAIM_SCOPE
    schema: str = CERTIFICATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CERTIFICATE_SCHEMA or self.claim_scope != CLAIM_SCOPE:
            raise PriorGuidedDiscoveryInvariantViolation("certificate claim/profile substitution")
        _text(self.target_task_id, "certificate target task ID")
        if self.prior_profile not in {PRODUCTION_PRIOR_PROFILE, CONTROL_PRIOR_PROFILE}:
            raise PriorGuidedDiscoveryInvariantViolation("certificate prior profile substitution")
        for name in (
            "structural_id",
            "target_coverage_id",
            "prior_id",
            "proposal_id",
            "target_audit_id",
            "hypothesis_id",
            "candidate_id",
            "predicate_tree_id",
            "partition_id",
        ):
            _sha(getattr(self, name), name)
        if type(self.portable_model_id) is not str or not self.portable_model_id.startswith("rapm:"):
            raise PriorGuidedDiscoveryInvariantViolation("certificate portable model ID is invalid")
        if type(self.selected_state_features) is not tuple or type(self.selected_action_features) is not tuple or type(self.state_thresholds) is not tuple:
            raise PriorGuidedDiscoveryInvariantViolation("certificate feature fields require tuples")
        if any(type(item) is not Fraction for item in self.state_thresholds):
            raise PriorGuidedDiscoveryInvariantViolation("certificate thresholds require exact fractions")
        for name in (
            "ground_state_count",
            "active_ground_state_count",
            "quotient_cell_count",
            "active_quotient_cell_count",
            "abstract_entry_count",
        ):
            _integer(getattr(self, name), name, 1)
        if (
            self.envelope_is_singleton is not True
            or self.exact_homomorphism_verified is not True
            or self.global_minimality_verified is not False
            or self.target_exact_audit_is_sole_acceptance_authority is not True
            or self.reusable_portable_rapm is not True
            or any(
                value is not False
                for value in (
                    self.minimality_claim,
                    self.feature_invention_claim,
                    self.sampled_dynamics_claim,
                    self.sample_efficiency_claim,
                    self.official_gate_claim,
                )
            )
        ):
            raise PriorGuidedDiscoveryInvariantViolation("certificate claim flags are invalid")

    def _payload(self) -> dict[str, Any]:
        result = {name: getattr(self, name) for name in self.__dataclass_fields__}
        result["selected_state_features"] = list(self.selected_state_features)
        result["selected_action_features"] = list(self.selected_action_features)
        result["state_thresholds"] = [_fraction_doc(item) for item in self.state_thresholds]
        return result

    @property
    def certificate_id(self) -> str:
        return _content_id(CERTIFICATE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_id": self.certificate_id}

    @classmethod
    def from_document(cls, document: Any) -> "PriorGuidedExactCertificateV1":
        record = _exact(
            document,
            set(cls.__dataclass_fields__) | {"certificate_id"},
            "prior-guided exact certificate",
        )
        if type(record["selected_state_features"]) is not list or type(record["selected_action_features"]) is not list or type(record["state_thresholds"]) is not list:
            raise PriorGuidedDiscoveryInvariantViolation("certificate feature fields must be lists")
        kwargs = {name: record[name] for name in cls.__dataclass_fields__}
        kwargs["selected_state_features"] = tuple(kwargs["selected_state_features"])
        kwargs["selected_action_features"] = tuple(kwargs["selected_action_features"])
        kwargs["state_thresholds"] = tuple(
            _fraction(item, "certificate state threshold") for item in kwargs["state_thresholds"]
        )
        result = cls(**kwargs)
        if record["certificate_id"] != result.certificate_id or record != result.to_document():
            raise PriorGuidedDiscoveryInvariantViolation("certificate ID/document mismatch")
        return result


@dataclass(frozen=True, slots=True)
class PriorGuidedDiscoveryResultV1:
    status: PriorGuidedDiscoveryStatus
    source_evidences: tuple[SourceCandidateEvidenceV1, ...]
    prior: StructuralHypothesisPriorV1
    proposal: HeldOutTargetProposalV1
    target_audit: ExactTargetCandidateAuditV1
    accounting: PriorGuidedDiscoveryAccountingV1
    predicate_tree: DirectPredicateTreeV1 | None
    partition: Partition | None
    semantic_adapter: DirectActionSemanticAdapterV1 | None
    quotient_models: QuotientModels | None
    portable_build: PortableBuildResult | None
    certificate: PriorGuidedExactCertificateV1 | None
    fallback_required: bool
    fallback_code: str | None
    exact_homomorphism_verified: bool
    global_minimality_verified: bool
    infeasibility_claim: bool
    schema: str = RESULT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != RESULT_SCHEMA or type(self.status) is not PriorGuidedDiscoveryStatus:
            raise PriorGuidedDiscoveryInvariantViolation("result schema/status substitution")
        if type(self.source_evidences) is not tuple or any(
            type(item) is not SourceCandidateEvidenceV1 for item in self.source_evidences
        ):
            raise PriorGuidedDiscoveryInvariantViolation("result source evidence requires exact tuple/types")
        for value, expected, label in (
            (self.prior, StructuralHypothesisPriorV1, "prior"),
            (self.proposal, HeldOutTargetProposalV1, "proposal"),
            (self.target_audit, ExactTargetCandidateAuditV1, "target audit"),
            (self.accounting, PriorGuidedDiscoveryAccountingV1, "accounting"),
        ):
            if type(value) is not expected:
                raise PriorGuidedDiscoveryInvariantViolation(f"result {label} requires exact type")
        for value, expected, label in (
            (self.predicate_tree, DirectPredicateTreeV1, "predicate tree"),
            (self.partition, Partition, "partition"),
            (self.semantic_adapter, DirectActionSemanticAdapterV1, "semantic adapter"),
            (self.quotient_models, QuotientModels, "quotient models"),
            (self.portable_build, PortableBuildResult, "portable build"),
            (self.certificate, PriorGuidedExactCertificateV1, "certificate"),
        ):
            if value is not None and type(value) is not expected:
                raise PriorGuidedDiscoveryInvariantViolation(f"result {label} requires exact type")
        ordered_sources = tuple(sorted(self.source_evidences, key=lambda item: item.source_task_id))
        if self.source_evidences != ordered_sources:
            raise PriorGuidedDiscoveryInvariantViolation("result source evidence must be canonical")
        if (
            self.prior.source_task_ids != tuple(item.source_task_id for item in self.source_evidences)
            or self.prior.source_evidence_ids != tuple(item.evidence_id for item in self.source_evidences)
            or self.prior.source_coverage_ids != tuple(item.source_coverage_id for item in self.source_evidences)
        ):
            raise PriorGuidedDiscoveryInvariantViolation("result source/prior authority mismatch")
        if self.prior.profile == PRODUCTION_PRIOR_PROFILE and (
            any(not item.candidate.exact_homomorphism for item in self.source_evidences)
            or any(item.hypothesis != self.prior.preferred_hypothesis for item in self.source_evidences)
        ):
            raise PriorGuidedDiscoveryInvariantViolation("production prior is not source-unanimous exact")
        if (
            self.proposal.prior_id != self.prior.prior_id
            or self.proposal.hypothesis != self.prior.preferred_hypothesis
            or self.proposal.target_task_id in self.prior.source_task_ids
            or self.proposal.target_coverage_id in self.prior.source_coverage_ids
        ):
            raise PriorGuidedDiscoveryInvariantViolation("result prior/proposal holdout mismatch")
        if any(
            item.structural_id != self.proposal.target_structural_id
            for item in self.source_evidences
        ):
            raise PriorGuidedDiscoveryInvariantViolation("source/target structural identity mismatch")
        if (
            self.target_audit.proposal_id != self.proposal.proposal_id
            or self.target_audit.prior_id != self.prior.prior_id
            or self.target_audit.target_task_id != self.proposal.target_task_id
            or self.target_audit.structural_id != self.proposal.target_structural_id
            or self.target_audit.target_coverage_id != self.proposal.target_coverage_id
            or self.target_audit.hypothesis != self.proposal.hypothesis
            or self.target_audit.candidate.selected_state_features != self.proposal.hypothesis.state_features
            or self.target_audit.candidate.selected_action_features != self.proposal.hypothesis.action_features
        ):
            raise PriorGuidedDiscoveryInvariantViolation("result proposal/audit authority mismatch")
        expected_source_totals = (
            len(self.source_evidences),
            sum(item.accounting.interaction_samples for item in self.source_evidences),
            sum(item.accounting.exact_ground_kernel_calls for item in self.source_evidences),
            sum(item.accounting.unique_ground_state_action_rows for item in self.source_evidences),
            sum(item.accounting.eligible_ground_state_action_rows for item in self.source_evidences),
            sum(item.accounting.candidate_hypothesis_evaluations for item in self.source_evidences),
        )
        actual_source_totals = (
            self.accounting.source_task_count,
            self.accounting.source_offline_interaction_samples,
            self.accounting.source_offline_exact_ground_kernel_calls,
            self.accounting.source_offline_unique_ground_state_action_rows,
            self.accounting.source_offline_eligible_ground_state_action_rows,
            self.accounting.source_offline_candidate_hypothesis_evaluations,
        )
        if actual_source_totals != expected_source_totals or (
            self.accounting.interaction_samples != self.target_audit.interaction_samples
            or self.accounting.exact_ground_kernel_calls != self.target_audit.exact_ground_kernel_calls
            or self.accounting.unique_ground_state_action_rows != self.target_audit.unique_ground_state_action_rows
            or self.accounting.eligible_ground_state_action_rows != self.target_audit.eligible_ground_state_action_rows
            or self.accounting.candidate_hypothesis_evaluations != self.target_audit.candidate_hypothesis_evaluations
            or self.accounting.acquisition_kind != self.target_audit.acquisition_kind
            or self.accounting.outcomes_counted_as_interaction_samples != self.target_audit.outcomes_counted_as_interaction_samples
        ):
            raise PriorGuidedDiscoveryInvariantViolation("result accounting authority mismatch")
        if type(self.exact_homomorphism_verified) is not bool or self.global_minimality_verified is not False or self.infeasibility_claim is not False:
            raise PriorGuidedDiscoveryInvariantViolation("result verification and claim flags are invalid")
        published = (
            self.predicate_tree,
            self.partition,
            self.semantic_adapter,
            self.quotient_models,
            self.portable_build,
            self.certificate,
        )
        if self.status is PriorGuidedDiscoveryStatus.EXACT_HELDOUT_HOMOMORPHISM:
            if self.exact_homomorphism_verified is not True:
                raise PriorGuidedDiscoveryInvariantViolation("positive result must explicitly verify exact homomorphism")
            if any(item is None for item in published) or self.fallback_required is not False or self.fallback_code is not None:
                raise PriorGuidedDiscoveryInvariantViolation("positive result is incomplete")
            if not self.target_audit.candidate.exact_homomorphism:
                raise PriorGuidedDiscoveryInvariantViolation("positive result lacks exact target audit")
            if (
                self.predicate_tree.tree_id != self.target_audit.candidate.predicate_tree_id
                or self.predicate_tree.partition_id != self.target_audit.candidate.partition_id
                or _partition_id(self.partition) != self.target_audit.candidate.partition_id
                or self.semantic_adapter.selected_action_features != self.proposal.hypothesis.action_features
                or self.quotient_models.nominal.partition != self.partition
                or self.quotient_models.envelope.partition != self.partition
            ):
                raise PriorGuidedDiscoveryInvariantViolation("result candidate/tree/partition/model mismatch")
            _validate_partition_graph(self.partition)
            _validate_quotient_graph(self.quotient_models)
            _validate_portable_graph(self.portable_build)
            certificate_chain = (
                self.certificate.target_task_id == self.proposal.target_task_id,
                self.certificate.structural_id == self.proposal.target_structural_id,
                self.certificate.target_coverage_id == self.proposal.target_coverage_id,
                self.certificate.prior_id == self.prior.prior_id,
                self.certificate.prior_profile == self.prior.profile,
                self.certificate.proposal_id == self.proposal.proposal_id,
                self.certificate.target_audit_id == self.target_audit.audit_id,
                self.certificate.hypothesis_id == self.proposal.hypothesis.hypothesis_id,
                self.certificate.candidate_id == self.target_audit.candidate.candidate_id,
                self.certificate.predicate_tree_id == self.predicate_tree.tree_id,
                self.certificate.partition_id == _partition_id(self.partition),
                self.certificate.portable_model_id == self.portable_build.model.model_id,
                self.certificate.selected_state_features == self.proposal.hypothesis.state_features,
                self.certificate.selected_action_features == self.proposal.hypothesis.action_features,
                self.certificate.state_thresholds == tuple(item.threshold for item in self.predicate_tree.generated_atoms),
                self.certificate.ground_state_count == len(self.partition.states),
                self.certificate.active_ground_state_count == sum(state.status is LMBStatus.ACTIVE for state in self.partition.states),
                self.certificate.quotient_cell_count == len(self.partition.cell_ids),
                self.certificate.active_quotient_cell_count == self.predicate_tree.active_cell_count,
                self.certificate.abstract_entry_count == len(self.quotient_models.envelope.entries),
                self.certificate.exact_homomorphism_verified is True,
                self.certificate.global_minimality_verified is False,
            )
            if not all(certificate_chain):
                raise PriorGuidedDiscoveryInvariantViolation("positive certificate chain mismatch")
        else:
            if self.exact_homomorphism_verified is not False:
                raise PriorGuidedDiscoveryInvariantViolation("prior mismatch cannot claim exact homomorphism")
            if any(item is not None for item in published) or self.fallback_required is not True or self.fallback_code != FALLBACK_CODE:
                raise PriorGuidedDiscoveryInvariantViolation("prior mismatch must fail closed")
            if self.target_audit.candidate.exact_homomorphism:
                raise PriorGuidedDiscoveryInvariantViolation("negative result contains exact target candidate")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status.value,
            "source_evidence_ids": [item.evidence_id for item in self.source_evidences],
            "prior_id": self.prior.prior_id,
            "proposal_id": self.proposal.proposal_id,
            "target_audit_id": self.target_audit.audit_id,
            "accounting": self.accounting.to_document(),
            "portable_model_id": None if self.portable_build is None else self.portable_build.model.model_id,
            "certificate_id": None if self.certificate is None else self.certificate.certificate_id,
            "fallback_required": self.fallback_required,
            "fallback_code": self.fallback_code,
            "exact_homomorphism_verified": self.exact_homomorphism_verified,
            "global_minimality_verified": self.global_minimality_verified,
            "infeasibility_claim": self.infeasibility_claim,
        }

    @property
    def result_id(self) -> str:
        return _content_id(RESULT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


class _CountingKernel:
    __slots__ = ("kernel", "exact_ground_kernel_calls", "accessed_rows")

    def __init__(self, kernel: LMBKernel) -> None:
        self.kernel = kernel
        self.exact_ground_kernel_calls = 0
        self.accessed_rows: set[tuple[LMBState, Any]] = set()

    def step(self, state: LMBState, action: Any) -> Any:
        self.exact_ground_kernel_calls += 1
        self.accessed_rows.add((state, action))
        return self.kernel.step(state, action)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.kernel, name)


@dataclass(frozen=True, slots=True)
class _CandidateRuntime:
    candidate: DirectHomomorphismCandidateV1
    witness: DirectHomomorphismWitnessV1 | None
    tree: DirectPredicateTreeV1
    partition: Partition
    adapter: DirectActionSemanticAdapterV1
    models: QuotientModels | None
    portable: PortableBuildResult | None
    exact_ground_kernel_calls: int
    unique_ground_state_action_rows: int
    eligible_ground_state_action_rows: int


def _audit_candidate(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    hypothesis: FeatureSubsetHypothesisV1,
    *,
    build_model: bool,
) -> _CandidateRuntime:
    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise PriorGuidedDiscoveryInvariantViolation(
            "candidate audit requires exact LMBKernel/SuiteBuildCoverage types"
        )
    if type(hypothesis) is not FeatureSubsetHypothesisV1:
        raise PriorGuidedDiscoveryInvariantViolation("candidate audit rejects duck hypotheses")
    try:
        _validate_feature_implementation_authority()
        states = _states(coverage.covered_states)
        registry = direct_state_feature_registry_v1()
        rows = _state_feature_rows(kernel, states, registry)
        tree, partition = _compile_state_tree(states, rows, hypothesis.state_features)
        counted = _CountingKernel(kernel)
        entry_count, witness = _verify_candidate_obligations(
            counted,
            partition,
            hypothesis.state_features,
            hypothesis.action_features,
        )
        candidate = DirectHomomorphismCandidateV1(
            hypothesis.state_features,
            hypothesis.action_features,
            tree.tree_id,
            tree.partition_id,
            tree.cell_count,
            tree.active_cell_count,
            len(tree.splits),
            entry_count,
            witness is None,
            None if witness is None else witness.witness_id,
        )
        adapter = DirectActionSemanticAdapterV1(hypothesis.action_features)
        models: QuotientModels | None = None
        portable: PortableBuildResult | None = None
        if witness is None and build_model:
            models = build_quotient_models(
                counted, states, partition, semantic_adapter=adapter
            )
            if not _singleton(models):
                raise PriorGuidedDiscoveryInvariantViolation(
                    "exact target audit produced a non-singleton envelope"
                )
            portable = _portable(counted, coverage, models)
        eligible_rows = sum(
            len(kernel.actions(state))
            for state in states
            if state.status is LMBStatus.ACTIVE
        )
        unique_rows = len(counted.accessed_rows)
        return _CandidateRuntime(
            candidate,
            witness,
            tree,
            partition,
            adapter,
            models,
            portable,
            counted.exact_ground_kernel_calls,
            unique_rows,
            eligible_rows,
        )
    except DirectSynthesisInvariantViolation as exc:
        raise PriorGuidedDiscoveryInvariantViolation(str(exc)) from exc


def build_source_candidate_evidence_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    *,
    source_task_id: str,
    hypothesis: FeatureSubsetHypothesisV1,
) -> SourceCandidateEvidenceV1:
    runtime = _audit_candidate(kernel, coverage, hypothesis, build_model=False)
    return SourceCandidateEvidenceV1(
        source_task_id,
        _structural_id(kernel),
        _coverage_id(coverage),
        hypothesis,
        runtime.candidate,
        runtime.witness,
        SourceOfflineAccountingV1(
            0,
            runtime.exact_ground_kernel_calls,
            runtime.unique_ground_state_action_rows,
            runtime.eligible_ground_state_action_rows,
            1,
        ),
    )


def verify_source_candidate_evidence_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    evidence: SourceCandidateEvidenceV1,
) -> tuple[str, ...]:
    if type(evidence) is not SourceCandidateEvidenceV1:
        raise PriorGuidedDiscoveryInvariantViolation("source verifier rejects duck evidence")
    expected = build_source_candidate_evidence_v1(
        kernel,
        coverage,
        source_task_id=evidence.source_task_id,
        hypothesis=evidence.hypothesis,
    )
    return () if evidence.to_document() == expected.to_document() else ("SOURCE_EVIDENCE_MISMATCH",)


def propose_heldout_target_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    *,
    target_task_id: str,
    prior: StructuralHypothesisPriorV1,
) -> HeldOutTargetProposalV1:
    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise PriorGuidedDiscoveryInvariantViolation(
            "proposal requires exact LMBKernel/SuiteBuildCoverage types"
        )
    if type(prior) is not StructuralHypothesisPriorV1:
        raise PriorGuidedDiscoveryInvariantViolation("proposal rejects duck priors")
    if target_task_id in prior.source_task_ids:
        raise PriorGuidedDiscoveryInvariantViolation(
            "held-out target task ID occurs among source task IDs"
        )
    target_coverage_id = _coverage_id(coverage)
    if target_coverage_id in prior.source_coverage_ids:
        raise PriorGuidedDiscoveryInvariantViolation(
            "held-out target coverage identity occurs among source coverage identities"
        )
    return HeldOutTargetProposalV1(
        target_task_id,
        _structural_id(kernel),
        target_coverage_id,
        prior.prior_id,
        prior.preferred_hypothesis,
    )


def _accounting(
    source_evidences: tuple[SourceCandidateEvidenceV1, ...],
    target: _CandidateRuntime,
) -> PriorGuidedDiscoveryAccountingV1:
    return PriorGuidedDiscoveryAccountingV1(
        interaction_samples=0,
        exact_ground_kernel_calls=target.exact_ground_kernel_calls,
        unique_ground_state_action_rows=target.unique_ground_state_action_rows,
        eligible_ground_state_action_rows=target.eligible_ground_state_action_rows,
        candidate_hypothesis_evaluations=1,
        source_task_count=len(source_evidences),
        source_offline_interaction_samples=sum(
            item.accounting.interaction_samples for item in source_evidences
        ),
        source_offline_exact_ground_kernel_calls=sum(
            item.accounting.exact_ground_kernel_calls for item in source_evidences
        ),
        source_offline_unique_ground_state_action_rows=sum(
            item.accounting.unique_ground_state_action_rows for item in source_evidences
        ),
        source_offline_eligible_ground_state_action_rows=sum(
            item.accounting.eligible_ground_state_action_rows for item in source_evidences
        ),
        source_offline_candidate_hypothesis_evaluations=sum(
            item.accounting.candidate_hypothesis_evaluations for item in source_evidences
        ),
        acquisition_kind=EXACT_ACQUISITION_KIND,
        outcomes_counted_as_interaction_samples=False,
    )


def _run_prior_guided_lmb_discovery_v1(
    kernel: LMBKernel,
    target_coverage: SuiteBuildCoverage[LMBState],
    *,
    target_task_id: str,
    source_evidences: tuple[SourceCandidateEvidenceV1, ...],
    prior: StructuralHypothesisPriorV1,
    required_prior_profile: str,
) -> PriorGuidedDiscoveryResultV1:
    if type(kernel) is not LMBKernel or type(target_coverage) is not SuiteBuildCoverage:
        raise PriorGuidedDiscoveryInvariantViolation(
            "V0-040 runner requires exact LMBKernel/SuiteBuildCoverage types"
        )
    if type(source_evidences) is not tuple or any(
        type(item) is not SourceCandidateEvidenceV1 for item in source_evidences
    ):
        raise PriorGuidedDiscoveryInvariantViolation(
            "V0-040 runner requires exact source-evidence tuple/types"
        )
    if type(prior) is not StructuralHypothesisPriorV1:
        raise PriorGuidedDiscoveryInvariantViolation("V0-040 runner rejects duck priors")
    if prior.profile != required_prior_profile:
        raise PriorGuidedDiscoveryInvariantViolation("runner rejects incompatible prior profile")
    ordered = tuple(sorted(source_evidences, key=lambda item: item.source_task_id))
    if source_evidences != ordered:
        raise PriorGuidedDiscoveryInvariantViolation("source evidence must be canonical")
    if prior.source_task_ids != tuple(item.source_task_id for item in ordered) or prior.source_evidence_ids != tuple(item.evidence_id for item in ordered):
        raise PriorGuidedDiscoveryInvariantViolation("prior does not bind supplied source evidence")
    proposal = propose_heldout_target_v1(
        kernel, target_coverage, target_task_id=target_task_id, prior=prior
    )
    runtime = _audit_candidate(
        kernel, target_coverage, proposal.hypothesis, build_model=True
    )
    audit = ExactTargetCandidateAuditV1(
        target_task_id,
        _structural_id(kernel),
        _coverage_id(target_coverage),
        prior.prior_id,
        proposal.proposal_id,
        proposal.hypothesis,
        runtime.candidate,
        runtime.witness,
        0,
        runtime.exact_ground_kernel_calls,
        runtime.unique_ground_state_action_rows,
        runtime.eligible_ground_state_action_rows,
    )
    accounting = _accounting(ordered, runtime)
    if not runtime.candidate.exact_homomorphism:
        return PriorGuidedDiscoveryResultV1(
            PriorGuidedDiscoveryStatus.PRIOR_MISMATCH_FALLBACK_REQUIRED,
            ordered,
            prior,
            proposal,
            audit,
            accounting,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            FALLBACK_CODE,
            False,
            False,
            False,
        )
    certificate = PriorGuidedExactCertificateV1(
        target_task_id,
        _structural_id(kernel),
        _coverage_id(target_coverage),
        prior.prior_id,
        proposal.proposal_id,
        audit.audit_id,
        proposal.hypothesis.hypothesis_id,
        runtime.candidate.candidate_id,
        runtime.tree.tree_id,
        _partition_id(runtime.partition),
        runtime.portable.model.model_id,
        proposal.hypothesis.state_features,
        proposal.hypothesis.action_features,
        tuple(item.threshold for item in runtime.tree.generated_atoms),
        len(target_coverage.covered_states),
        sum(state.status is LMBStatus.ACTIVE for state in target_coverage.covered_states),
        len(runtime.partition.cell_ids),
        runtime.tree.active_cell_count,
        len(runtime.models.envelope.entries),
        prior.profile,
    )
    return PriorGuidedDiscoveryResultV1(
        PriorGuidedDiscoveryStatus.EXACT_HELDOUT_HOMOMORPHISM,
        ordered,
        prior,
        proposal,
        audit,
        accounting,
        runtime.tree,
        runtime.partition,
        runtime.adapter,
        runtime.models,
        runtime.portable,
        certificate,
        False,
        None,
        True,
        False,
        False,
    )


def run_prior_guided_lmb_discovery_v1(
    kernel: LMBKernel,
    target_coverage: SuiteBuildCoverage[LMBState],
    *,
    target_task_id: str,
    source_evidences: tuple[SourceCandidateEvidenceV1, ...],
    prior: StructuralHypothesisPriorV1,
) -> PriorGuidedDiscoveryResultV1:
    return _run_prior_guided_lmb_discovery_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_evidences=source_evidences,
        prior=prior,
        required_prior_profile=PRODUCTION_PRIOR_PROFILE,
    )


def run_prior_guided_lmb_control_v1(
    kernel: LMBKernel,
    target_coverage: SuiteBuildCoverage[LMBState],
    *,
    target_task_id: str,
    source_evidences: tuple[SourceCandidateEvidenceV1, ...],
    prior: StructuralHypothesisPriorV1,
) -> PriorGuidedDiscoveryResultV1:
    return _run_prior_guided_lmb_discovery_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_evidences=source_evidences,
        prior=prior,
        required_prior_profile=CONTROL_PRIOR_PROFILE,
    )


def _verify_prior_guided_lmb_discovery_v1(
    kernel: LMBKernel,
    target_coverage: SuiteBuildCoverage[LMBState],
    *,
    target_task_id: str,
    source_coverages: tuple[tuple[str, SuiteBuildCoverage[LMBState]], ...],
    result: PriorGuidedDiscoveryResultV1,
    required_prior_profile: str,
) -> tuple[str, ...]:
    """Independently rebuild every source audit and the complete target result."""

    if type(result) is not PriorGuidedDiscoveryResultV1:
        raise PriorGuidedDiscoveryInvariantViolation("independent verifier rejects duck results")
    if result.prior.profile != required_prior_profile:
        raise PriorGuidedDiscoveryInvariantViolation("verifier rejects incompatible prior profile")
    if type(source_coverages) is not tuple or any(
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not str
        or type(item[1]) is not SuiteBuildCoverage
        for item in source_coverages
    ):
        raise PriorGuidedDiscoveryInvariantViolation(
            "source verifier inputs require exact canonical tuple pairs"
        )
    if tuple(sorted(source_coverages, key=lambda item: item[0])) != source_coverages:
        raise PriorGuidedDiscoveryInvariantViolation("source coverage inputs must be sorted")
    if tuple(item[0] for item in source_coverages) != result.prior.source_task_ids:
        raise PriorGuidedDiscoveryInvariantViolation("source coverage/task identities mismatch")
    source_failures: list[str] = []
    for (source_task_id, coverage), evidence in zip(
        source_coverages, result.source_evidences
    ):
        if source_task_id != evidence.source_task_id:
            source_failures.append("SOURCE_TASK_ORDER_MISMATCH")
            continue
        if verify_source_candidate_evidence_v1(kernel, coverage, evidence):
            source_failures.append(f"SOURCE_EVIDENCE_MISMATCH:{source_task_id}")
    if source_failures:
        return tuple(source_failures)
    expected = _run_prior_guided_lmb_discovery_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_evidences=result.source_evidences,
        prior=result.prior,
        required_prior_profile=required_prior_profile,
    )
    failures: list[str] = []
    for code, left, right in (
        ("RESULT_DOCUMENT_MISMATCH", result.to_document(), expected.to_document()),
        ("PROPOSAL_MISMATCH", result.proposal.to_document(), expected.proposal.to_document()),
        ("TARGET_AUDIT_MISMATCH", result.target_audit.to_document(), expected.target_audit.to_document()),
        ("ACCOUNTING_MISMATCH", result.accounting.to_document(), expected.accounting.to_document()),
        ("PREDICATE_TREE_MISMATCH", None if result.predicate_tree is None else result.predicate_tree.to_document(), None if expected.predicate_tree is None else expected.predicate_tree.to_document()),
        ("PARTITION_MISMATCH", result.partition, expected.partition),
        ("SEMANTIC_ADAPTER_MISMATCH", result.semantic_adapter, expected.semantic_adapter),
        ("QUOTIENT_MODELS_MISMATCH", result.quotient_models, expected.quotient_models),
        ("PORTABLE_MODEL_MISMATCH", None if result.portable_build is None else result.portable_build.model.to_dict(), None if expected.portable_build is None else expected.portable_build.model.to_dict()),
        ("PORTABLE_REGISTRY_MISMATCH", None if result.portable_build is None else result.portable_build.registry, None if expected.portable_build is None else expected.portable_build.registry),
        ("CERTIFICATE_MISMATCH", None if result.certificate is None else result.certificate.to_document(), None if expected.certificate is None else expected.certificate.to_document()),
    ):
        if left != right:
            failures.append(code)
    return tuple(failures)


def verify_prior_guided_lmb_discovery_v1(
    kernel: LMBKernel,
    target_coverage: SuiteBuildCoverage[LMBState],
    *,
    target_task_id: str,
    source_coverages: tuple[tuple[str, SuiteBuildCoverage[LMBState]], ...],
    result: PriorGuidedDiscoveryResultV1,
) -> tuple[str, ...]:
    return _verify_prior_guided_lmb_discovery_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_coverages=source_coverages,
        result=result,
        required_prior_profile=PRODUCTION_PRIOR_PROFILE,
    )


def verify_prior_guided_lmb_control_v1(
    kernel: LMBKernel,
    target_coverage: SuiteBuildCoverage[LMBState],
    *,
    target_task_id: str,
    source_coverages: tuple[tuple[str, SuiteBuildCoverage[LMBState]], ...],
    result: PriorGuidedDiscoveryResultV1,
) -> tuple[str, ...]:
    return _verify_prior_guided_lmb_discovery_v1(
        kernel,
        target_coverage,
        target_task_id=target_task_id,
        source_coverages=source_coverages,
        result=result,
        required_prior_profile=CONTROL_PRIOR_PROFILE,
    )


__all__ = [
    "ExactTargetCandidateAuditV1",
    "FeatureSubsetHypothesisV1",
    "HeldOutTargetProposalV1",
    "PriorGuidedDiscoveryAccountingV1",
    "PriorGuidedDiscoveryInvariantViolation",
    "PriorGuidedDiscoveryResultV1",
    "PriorGuidedDiscoveryStatus",
    "PriorGuidedExactCertificateV1",
    "SourceCandidateEvidenceV1",
    "SourceOfflineAccountingV1",
    "StructuralHypothesisPriorV1",
    "build_external_control_structural_prior_v1",
    "build_source_candidate_evidence_v1",
    "build_structural_hypothesis_prior_v1",
    "feature_subset_hypothesis_v1",
    "propose_heldout_target_v1",
    "run_prior_guided_lmb_control_v1",
    "run_prior_guided_lmb_discovery_v1",
    "verify_prior_guided_lmb_control_v1",
    "verify_prior_guided_lmb_discovery_v1",
    "verify_source_candidate_evidence_v1",
]
