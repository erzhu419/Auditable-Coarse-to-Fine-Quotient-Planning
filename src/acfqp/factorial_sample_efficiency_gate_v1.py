"""Matched V0-067 sample-efficiency Gate over the V0-066 graph family.

The Gate is intentionally an authority boundary, not an acquisition
implementation.  It consumes independently verified occurrence results from
four quotient-planning cells

```
no prior / fixed       no prior / sequential
meta prior / fixed     meta prior / sequential
```

and two cold direct-ground controls (fixed and sequential).  The four
quotient cells cover the exact V0-066 W5, K6, and K6-minus-edge occurrences.
The direct controls cover the two positive W5/K6 occurrences.  K6-minus-edge
is a fail-closed negative control with one common exact-fallback authority; it
is retained in the native family work vector but excluded from the
generative-draw endpoint.

The distinction between *acquisition draws* and *certified target draws* is
normative.  In particular, the historical V0-066 graph arm contains exactly
18,612,224 acquisition draws, but its K6-minus-edge route invokes an exact
ground fallback.  All four quotient cells must use that same 60-row exact
fallback authority.  Those exact rows are reported separately and never
enter, offset, or masquerade as the positive-context draw endpoint.

The Gate reports both transfer regimes:

* pretrained target-online draws, excluding the frozen source archive; and
* offline-inclusive cumulative draws, charging the source archive once and
  identifying the first observed logical occurrence at which it amortizes.

No heterogeneous work classes are scalarized.  The positive claim, when all
checks pass, is limited to the registered finite V0-066 workload.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.31.0"
PROFILE_KEY = "v0067_v0066_graph_factorial_sample_efficiency_v0"

FIXED_SAMPLE_COUNT_PER_ROW = 131_072
REGISTERED_FAMILY_TAIL_UPPER = Fraction(287, 250_000)
REGISTERED_CONFIDENCE_LOWER = 1 - REGISTERED_FAMILY_TAIL_UPPER
REGISTERED_CLAIM_SCOPE = (
    "REGISTERED_PRETRAINED_REUSABLE_QUOTIENT_POSITIVE_TARGET_TRANSITION_"
    "PROBABILITY_GENERATIVE_DRAW_EFFICIENCY_CONDITIONAL_ON_KNOWN_EXACT_"
    "SUPPORT_REWARD_FAILURE_LABELS"
)


class FactorialSampleEfficiencyInvariantViolation(ValueError):
    """A preregistration, arm result, or matched comparison is invalid."""


DOMAIN_TAGS = {
    "arm": "acfqp:v0067-factorial-arm:v1",
    "events": "acfqp:v0067-evidence-event-vector:v1",
    "work": "acfqp:v0067-occurrence-sample-work:v1",
    "confidence": "acfqp:v0067-confidence-contract:v1",
    "confidence_reconciliation": (
        "acfqp:v0067-confidence-reconciliation:v1"
    ),
    "occurrence": "acfqp:v0067-graph-occurrence:v1",
    "paired_seed": "acfqp:v0067-paired-graph-seed-stream:v1",
    "prior": "acfqp:v0067-source-prior-gate-evidence:v1",
    "operator_instantiation": (
        "acfqp:v0067-target-sequential-operator-instantiation:v1"
    ),
    "result": "acfqp:v0067-occurrence-arm-result:v1",
    "preregistration": "acfqp:v0067-factorial-preregistration:v1",
    "summary": "acfqp:v0067-factorial-arm-summary:v1",
    "gate": "acfqp:v0067-factorial-gate-result:v1",
}


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise FactorialSampleEfficiencyInvariantViolation(str(error)) from error
    return hashlib.sha256(tag + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise FactorialSampleEfficiencyInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _text(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise FactorialSampleEfficiencyInvariantViolation(
            f"{field} must be nonempty text"
        )
    return value


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise FactorialSampleEfficiencyInvariantViolation(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


class PlannerKind(str, Enum):
    QUOTIENT_RAPM = "QUOTIENT_RAPM"
    COLD_DIRECT_GROUND = "COLD_DIRECT_GROUND"


class ProposalMode(str, Enum):
    NO_PRIOR = "NO_PRIOR"
    SOURCE_META_PRIOR = "SOURCE_META_PRIOR"


class StoppingMode(str, Enum):
    FIXED = "FIXED"
    SEQUENTIAL = "SEQUENTIAL"


class TerminalClass(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    INFEASIBILITY_CERTIFICATE = "INFEASIBILITY_CERTIFICATE"


class ConfidenceFamily(str, Enum):
    QUOTIENT_FIXED = "QUOTIENT_FIXED"
    QUOTIENT_SEQUENTIAL = "QUOTIENT_SEQUENTIAL"
    DIRECT_FIXED = "DIRECT_FIXED"
    DIRECT_SEQUENTIAL = "DIRECT_SEQUENTIAL"


@dataclass(frozen=True, slots=True)
class FactorialArmV1:
    planner: PlannerKind
    proposal: ProposalMode
    stopping: StoppingMode

    def __post_init__(self) -> None:
        if (
            type(self.planner) is not PlannerKind
            or type(self.proposal) is not ProposalMode
            or type(self.stopping) is not StoppingMode
            or (
                self.planner is PlannerKind.COLD_DIRECT_GROUND
                and self.proposal is not ProposalMode.NO_PRIOR
            )
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "factorial arm is outside the registered 4+2 design"
            )

    @property
    def arm_key(self) -> str:
        return (
            f"{self.planner.value.lower()}__"
            f"{self.proposal.value.lower()}__"
            f"{self.stopping.value.lower()}"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_factorial_arm.v1",
            "schema_version": SCHEMA_VERSION,
            "planner": self.planner.value,
            "proposal": self.proposal.value,
            "stopping": self.stopping.value,
            "arm_key": self.arm_key,
        }

    @property
    def arm_id(self) -> str:
        return _content_id("arm", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "arm_id": self.arm_id}


NO_PRIOR_FIXED = FactorialArmV1(
    PlannerKind.QUOTIENT_RAPM,
    ProposalMode.NO_PRIOR,
    StoppingMode.FIXED,
)
NO_PRIOR_SEQUENTIAL = FactorialArmV1(
    PlannerKind.QUOTIENT_RAPM,
    ProposalMode.NO_PRIOR,
    StoppingMode.SEQUENTIAL,
)
META_PRIOR_FIXED = FactorialArmV1(
    PlannerKind.QUOTIENT_RAPM,
    ProposalMode.SOURCE_META_PRIOR,
    StoppingMode.FIXED,
)
META_PRIOR_SEQUENTIAL = FactorialArmV1(
    PlannerKind.QUOTIENT_RAPM,
    ProposalMode.SOURCE_META_PRIOR,
    StoppingMode.SEQUENTIAL,
)
DIRECT_FIXED = FactorialArmV1(
    PlannerKind.COLD_DIRECT_GROUND,
    ProposalMode.NO_PRIOR,
    StoppingMode.FIXED,
)
DIRECT_SEQUENTIAL = FactorialArmV1(
    PlannerKind.COLD_DIRECT_GROUND,
    ProposalMode.NO_PRIOR,
    StoppingMode.SEQUENTIAL,
)

REGISTERED_ARMS = (
    NO_PRIOR_FIXED,
    NO_PRIOR_SEQUENTIAL,
    META_PRIOR_FIXED,
    META_PRIOR_SEQUENTIAL,
    DIRECT_FIXED,
    DIRECT_SEQUENTIAL,
)


@dataclass(frozen=True, slots=True)
class RegisteredGraphContextV1:
    context_key: str
    context_id: str
    no_prior_fixed_acquisition_rows: int
    direct_fixed_acquisition_rows: int
    fixture_role: str
    risk_tolerance: Fraction

    def __post_init__(self) -> None:
        _text(self.context_key, "registered graph context key")
        _cid(self.context_id, "registered graph context")
        registered = {
            "variable_target_w5_v0": (
                "a7f8b82bcf6639ad57506f3c900abc98d5dc3be0cbfd50515105290da476ce36",
                22,
                30,
                "POSITIVE_CONDITIONAL_CERTIFICATE",
                Fraction(1, 20),
            ),
            "variable_target_k6_v0": (
                "09ee595f5fe3561eafe1d701607fef559d280b34fd9d1dddc4cb551024a61430",
                60,
                60,
                "POSITIVE_CONDITIONAL_CERTIFICATE",
                Fraction(1, 20),
            ),
            "variable_negative_k6_minus_edge_v0": (
                "eebbfb29f695fbb6f5deb81fdac9a64d3df68dd03940d484c4e0e51b58ee95fb",
                60,
                60,
                "NO_SOUND_COVER_REQUIRES_MATCHED_FALLBACK",
                Fraction(1, 5),
            ),
        }
        if registered.get(self.context_key) != (
            self.context_id,
            self.no_prior_fixed_acquisition_rows,
            self.direct_fixed_acquisition_rows,
            self.fixture_role,
            self.risk_tolerance,
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "sample Gate context is not the frozen V0-066 graph family"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "context_key": self.context_key,
            "context_id": self.context_id,
            "no_prior_fixed_acquisition_rows": (
                self.no_prior_fixed_acquisition_rows
            ),
            "direct_fixed_acquisition_rows": (
                self.direct_fixed_acquisition_rows
            ),
            "fixture_role": self.fixture_role,
            "risk_tolerance": _fdoc(self.risk_tolerance),
        }


REGISTERED_GRAPH_CONTEXTS = (
    RegisteredGraphContextV1(
        "variable_target_w5_v0",
        "a7f8b82bcf6639ad57506f3c900abc98d5dc3be0cbfd50515105290da476ce36",
        22,
        30,
        "POSITIVE_CONDITIONAL_CERTIFICATE",
        Fraction(1, 20),
    ),
    RegisteredGraphContextV1(
        "variable_target_k6_v0",
        "09ee595f5fe3561eafe1d701607fef559d280b34fd9d1dddc4cb551024a61430",
        60,
        60,
        "POSITIVE_CONDITIONAL_CERTIFICATE",
        Fraction(1, 20),
    ),
    RegisteredGraphContextV1(
        "variable_negative_k6_minus_edge_v0",
        "eebbfb29f695fbb6f5deb81fdac9a64d3df68dd03940d484c4e0e51b58ee95fb",
        60,
        60,
        "NO_SOUND_COVER_REQUIRES_MATCHED_FALLBACK",
        Fraction(1, 5),
    ),
)


@dataclass(frozen=True, slots=True)
class EvidenceEventVectorV1:
    """Canonical five-class evidence vector for one immutable lane."""

    lane: str
    environment_interactions: int
    generative_oracle_samples: int
    exact_kernel_queries: int
    offline_logged_observations: int
    synthetic_model_rollouts: int

    def __post_init__(self) -> None:
        if self.lane not in (
            "ONLINE_TARGET",
            "OPERATIONAL_QUERY",
            "STANDALONE_EVALUATION",
            "OFFLINE_SOURCE",
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "evidence vector lane is unregistered"
            )
        for value, field in (
            (self.environment_interactions, "environment interactions"),
            (self.generative_oracle_samples, "generative oracle samples"),
            (self.exact_kernel_queries, "exact kernel queries"),
            (self.offline_logged_observations, "offline observations"),
            (self.synthetic_model_rollouts, "synthetic rollouts"),
        ):
            _integer(value, field)
        if (
            self.lane != "OFFLINE_SOURCE"
            and self.offline_logged_observations != 0
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "offline observations leaked into a target/evaluation lane"
            )

    @classmethod
    def zero(cls, lane: str) -> "EvidenceEventVectorV1":
        return cls(lane, 0, 0, 0, 0, 0)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_evidence_event_vector.v1",
            "schema_version": SCHEMA_VERSION,
            "lane": self.lane,
            "environment_interactions": self.environment_interactions,
            "generative_oracle_samples": self.generative_oracle_samples,
            "exact_kernel_queries": self.exact_kernel_queries,
            "offline_logged_observations": (
                self.offline_logged_observations
            ),
            "synthetic_model_rollouts": self.synthetic_model_rollouts,
        }

    @property
    def vector_id(self) -> str:
        return _content_id("events", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "vector_id": self.vector_id}


@dataclass(frozen=True, slots=True)
class OccurrenceSampleWorkV1:
    """Stage-separated target work; no source cost is repeated per result."""

    target_acquisition: EvidenceEventVectorV1
    planning_and_certificate: EvidenceEventVectorV1
    fallback: EvidenceEventVectorV1
    independent_verification: EvidenceEventVectorV1

    def __post_init__(self) -> None:
        expected_lanes = (
            "ONLINE_TARGET",
            "OPERATIONAL_QUERY",
            "OPERATIONAL_QUERY",
            "STANDALONE_EVALUATION",
        )
        if (
            any(
                type(item) is not EvidenceEventVectorV1
                for item in (
                    self.target_acquisition,
                    self.planning_and_certificate,
                    self.fallback,
                    self.independent_verification,
                )
            )
            or tuple(
                item.lane
                for item in (
                    self.target_acquisition,
                    self.planning_and_certificate,
                    self.fallback,
                    self.independent_verification,
                )
            )
            != expected_lanes
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "occurrence sample work lanes were substituted"
            )

    @property
    def acquisition_draws(self) -> int:
        return self.target_acquisition.generative_oracle_samples

    @property
    def operational_target_draws(self) -> int:
        return sum(
            item.generative_oracle_samples
            for item in (
                self.target_acquisition,
                self.planning_and_certificate,
                self.fallback,
            )
        )

    @property
    def certified_target_draws(self) -> int:
        return (
            self.operational_target_draws
            + self.independent_verification.generative_oracle_samples
        )

    @property
    def operational_exact_kernel_queries(self) -> int:
        return sum(
            item.exact_kernel_queries
            for item in (
                self.target_acquisition,
                self.planning_and_certificate,
                self.fallback,
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_occurrence_sample_work.v1",
            "schema_version": SCHEMA_VERSION,
            "target_acquisition_id": self.target_acquisition.vector_id,
            "planning_and_certificate_id": (
                self.planning_and_certificate.vector_id
            ),
            "fallback_id": self.fallback.vector_id,
            "independent_verification_id": (
                self.independent_verification.vector_id
            ),
            "acquisition_draws": self.acquisition_draws,
            "operational_target_draws": self.operational_target_draws,
            "certified_target_draws": self.certified_target_draws,
            "operational_exact_kernel_queries": (
                self.operational_exact_kernel_queries
            ),
        }

    @property
    def work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "target_acquisition": self.target_acquisition.to_document(),
            "planning_and_certificate": (
                self.planning_and_certificate.to_document()
            ),
            "fallback": self.fallback.to_document(),
            "independent_verification": (
                self.independent_verification.to_document()
            ),
            "work_id": self.work_id,
        }


@dataclass(frozen=True, slots=True)
class ConfidenceContractV1:
    claim_scope_id: str
    confidence_budget_id: str
    certificate_profile_id: str
    family: ConfidenceFamily
    aggregate_obligation_count: int
    per_obligation_tail_upper: Fraction
    family_tail_upper: Fraction
    confidence_lower: Fraction
    conditional_iid_scope: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.claim_scope_id, "confidence claim scope"),
            (self.confidence_budget_id, "confidence budget"),
            (self.certificate_profile_id, "certificate profile"),
        ):
            _cid(value, field)
        _integer(
            self.aggregate_obligation_count,
            "confidence aggregate obligations",
            1,
        )
        if (
            type(self.family) is not ConfidenceFamily
            or type(self.per_obligation_tail_upper) is not Fraction
            or type(self.family_tail_upper) is not Fraction
            or type(self.confidence_lower) is not Fraction
            or self.per_obligation_tail_upper != Fraction(1, 250_000)
            or self.family_tail_upper
            != (
                self.aggregate_obligation_count
                * self.per_obligation_tail_upper
            )
            or not 0 < self.family_tail_upper < 1
            or self.confidence_lower != 1 - self.family_tail_upper
            or self.family_tail_upper > REGISTERED_FAMILY_TAIL_UPPER
            or self.conditional_iid_scope
            != (
                "CONDITIONAL_ON_REGISTERED_COUNTER_STREAM_"
                "IID_SIMULATOR_ASSUMPTION"
            )
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "confidence contract is weaker than the V0-066 family budget"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_confidence_contract.v1",
            "schema_version": SCHEMA_VERSION,
            "claim_scope_id": self.claim_scope_id,
            "confidence_budget_id": self.confidence_budget_id,
            "certificate_profile_id": self.certificate_profile_id,
            "family": self.family.value,
            "aggregate_obligation_count": self.aggregate_obligation_count,
            "per_obligation_tail_upper": _fdoc(
                self.per_obligation_tail_upper
            ),
            "family_tail_upper": _fdoc(self.family_tail_upper),
            "confidence_lower": _fdoc(self.confidence_lower),
            "conditional_iid_scope": self.conditional_iid_scope,
        }

    @property
    def confidence_id(self) -> str:
        return _content_id("confidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "confidence_id": self.confidence_id}


@dataclass(frozen=True, slots=True)
class RegisteredGraphOccurrenceV1:
    context_key: str
    context_id: str
    query_id: str
    replica_index: int

    def __post_init__(self) -> None:
        _cid(self.context_id, "occurrence context")
        _cid(self.query_id, "occurrence query")
        _integer(self.replica_index, "occurrence replica", 1)
        matching = tuple(
            item
            for item in REGISTERED_GRAPH_CONTEXTS
            if item.context_key == self.context_key
            and item.context_id == self.context_id
        )
        if len(matching) != 1:
            raise FactorialSampleEfficiencyInvariantViolation(
                "occurrence is outside the V0-066 graph contexts"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_graph_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "context_key": self.context_key,
            "context_id": self.context_id,
            "query_id": self.query_id,
            "replica_index": self.replica_index,
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


@dataclass(frozen=True, slots=True)
class SourcePriorGateEvidenceV1:
    prior_id: str
    source_context_ids: tuple[str, ...]
    target_context_ids: tuple[str, ...]
    offline_source_work: EvidenceEventVectorV1
    physical_unique_proxy_work: EvidenceEventVectorV1
    sunk_source_provenance_work: EvidenceEventVectorV1
    prior_verification_ids: tuple[str, ...]
    offline_accounting_semantics: str = (
        "COMPARISON_ACCOUNTED_MARGINAL_PROXY_EVIDENCE"
    )
    full_source_project_cost_claimed: bool = False
    frozen_before_target: bool = True
    proposal_only: bool = True
    may_certify: bool = False
    may_narrow_target_envelopes: bool = False

    def __post_init__(self) -> None:
        _cid(self.prior_id, "source meta-prior")
        if (
            type(self.prior_verification_ids) is not tuple
            or not self.prior_verification_ids
            or self.prior_verification_ids
            != tuple(sorted(set(self.prior_verification_ids)))
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "source prior verification IDs are not a canonical set"
            )
        for value in self.prior_verification_ids:
            _cid(value, "source meta-prior verification")
        for values, field in (
            (self.source_context_ids, "prior source contexts"),
            (self.target_context_ids, "prior target contexts"),
        ):
            if (
                type(values) is not tuple
                or not values
                or values != tuple(sorted(set(values)))
            ):
                raise FactorialSampleEfficiencyInvariantViolation(
                    f"{field} must be a canonical nonempty set"
                )
            for value in values:
                _cid(value, field)
        if (
            set(self.source_context_ids) & set(self.target_context_ids)
            or type(self.offline_source_work) is not EvidenceEventVectorV1
            or self.offline_source_work.lane != "OFFLINE_SOURCE"
            or type(self.physical_unique_proxy_work)
            is not EvidenceEventVectorV1
            or self.physical_unique_proxy_work.lane != "OFFLINE_SOURCE"
            or type(self.sunk_source_provenance_work)
            is not EvidenceEventVectorV1
            or self.sunk_source_provenance_work.lane != "OFFLINE_SOURCE"
            or self.physical_unique_proxy_work.generative_oracle_samples
            > self.offline_source_work.generative_oracle_samples
            or self.offline_accounting_semantics
            != "COMPARISON_ACCOUNTED_MARGINAL_PROXY_EVIDENCE"
            or self.full_source_project_cost_claimed is not False
            or self.frozen_before_target is not True
            or self.proposal_only is not True
            or self.may_certify is not False
            or self.may_narrow_target_envelopes is not False
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "meta-prior leaked target identity or gained certificate authority"
            )

    @property
    def offline_source_draws(self) -> int:
        return self.offline_source_work.generative_oracle_samples

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_source_prior_gate_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "prior_id": self.prior_id,
            "source_context_ids": list(self.source_context_ids),
            "target_context_ids": list(self.target_context_ids),
            "offline_source_work_id": self.offline_source_work.vector_id,
            "physical_unique_proxy_work_id": (
                self.physical_unique_proxy_work.vector_id
            ),
            "sunk_source_provenance_work_id": (
                self.sunk_source_provenance_work.vector_id
            ),
            "prior_verification_ids": list(self.prior_verification_ids),
            "offline_accounting_semantics": (
                self.offline_accounting_semantics
            ),
            "full_source_project_cost_claimed": False,
            "frozen_before_target": True,
            "proposal_only": True,
            "may_certify": False,
            "may_narrow_target_envelopes": False,
        }

    @property
    def gate_prior_id(self) -> str:
        return _content_id("prior", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "offline_source_work": self.offline_source_work.to_document(),
            "physical_unique_proxy_work": (
                self.physical_unique_proxy_work.to_document()
            ),
            "sunk_source_provenance_work": (
                self.sunk_source_provenance_work.to_document()
            ),
            "offline_source_draws": self.offline_source_draws,
            "gate_prior_id": self.gate_prior_id,
        }


@dataclass(frozen=True, slots=True)
class TargetSequentialOperatorInstantiationV1:
    """Typed narrowing of the source-ranked operator family on the target.

    The source candidate registers a maximum cap of 131072 draws per row.
    The target runner preregisters a strictly smaller 16384-draw cap.  This
    artifact records that relationship without claiming that the two complete
    profiles are identical.
    """

    target_proposal_id: str
    target_context_id: str
    target_query_id: str
    source_role_schema_id: str
    source_candidate_id: str
    source_operator_semantics_id: str
    target_profile_id: str
    target_checkpoints: tuple[int, ...]
    source_maximum_draws_per_row: int
    target_maximum_draws_per_row: int
    row_schedule: str
    stopping_rule: str
    confidence_method_id: str
    confidence_alpha: Fraction
    target_half_width: Fraction
    cap_failure_terminal: str
    target_cap_preregistered: bool = True
    exact_profile_transfer_claimed: bool = False
    operator_family_instantiation_only: bool = True

    def __post_init__(self) -> None:
        from acfqp.anytime_variable_graph_runner_v1 import (
            CHECKPOINTS,
            AnytimeVariableGraphTerminal,
            anytime_variable_graph_profile_v1,
        )
        from acfqp.v0066_graph_acquisition_metaprior_v1 import (
            GraphAcquisitionOperatorKind,
            _operator_candidates,
        )

        for value, field in (
            (self.target_proposal_id, "operator target proposal"),
            (self.target_context_id, "operator target context"),
            (self.target_query_id, "operator target query"),
            (self.source_role_schema_id, "operator source role schema"),
            (self.source_candidate_id, "operator source candidate"),
            (
                self.source_operator_semantics_id,
                "operator source semantics",
            ),
            (self.target_profile_id, "operator target profile"),
        ):
            _cid(value, field)
        source_semantics, source_candidate = next(
            (
                semantics,
                candidate,
            )
            for semantics, candidate in _operator_candidates(
                self.source_role_schema_id
            )
            if semantics.operator_kind
            is GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER
        )
        target_profile = anytime_variable_graph_profile_v1()
        if (
            self.source_candidate_id != source_candidate.candidate_id
            or self.source_operator_semantics_id
            != source_semantics.semantics_id
            or self.target_profile_id != target_profile.profile_id
            or self.target_checkpoints != CHECKPOINTS
            or self.target_checkpoints != target_profile.checkpoints
            or self.source_maximum_draws_per_row
            != source_semantics.maximum_draws_per_row
            or self.target_maximum_draws_per_row
            != target_profile.max_draws
            or self.target_maximum_draws_per_row
            != self.target_checkpoints[-1]
            or self.target_maximum_draws_per_row
            > self.source_maximum_draws_per_row
            or self.row_schedule != source_semantics.row_schedule
            or self.stopping_rule != source_semantics.stopping_rule
            or self.confidence_method_id
            != source_semantics.confidence_method_id
            or self.confidence_method_id != target_profile.method_id
            or self.confidence_alpha != source_semantics.confidence_alpha
            or self.confidence_alpha != target_profile.confidence_alpha
            or self.target_half_width != source_semantics.target_half_width
            or self.target_half_width != target_profile.target_half_width
            or self.cap_failure_terminal
            != AnytimeVariableGraphTerminal.FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP.value
            or self.target_cap_preregistered is not True
            or self.exact_profile_transfer_claimed is not False
            or self.operator_family_instantiation_only is not True
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "target operator is not a preregistered cap-narrowing "
                "instantiation of the selected source operator family"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v0067_target_sequential_operator_instantiation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "target_proposal_id": self.target_proposal_id,
            "target_context_id": self.target_context_id,
            "target_query_id": self.target_query_id,
            "source_role_schema_id": self.source_role_schema_id,
            "source_candidate_id": self.source_candidate_id,
            "source_operator_semantics_id": (
                self.source_operator_semantics_id
            ),
            "target_profile_id": self.target_profile_id,
            "target_checkpoints": list(self.target_checkpoints),
            "source_maximum_draws_per_row": (
                self.source_maximum_draws_per_row
            ),
            "target_maximum_draws_per_row": (
                self.target_maximum_draws_per_row
            ),
            "row_schedule": self.row_schedule,
            "stopping_rule": self.stopping_rule,
            "confidence_method_id": self.confidence_method_id,
            "confidence_alpha": _fdoc(self.confidence_alpha),
            "target_half_width": _fdoc(self.target_half_width),
            "cap_failure_terminal": self.cap_failure_terminal,
            "target_cap_preregistered": True,
            "exact_profile_transfer_claimed": False,
            "operator_family_instantiation_only": True,
        }

    @property
    def instantiation_id(self) -> str:
        return _content_id("operator_instantiation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "instantiation_id": self.instantiation_id,
        }


@dataclass(frozen=True, slots=True)
class GraphOccurrenceArmResultV1:
    occurrence: RegisteredGraphOccurrenceV1
    arm: FactorialArmV1
    confidence: ConfidenceContractV1
    work: OccurrenceSampleWorkV1
    acquired_ground_rows: int
    terminal_class: TerminalClass
    certificate_id: str
    evidence_verification_id: str
    exact_evaluation_id: str
    access_verification_id: str
    paired_seed_stream_id: str
    exact_failure_probability: Fraction
    exact_normalized_reward: Fraction
    normalized_regret: Fraction
    audit_covers_exact_objective_constraint: bool
    false_certificate_count: int
    source_prior_gate_id: str | None
    source_proposal_id: str | None
    source_prior_selected_this_arm: bool
    cold_occurrence_local_model: bool
    target_model_reused: bool
    target_operator_instantiation: (
        TargetSequentialOperatorInstantiationV1 | None
    ) = None
    raw_draw_replay_passed: bool = True
    target_local_certificate: bool = True
    exact_probabilities_used_by_statistical_model: bool = False
    direct_prefix_acquisition: bool = True
    operational_full_fixed_evidence_access_count: int = 0
    prefix_coupling_verified: bool = True
    known_exact_structural_support_reward_failure_labels: bool = True
    pretrained_source_skeleton_used: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.occurrence) is not RegisteredGraphOccurrenceV1
            or type(self.arm) is not FactorialArmV1
            or type(self.confidence) is not ConfidenceContractV1
            or type(self.work) is not OccurrenceSampleWorkV1
            or type(self.terminal_class) is not TerminalClass
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "occurrence arm result contains a runtime substitution"
            )
        for value, field in (
            (self.certificate_id, "arm certificate"),
            (self.evidence_verification_id, "arm evidence verification"),
            (self.exact_evaluation_id, "arm exact evaluation"),
            (self.access_verification_id, "arm access verification"),
            (self.paired_seed_stream_id, "arm paired seed stream"),
        ):
            _cid(value, field)
        _integer(self.acquired_ground_rows, "acquired ground rows", 1)
        context = next(
            item
            for item in REGISTERED_GRAPH_CONTEXTS
            if item.context_id == self.occurrence.context_id
        )
        is_negative = (
            context.context_key == "variable_negative_k6_minus_edge_v0"
        )
        expected_confidence_family = (
            ConfidenceFamily.QUOTIENT_FIXED
            if self.arm.planner is PlannerKind.QUOTIENT_RAPM
            and self.arm.stopping is StoppingMode.FIXED
            else (
                ConfidenceFamily.QUOTIENT_SEQUENTIAL
                if self.arm.planner is PlannerKind.QUOTIENT_RAPM
                else (
                    ConfidenceFamily.DIRECT_FIXED
                    if self.arm.stopping is StoppingMode.FIXED
                    else ConfidenceFamily.DIRECT_SEQUENTIAL
                )
            )
        )
        if (
            type(self.exact_failure_probability) is not Fraction
            or not 0 <= self.exact_failure_probability <= 1
            or type(self.exact_normalized_reward) is not Fraction
            or not 0 <= self.exact_normalized_reward <= 1
            or type(self.normalized_regret) is not Fraction
            or not 0 <= self.normalized_regret <= Fraction(1, 20)
            or self.exact_normalized_reward != Fraction(3, 64)
            or self.audit_covers_exact_objective_constraint is not True
            or self.false_certificate_count != 0
            or self.raw_draw_replay_passed is not True
            or self.target_local_certificate is not True
            or self.exact_probabilities_used_by_statistical_model is not False
            or self.direct_prefix_acquisition is not True
            or self.operational_full_fixed_evidence_access_count != 0
            or self.prefix_coupling_verified is not True
            or self.known_exact_structural_support_reward_failure_labels
            is not True
            or self.pretrained_source_skeleton_used
            is not (self.arm.planner is PlannerKind.QUOTIENT_RAPM)
            or self.confidence.family is not expected_confidence_family
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "arm certificate/evaluation obligations are not closed"
            )
        if (
            self.arm.proposal is ProposalMode.SOURCE_META_PRIOR
            and (
                self.source_prior_gate_id is None
                or _cid(self.source_prior_gate_id, "arm source prior")
                != self.source_prior_gate_id
                or self.source_proposal_id is None
                or _cid(self.source_proposal_id, "arm source proposal")
                != self.source_proposal_id
            )
        ) or (
            self.arm.proposal is ProposalMode.NO_PRIOR
            and (
                self.source_prior_gate_id is not None
                or self.source_proposal_id is not None
                or self.source_prior_selected_this_arm is not False
            )
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "source prior use does not match the factorial cell"
            )
        if (
            self.arm == META_PRIOR_SEQUENTIAL
            and self.source_prior_selected_this_arm is not True
        ) or (
            self.arm == META_PRIOR_FIXED
            and self.source_prior_selected_this_arm is not False
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "meta-prior selection and forced fixed ablation were conflated"
            )
        if self.arm == META_PRIOR_SEQUENTIAL:
            if (
                type(self.target_operator_instantiation)
                is not TargetSequentialOperatorInstantiationV1
                or self.target_operator_instantiation.target_proposal_id
                != self.source_proposal_id
                or self.target_operator_instantiation.target_context_id
                != self.occurrence.context_id
                or self.target_operator_instantiation.target_query_id
                != self.occurrence.query_id
            ):
                raise FactorialSampleEfficiencyInvariantViolation(
                    "meta-prior sequential cell lacks its typed target "
                    "operator instantiation"
                )
        elif self.target_operator_instantiation is not None:
            raise FactorialSampleEfficiencyInvariantViolation(
                "only the selected meta-prior sequential cell may bind a "
                "target operator instantiation"
            )
        if self.arm.planner is PlannerKind.COLD_DIRECT_GROUND:
            if (
                self.cold_occurrence_local_model is not True
                or self.target_model_reused is not False
            ):
                raise FactorialSampleEfficiencyInvariantViolation(
                    "matched direct route was not cold per occurrence"
                )
        elif self.cold_occurrence_local_model is not False:
            raise FactorialSampleEfficiencyInvariantViolation(
                "quotient arm was mislabeled as a cold direct route"
            )
        if is_negative:
            if (
                self.arm.planner is not PlannerKind.QUOTIENT_RAPM
                or self.terminal_class is not TerminalClass.PLAN_CERTIFICATE
                or self.exact_failure_probability
                >= context.risk_tolerance
                or self.work.fallback.exact_kernel_queries != 60
            ):
                raise FactorialSampleEfficiencyInvariantViolation(
                    "negative control must close as the matched feasible "
                    "60-row exact fallback under its registered delta"
                )
        elif (
            self.terminal_class is not TerminalClass.PLAN_CERTIFICATE
            or self.exact_failure_probability
            >= context.risk_tolerance
            or self.work.fallback.exact_kernel_queries != 0
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "positive sample endpoint must close as a feasible plan "
                "without an operational exact fallback"
            )
        if (
            self.work.target_acquisition.exact_kernel_queries
            != self.acquired_ground_rows
            or self.work.planning_and_certificate.exact_kernel_queries != 0
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "authoritative support-descriptor queries were omitted or "
                "charged outside target acquisition"
            )
        if self.arm == NO_PRIOR_FIXED:
            if (
                self.acquired_ground_rows
                != context.no_prior_fixed_acquisition_rows
                or self.work.acquisition_draws
                != self.acquired_ground_rows * FIXED_SAMPLE_COUNT_PER_ROW
            ):
                raise FactorialSampleEfficiencyInvariantViolation(
                    "no-prior fixed cell no longer reproduces V0-066 acquisition"
                )
        elif self.arm == DIRECT_FIXED:
            if (
                self.acquired_ground_rows
                != context.direct_fixed_acquisition_rows
                or self.work.acquisition_draws
                != self.acquired_ground_rows * FIXED_SAMPLE_COUNT_PER_ROW
            ):
                raise FactorialSampleEfficiencyInvariantViolation(
                    "fixed direct cell is not the full cold H2 graph support"
                )
        elif self.arm.stopping is StoppingMode.FIXED:
            if (
                self.work.acquisition_draws
                != self.acquired_ground_rows * FIXED_SAMPLE_COUNT_PER_ROW
            ):
                raise FactorialSampleEfficiencyInvariantViolation(
                    "fixed meta-prior arm did not use the fixed row budget"
                )
        else:
            if not 0 < self.work.acquisition_draws <= (
                self.acquired_ground_rows * FIXED_SAMPLE_COUNT_PER_ROW
            ):
                raise FactorialSampleEfficiencyInvariantViolation(
                    "sequential arm exceeded the fixed per-row cap"
                )

    @property
    def matched_oracle_authority(self) -> bool:
        expected_fallback = (
            60
            if self.occurrence.context_key
            == "variable_negative_k6_minus_edge_v0"
            else 0
        )
        return (
            self.work.target_acquisition.exact_kernel_queries
            == self.acquired_ground_rows
            and self.work.planning_and_certificate.exact_kernel_queries == 0
            and self.work.fallback.exact_kernel_queries == expected_fallback
            and self.exact_probabilities_used_by_statistical_model is False
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_occurrence_arm_result.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence.occurrence_id,
            "arm_id": self.arm.arm_id,
            "confidence_id": self.confidence.confidence_id,
            "work_id": self.work.work_id,
            "acquired_ground_rows": self.acquired_ground_rows,
            "terminal_class": self.terminal_class.value,
            "certificate_id": self.certificate_id,
            "evidence_verification_id": self.evidence_verification_id,
            "exact_evaluation_id": self.exact_evaluation_id,
            "access_verification_id": self.access_verification_id,
            "paired_seed_stream_id": self.paired_seed_stream_id,
            "exact_failure_probability": _fdoc(
                self.exact_failure_probability
            ),
            "exact_normalized_reward": _fdoc(
                self.exact_normalized_reward
            ),
            "normalized_regret": _fdoc(self.normalized_regret),
            "audit_covers_exact_objective_constraint": True,
            "false_certificate_count": 0,
            "source_prior_gate_id": self.source_prior_gate_id,
            "source_proposal_id": self.source_proposal_id,
            "source_prior_selected_this_arm": (
                self.source_prior_selected_this_arm
            ),
            "target_operator_instantiation_id": (
                None
                if self.target_operator_instantiation is None
                else self.target_operator_instantiation.instantiation_id
            ),
            "cold_occurrence_local_model": self.cold_occurrence_local_model,
            "target_model_reused": self.target_model_reused,
            "raw_draw_replay_passed": True,
            "target_local_certificate": True,
            "exact_probabilities_used_by_statistical_model": False,
            "direct_prefix_acquisition": True,
            "operational_full_fixed_evidence_access_count": 0,
            "prefix_coupling_verified": True,
            "known_exact_structural_support_reward_failure_labels": True,
            "pretrained_source_skeleton_used": (
                self.pretrained_source_skeleton_used
            ),
            "matched_oracle_authority": self.matched_oracle_authority,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence": self.occurrence.to_document(),
            "arm": self.arm.to_document(),
            "confidence": self.confidence.to_document(),
            "work": self.work.to_document(),
            "target_operator_instantiation": (
                None
                if self.target_operator_instantiation is None
                else self.target_operator_instantiation.to_document()
            ),
            "result_id": self.result_id,
        }


@dataclass(frozen=True, slots=True)
class ConfidenceReconciliationV1:
    authority_confidence_ids: tuple[str, ...]
    authority_profile_ids: tuple[str, ...]
    family_authority_counts: tuple[tuple[ConfidenceFamily, int], ...]
    family_obligation_counts: tuple[tuple[ConfidenceFamily, int], ...]
    family_tail_uppers: tuple[tuple[ConfidenceFamily, Fraction], ...]
    result_count: int
    deduplicated_authority_count: int
    joint_tail_upper: Fraction
    joint_confidence_lower: Fraction

    def __post_init__(self) -> None:
        expected_counts = (
            (ConfidenceFamily.QUOTIENT_FIXED, 1),
            (ConfidenceFamily.QUOTIENT_SEQUENTIAL, 3),
            (ConfidenceFamily.DIRECT_FIXED, 2),
            (ConfidenceFamily.DIRECT_SEQUENTIAL, 2),
        )
        expected_obligations = (
            (ConfidenceFamily.QUOTIENT_FIXED, 287),
            (ConfidenceFamily.QUOTIENT_SEQUENTIAL, 287),
            (ConfidenceFamily.DIRECT_FIXED, 198),
            (ConfidenceFamily.DIRECT_SEQUENTIAL, 198),
        )
        expected_tails = tuple(
            (family, Fraction(count, 250_000))
            for family, count in expected_obligations
        )
        if (
            self.authority_confidence_ids
            != tuple(sorted(set(self.authority_confidence_ids)))
            or self.authority_profile_ids
            != tuple(sorted(set(self.authority_profile_ids)))
            or len(self.authority_confidence_ids)
            != len(self.authority_profile_ids)
            or self.family_authority_counts != expected_counts
            or self.family_obligation_counts != expected_obligations
            or self.family_tail_uppers != expected_tails
            or self.result_count != 16
            or self.deduplicated_authority_count != 8
            or self.deduplicated_authority_count
            != len(self.authority_confidence_ids)
            or self.joint_tail_upper != Fraction(97, 25_000)
            or self.joint_tail_upper
            != sum(
                (tail for _, tail in self.family_tail_uppers),
                Fraction(0),
            )
            or self.joint_confidence_lower
            != 1 - self.joint_tail_upper
            or self.joint_confidence_lower != Fraction(24_903, 25_000)
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "simultaneous confidence authorities were duplicated, "
                "dropped, or failed family reconciliation"
            )
        for item in (
            *self.authority_confidence_ids,
            *self.authority_profile_ids,
        ):
            _cid(item, "confidence reconciliation authority")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_confidence_reconciliation.v1",
            "schema_version": SCHEMA_VERSION,
            "authority_confidence_ids": list(
                self.authority_confidence_ids
            ),
            "authority_profile_ids": list(self.authority_profile_ids),
            "family_authority_counts": [
                {"family": family.value, "count": count}
                for family, count in self.family_authority_counts
            ],
            "family_obligation_counts": [
                {"family": family.value, "count": count}
                for family, count in self.family_obligation_counts
            ],
            "family_tail_uppers": [
                {"family": family.value, "tail_upper": _fdoc(tail)}
                for family, tail in self.family_tail_uppers
            ],
            "result_count": self.result_count,
            "deduplicated_authority_count": (
                self.deduplicated_authority_count
            ),
            "joint_tail_upper": _fdoc(self.joint_tail_upper),
            "joint_confidence_lower": _fdoc(
                self.joint_confidence_lower
            ),
        }

    @property
    def reconciliation_id(self) -> str:
        return _content_id("confidence_reconciliation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciliation_id": self.reconciliation_id,
        }


def _reconcile_confidence_v1(
    results: tuple[GraphOccurrenceArmResultV1, ...],
) -> ConfidenceReconciliationV1:
    by_profile: dict[str, ConfidenceContractV1] = {}
    for item in results:
        previous = by_profile.get(item.confidence.certificate_profile_id)
        if (
            previous is not None
            and previous.confidence_id != item.confidence.confidence_id
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "one statistical authority was assigned incompatible "
                "confidence contracts"
            )
        by_profile[item.confidence.certificate_profile_id] = item.confidence
    authorities = tuple(by_profile.values())
    ordered_families = tuple(ConfidenceFamily)
    return ConfidenceReconciliationV1(
        tuple(sorted(item.confidence_id for item in authorities)),
        tuple(sorted(by_profile)),
        tuple(
            (
                family,
                sum(item.family is family for item in authorities),
            )
            for family in ordered_families
        ),
        tuple(
            (
                family,
                sum(
                    item.aggregate_obligation_count
                    for item in authorities
                    if item.family is family
                ),
            )
            for family in ordered_families
        ),
        tuple(
            (
                family,
                sum(
                    (
                        item.family_tail_upper
                        for item in authorities
                        if item.family is family
                    ),
                    Fraction(0),
                ),
            )
            for family in ordered_families
        ),
        len(results),
        len(authorities),
        sum(
            (item.family_tail_upper for item in authorities),
            Fraction(0),
        ),
        1
        - sum(
            (item.family_tail_upper for item in authorities),
            Fraction(0),
        ),
    )


@dataclass(frozen=True, slots=True)
class FactorialSampleEfficiencyPreregistrationV1:
    occurrences: tuple[RegisteredGraphOccurrenceV1, ...]
    arms: tuple[FactorialArmV1, ...]
    source_prior_gate_id: str
    claim_scope_id: str
    confidence_budget_id: str
    primary_endpoint: str = "CERTIFIED_TARGET_GENERATIVE_DRAWS"
    fixed_historical_acquisition_draws_per_replica: int = 18_612_224
    fixed_positive_acquisition_draws_per_replica: int = 10_747_904
    fixed_direct_acquisition_draws_per_replica: int = 11_796_480
    all_registered_cells_in_closure_denominator: bool = True
    negative_control_excluded_from_draw_endpoint: bool = True
    negative_exact_fallback_rows_per_cell: int = 60

    def __post_init__(self) -> None:
        if (
            type(self.occurrences) is not tuple
            or not self.occurrences
            or any(
                type(item) is not RegisteredGraphOccurrenceV1
                for item in self.occurrences
            )
            or tuple(
                (
                    item.replica_index,
                    next(
                        index
                        for index, context in enumerate(
                            REGISTERED_GRAPH_CONTEXTS
                        )
                        if context.context_id == item.context_id
                    ),
                )
                for item in self.occurrences
            )
            != tuple(
                sorted(
                    (
                        item.replica_index,
                        next(
                            index
                            for index, context in enumerate(
                                REGISTERED_GRAPH_CONTEXTS
                            )
                            if context.context_id == item.context_id
                        ),
                    )
                    for item in self.occurrences
                )
            )
            or len({item.occurrence_id for item in self.occurrences})
            != len(self.occurrences)
            or self.replica_count != 1
            or any(
                sum(
                    item.replica_index == replica
                    and item.context_id == context.context_id
                    for item in self.occurrences
                )
                != 1
                for replica in range(1, self.replica_count + 1)
                for context in REGISTERED_GRAPH_CONTEXTS
            )
            or type(self.arms) is not tuple
            or self.arms != REGISTERED_ARMS
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "preregistration is not the complete ordered 4+2 V0-066 design"
            )
        for value, field in (
            (self.source_prior_gate_id, "preregistered source prior"),
            (self.claim_scope_id, "preregistered claim scope"),
            (self.confidence_budget_id, "preregistered confidence budget"),
        ):
            _cid(value, field)
        if (
            self.primary_endpoint != "CERTIFIED_TARGET_GENERATIVE_DRAWS"
            or self.fixed_historical_acquisition_draws_per_replica
            != 18_612_224
            or self.fixed_positive_acquisition_draws_per_replica
            != 10_747_904
            or self.fixed_direct_acquisition_draws_per_replica
            != 11_796_480
            or self.all_registered_cells_in_closure_denominator is not True
            or self.negative_control_excluded_from_draw_endpoint is not True
            or self.negative_exact_fallback_rows_per_cell != 60
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "sample Gate endpoint or historical controls changed"
            )

    @property
    def replica_count(self) -> int:
        return max(item.replica_index for item in self.occurrences)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_factorial_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_ids": [
                item.occurrence_id for item in self.occurrences
            ],
            "arm_ids": [item.arm_id for item in self.arms],
            "source_prior_gate_id": self.source_prior_gate_id,
            "claim_scope_id": self.claim_scope_id,
            "confidence_budget_id": self.confidence_budget_id,
            "primary_endpoint": self.primary_endpoint,
            "fixed_historical_acquisition_draws_per_replica": (
                self.fixed_historical_acquisition_draws_per_replica
            ),
            "fixed_positive_acquisition_draws_per_replica": (
                self.fixed_positive_acquisition_draws_per_replica
            ),
            "fixed_direct_acquisition_draws_per_replica": (
                self.fixed_direct_acquisition_draws_per_replica
            ),
            "all_registered_cells_in_closure_denominator": True,
            "negative_control_excluded_from_draw_endpoint": True,
            "negative_exact_fallback_rows_per_cell": 60,
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrences": [
                item.to_document() for item in self.occurrences
            ],
            "arms": [item.to_document() for item in self.arms],
            "replica_count": self.replica_count,
            "preregistration_id": self.preregistration_id,
        }


@dataclass(frozen=True, slots=True)
class FactorialArmSummaryV1:
    arm: FactorialArmV1
    occurrence_count: int
    acquisition_draws: int
    operational_target_draws: int
    certified_target_draws: int
    positive_certified_target_draws: int
    negative_control_certified_target_draws: int
    exact_kernel_queries: int
    negative_control_exact_kernel_queries: int
    plan_certificate_count: int
    infeasibility_certificate_count: int
    false_certificate_count: int
    per_context_certified_draws: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if type(self.arm) is not FactorialArmV1:
            raise FactorialSampleEfficiencyInvariantViolation(
                "arm summary uses a substituted arm"
            )
        for value, field in (
            (self.occurrence_count, "summary occurrences"),
            (self.acquisition_draws, "summary acquisition draws"),
            (self.operational_target_draws, "summary operational draws"),
            (self.certified_target_draws, "summary certified draws"),
            (
                self.positive_certified_target_draws,
                "summary positive certified draws",
            ),
            (
                self.negative_control_certified_target_draws,
                "summary negative certified draws",
            ),
            (self.exact_kernel_queries, "summary exact queries"),
            (
                self.negative_control_exact_kernel_queries,
                "summary negative exact queries",
            ),
            (self.plan_certificate_count, "summary plan certificates"),
            (
                self.infeasibility_certificate_count,
                "summary infeasibility certificates",
            ),
            (self.false_certificate_count, "summary false certificates"),
        ):
            _integer(value, field)
        if (
            self.occurrence_count <= 0
            or self.operational_target_draws < self.acquisition_draws
            or self.certified_target_draws < self.operational_target_draws
            or self.certified_target_draws
            != self.positive_certified_target_draws
            + self.negative_control_certified_target_draws
            or self.plan_certificate_count
            + self.infeasibility_certificate_count
            != self.occurrence_count
            or self.false_certificate_count != 0
            or type(self.per_context_certified_draws) is not tuple
            or tuple(key for key, _ in self.per_context_certified_draws)
            != tuple(item.context_key for item in REGISTERED_GRAPH_CONTEXTS)
            or any(
                type(value) is not int or value < 0
                for _, value in self.per_context_certified_draws
            )
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "arm summary lost work or closure accounting"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_factorial_arm_summary.v1",
            "schema_version": SCHEMA_VERSION,
            "arm_id": self.arm.arm_id,
            "occurrence_count": self.occurrence_count,
            "acquisition_draws": self.acquisition_draws,
            "operational_target_draws": self.operational_target_draws,
            "certified_target_draws": self.certified_target_draws,
            "positive_certified_target_draws": (
                self.positive_certified_target_draws
            ),
            "negative_control_certified_target_draws": (
                self.negative_control_certified_target_draws
            ),
            "exact_kernel_queries": self.exact_kernel_queries,
            "negative_control_exact_kernel_queries": (
                self.negative_control_exact_kernel_queries
            ),
            "plan_certificate_count": self.plan_certificate_count,
            "infeasibility_certificate_count": (
                self.infeasibility_certificate_count
            ),
            "false_certificate_count": 0,
            "per_context_certified_draws": [
                {"context_key": key, "draws": value}
                for key, value in self.per_context_certified_draws
            ],
        }

    @property
    def summary_id(self) -> str:
        return _content_id("summary", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "summary_id": self.summary_id}


@dataclass(frozen=True, slots=True)
class FactorialSampleEfficiencyGateResultV1:
    preregistration_id: str
    source_prior_gate_id: str
    result_ids: tuple[str, ...]
    summaries: tuple[FactorialArmSummaryV1, ...]
    all_occurrences_closed: bool
    equal_confidence_contract: bool
    confidence_reconciliation: ConfidenceReconciliationV1
    prefix_only_access_verified: bool
    matched_oracle_authority: bool
    exact_objective_constraint_preservation: bool
    exact_risk_equality_claimed: bool
    fixed_v0066_acquisition_reproduced: bool
    fixed_direct_control_reproduced: bool
    sequential_main_effect: bool
    meta_selection_valid: bool
    meta_prior_main_effect: bool
    meta_prior_target_savings_claimed: bool
    combined_online_advantage: bool
    per_context_no_harm: bool
    online_gate_passed: bool
    offline_source_draws: int
    offline_inclusive_break_even_occurrence: int | None
    offline_inclusive_gate_passed: bool
    offline_inclusive_status: str
    registered_positive_target_generative_draw_efficiency: bool
    historical_v0066_exact_fallback_detected: bool
    claim_scope: str
    no_prior_means_no_operator_metaprior_only: bool = True
    pretrained_source_skeleton_used_by_all_quotient_arms: bool = True
    broad_generalization_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_n_break_even: None = None

    def __post_init__(self) -> None:
        _cid(self.preregistration_id, "Gate preregistration")
        _cid(self.source_prior_gate_id, "Gate source prior")
        if (
            type(self.result_ids) is not tuple
            or not self.result_ids
            or self.result_ids != tuple(sorted(set(self.result_ids)))
            or type(self.summaries) is not tuple
            or tuple(item.arm for item in self.summaries)
            != REGISTERED_ARMS
            or type(self.confidence_reconciliation)
            is not ConfidenceReconciliationV1
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "Gate result identity or summary coverage changed"
            )
        for item in self.result_ids:
            _cid(item, "Gate occurrence result")
        _integer(self.offline_source_draws, "Gate offline draws")
        if self.offline_inclusive_break_even_occurrence is not None:
            _integer(
                self.offline_inclusive_break_even_occurrence,
                "Gate break-even occurrence",
                1,
            )
        expected_online = all(
            (
                self.all_occurrences_closed,
                self.equal_confidence_contract,
                self.prefix_only_access_verified,
                self.matched_oracle_authority,
                self.exact_objective_constraint_preservation,
                self.fixed_v0066_acquisition_reproduced,
                self.fixed_direct_control_reproduced,
                self.sequential_main_effect,
                self.meta_selection_valid,
                self.combined_online_advantage,
                self.per_context_no_harm,
            )
        )
        expected_offline = self.offline_inclusive_break_even_occurrence is not None
        if (
            self.online_gate_passed is not expected_online
            or self.offline_inclusive_gate_passed is not expected_offline
            or self.offline_inclusive_status
            != (
                "ESTABLISHED"
                if expected_offline
                else "NOT_ESTABLISHED"
            )
            or self.registered_positive_target_generative_draw_efficiency
            is not expected_online
            or self.exact_risk_equality_claimed is not False
            or self.meta_prior_target_savings_claimed is not False
            or self.claim_scope
            != REGISTERED_CLAIM_SCOPE
            or self.no_prior_means_no_operator_metaprior_only is not True
            or self.pretrained_source_skeleton_used_by_all_quotient_arms
            is not True
            or self.broad_generalization_claimed is not False
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_n_break_even is not None
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "Gate conclusion exceeds its verified finite claim"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_factorial_gate_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "source_prior_gate_id": self.source_prior_gate_id,
            "result_ids": list(self.result_ids),
            "summary_ids": [item.summary_id for item in self.summaries],
            "all_occurrences_closed": self.all_occurrences_closed,
            "equal_confidence_contract": self.equal_confidence_contract,
            "confidence_reconciliation_id": (
                self.confidence_reconciliation.reconciliation_id
            ),
            "joint_tail_upper": _fdoc(
                self.confidence_reconciliation.joint_tail_upper
            ),
            "joint_confidence_lower": _fdoc(
                self.confidence_reconciliation.joint_confidence_lower
            ),
            "prefix_only_access_verified": (
                self.prefix_only_access_verified
            ),
            "matched_oracle_authority": self.matched_oracle_authority,
            "exact_objective_constraint_preservation": (
                self.exact_objective_constraint_preservation
            ),
            "exact_risk_equality_claimed": False,
            "fixed_v0066_acquisition_reproduced": (
                self.fixed_v0066_acquisition_reproduced
            ),
            "fixed_direct_control_reproduced": (
                self.fixed_direct_control_reproduced
            ),
            "sequential_main_effect": self.sequential_main_effect,
            "meta_selection_valid": self.meta_selection_valid,
            "meta_prior_main_effect": self.meta_prior_main_effect,
            "meta_prior_target_savings_claimed": False,
            "combined_online_advantage": self.combined_online_advantage,
            "per_context_no_harm": self.per_context_no_harm,
            "online_gate_passed": self.online_gate_passed,
            "offline_source_draws": self.offline_source_draws,
            "offline_inclusive_break_even_occurrence": (
                self.offline_inclusive_break_even_occurrence
            ),
            "offline_inclusive_gate_passed": (
                self.offline_inclusive_gate_passed
            ),
            "offline_inclusive_status": self.offline_inclusive_status,
            "registered_positive_target_generative_draw_efficiency": (
                self.registered_positive_target_generative_draw_efficiency
            ),
            "historical_v0066_exact_fallback_detected": (
                self.historical_v0066_exact_fallback_detected
            ),
            "claim_scope": self.claim_scope,
            "no_prior_means_no_operator_metaprior_only": True,
            "pretrained_source_skeleton_used_by_all_quotient_arms": True,
            "broad_generalization_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
        }

    @property
    def gate_result_id(self) -> str:
        return _content_id("gate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "summaries": [item.to_document() for item in self.summaries],
            "confidence_reconciliation": (
                self.confidence_reconciliation.to_document()
            ),
            "gate_result_id": self.gate_result_id,
        }


def build_registered_graph_occurrences_v1(
    query_ids_by_context: Mapping[str, str],
    replica_count: int,
) -> tuple[RegisteredGraphOccurrenceV1, ...]:
    """Freeze the paired occurrence order before any arm observes a draw."""

    _integer(replica_count, "replica count", 1)
    if (
        type(query_ids_by_context) is not dict
        or set(query_ids_by_context)
        != {item.context_key for item in REGISTERED_GRAPH_CONTEXTS}
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "every V0-066 context requires one frozen QuerySpec ID"
        )
    return tuple(
        RegisteredGraphOccurrenceV1(
            context.context_key,
            context.context_id,
            _cid(
                query_ids_by_context[context.context_key],
                f"{context.context_key} query",
            ),
            replica_index,
        )
        for replica_index in range(1, replica_count + 1)
        for context in REGISTERED_GRAPH_CONTEXTS
    )


def paired_graph_seed_stream_id_v1(
    occurrence: RegisteredGraphOccurrenceV1,
) -> str:
    """Identity shared by fixed/sequential arms using V0-066 row prefixes."""

    if type(occurrence) is not RegisteredGraphOccurrenceV1:
        raise FactorialSampleEfficiencyInvariantViolation(
            "paired seed stream requires a registered graph occurrence"
        )
    return _content_id(
        "paired_seed",
        {
            "schema": "acfqp.v0067_paired_graph_seed_stream.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": occurrence.context_id,
            "query_id": occurrence.query_id,
            "replica_index": occurrence.replica_index,
            "row_seed_semantics": (
                "v0066_splitmix64_row_seed_prefix_common_random_numbers"
            ),
            "fixed_full_replay_lane": "STANDALONE_EVALUATION_AFTER_FREEZE",
        },
    )


def build_source_prior_gate_evidence_v1(
    prior: Any,
    proposals: tuple[Any, ...],
    verifications: tuple[Any, ...],
) -> SourcePriorGateEvidenceV1:
    """Adapt the proposal-only meta-prior authority into the Gate.

    Imports are local so the factorial schema remains usable by no-prior
    diagnostics without importing the proposal builder.
    """

    from acfqp.proposal_only_metaprior_v1 import (
        ProposalOnlyMetaPriorVerificationV1,
        ProposalOnlyRankingV1,
        ProposalStatus,
        SourceConsensusMetaPriorV1,
    )

    if (
        type(prior) is not SourceConsensusMetaPriorV1
        or type(proposals) is not tuple
        or type(verifications) is not tuple
        or len(proposals) != len(REGISTERED_GRAPH_CONTEXTS)
        or len(verifications) != len(proposals)
        or any(type(item) is not ProposalOnlyRankingV1 for item in proposals)
        or any(
            type(item) is not ProposalOnlyMetaPriorVerificationV1
            for item in verifications
        )
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "source prior Gate adapter requires complete typed authorities"
        )
    target_ids = tuple(sorted(item.target_context_id for item in proposals))
    expected_targets = tuple(
        sorted(item.context_id for item in REGISTERED_GRAPH_CONTEXTS)
    )
    proposal_ids = {item.proposal_id for item in proposals}
    if (
        target_ids != expected_targets
        or len(set(target_ids)) != len(target_ids)
        or any(
            item.status is not ProposalStatus.PROPOSAL_READY
            or item.prior_id != prior.prior_id
            or not item.selected_candidate_ids
            or item.offline_accounting != prior.offline_accounting
            or item.online_accounting.generative_draw_count != 0
            or item.online_accounting.exact_kernel_call_count != 0
            for item in proposals
        )
        or {item.proposal_id for item in verifications} != proposal_ids
        or any(
            item.prior_id != prior.prior_id
            or item.status is not ProposalStatus.PROPOSAL_READY
            or item.certificate_verified
            for item in verifications
        )
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "source prior proposal/verification coverage is incomplete"
        )
    accounting = prior.offline_accounting
    source_work = EvidenceEventVectorV1(
        "OFFLINE_SOURCE",
        accounting.environment_interaction_count,
        accounting.generative_draw_count,
        accounting.exact_kernel_call_count,
        accounting.logged_observation_count,
        0,
    )
    return SourcePriorGateEvidenceV1(
        prior.prior_id,
        prior.source_context_ids,
        target_ids,
        source_work,
        source_work,
        EvidenceEventVectorV1.zero("OFFLINE_SOURCE"),
        tuple(sorted(item.verification_id for item in verifications)),
    )


def build_v0066_source_prior_gate_evidence_v1(
    campaign: Any,
    verification: Any,
) -> SourcePriorGateEvidenceV1:
    """Typed adapter for the concrete V0-066 graph acquisition meta-prior."""

    from acfqp.v0066_graph_acquisition_metaprior_v1 import (
        V0066GraphAcquisitionMetaPriorCampaignV1,
        V0066GraphAcquisitionMetaPriorVerificationV1,
    )

    if (
        type(campaign) is not V0066GraphAcquisitionMetaPriorCampaignV1
        or type(verification)
        is not V0066GraphAcquisitionMetaPriorVerificationV1
        or verification.campaign_id != campaign.campaign_id
        or verification.source_prior_id != campaign.source_prior.prior_id
        or verification.source_evidence_id
        != campaign.source_evidence.evidence_id
        or campaign.source_only_nonneutral_proxy_ranking is not True
        or campaign.end_to_end_operator_ranking_claimed is not False
        or verification.nonneutral_source_proxy_ordering_replayed
        is not True
        or verification.source_proxy_noncertification_verified is not True
        or set(verification.verified_target_proposal_ids)
        != {
            item.target_proposal_id
            for item in campaign.target_proposals
        }
        or any(
            item.expected_selected_candidate_id
            != campaign.source_evidence.sequential_candidate_id
            for item in campaign.target_proposals
        )
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "concrete V0-066 source meta-prior failed typed Gate adaptation"
        )
    accounting = campaign.source_prior.offline_accounting
    return SourcePriorGateEvidenceV1(
        campaign.source_prior.prior_id,
        campaign.source_prior.source_context_ids,
        tuple(
            sorted(
                item.applicability.target_context_id
                for item in campaign.target_proposals
            )
        ),
        EvidenceEventVectorV1(
            "OFFLINE_SOURCE",
            accounting.environment_interaction_count,
            accounting.generative_draw_count,
            accounting.exact_kernel_call_count,
            0,
            0,
        ),
        EvidenceEventVectorV1(
            "OFFLINE_SOURCE",
            0,
            campaign.source_evidence.fixed_arm_draws,
            len(campaign.source_evidence.trials),
            0,
            0,
        ),
        EvidenceEventVectorV1(
            "OFFLINE_SOURCE",
            0,
            0,
            len(campaign.source_log.rows),
            0,
            0,
        ),
        (verification.verification_id,),
    )


def adapt_direct_sequential_result_v1(
    preregistration: FactorialSampleEfficiencyPreregistrationV1,
    occurrence: RegisteredGraphOccurrenceV1,
    result: Any,
    verification: Any,
) -> GraphOccurrenceArmResultV1:
    """Convert a verified cold direct runner result into one Gate cell."""

    from acfqp.variable_graph_direct_sequential_v1 import (
        DirectSequentialResultV1,
        DirectSequentialVerificationV1,
    )

    if (
        type(preregistration)
        is not FactorialSampleEfficiencyPreregistrationV1
        or occurrence not in preregistration.occurrences
        or type(result) is not DirectSequentialResultV1
        or type(verification) is not DirectSequentialVerificationV1
        or occurrence.context_id != result.context.context_id
        or verification.result_id != result.result_id
        or verification.replayed_evaluation_id
        != result.evaluation.evaluation_id
        or set(verification.replayed_row_ids)
        != {item.row_id for item in result.rows}
        or tuple(verification.replayed_audit_ids)
        != tuple(item.audit_id for item in result.audits)
        or result.profile.registered_family_tail_upper
        > REGISTERED_FAMILY_TAIL_UPPER
        or result.full_v0066_row_access_count != 0
        or result.operational_exact_probability_reads != 0
        or result.operational_exact_kernel_queries
        != result.acquired_ground_rows
        or verification.replayed_operational_exact_kernel_queries
        != len(verification.replayed_row_ids)
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "cold direct sequential result failed typed Gate adaptation"
        )
    regret = max(
        Fraction(0),
        Fraction(3, 64) - result.evaluation.exact_normalized_reward,
    )
    return GraphOccurrenceArmResultV1(
        occurrence=occurrence,
        arm=DIRECT_SEQUENTIAL,
        confidence=ConfidenceContractV1(
            preregistration.claim_scope_id,
            preregistration.confidence_budget_id,
            result.profile.profile_id,
            ConfidenceFamily.DIRECT_SEQUENTIAL,
            result.profile.context_aggregate_obligation_count,
            result.profile.per_obligation_alpha,
            result.profile.context_tail_upper,
            1 - result.profile.context_tail_upper,
            (
                "CONDITIONAL_ON_REGISTERED_COUNTER_STREAM_"
                "IID_SIMULATOR_ASSUMPTION"
            ),
        ),
        work=OccurrenceSampleWorkV1(
            EvidenceEventVectorV1(
                "ONLINE_TARGET",
                0,
                result.target_generative_draws,
                result.operational_exact_kernel_queries,
                0,
                0,
            ),
            EvidenceEventVectorV1.zero("OPERATIONAL_QUERY"),
            EvidenceEventVectorV1.zero("OPERATIONAL_QUERY"),
            EvidenceEventVectorV1(
                "STANDALONE_EVALUATION",
                0,
                0,
                (
                    verification.replayed_operational_exact_kernel_queries
                    + result.evaluation.exact_policy_rows_evaluated
                ),
                0,
                0,
            ),
        ),
        acquired_ground_rows=result.acquired_ground_rows,
        terminal_class=TerminalClass.PLAN_CERTIFICATE,
        certificate_id=result.final_audit.audit_id,
        evidence_verification_id=verification.verification_id,
        exact_evaluation_id=result.evaluation.evaluation_id,
        access_verification_id=verification.verification_id,
        paired_seed_stream_id=paired_graph_seed_stream_id_v1(occurrence),
        exact_failure_probability=(
            result.evaluation.exact_failure_probability
        ),
        exact_normalized_reward=(
            result.evaluation.exact_normalized_reward
        ),
        normalized_regret=regret,
        audit_covers_exact_objective_constraint=(
            result.evaluation.audit_covers_exact_policy
        ),
        false_certificate_count=0,
        source_prior_gate_id=None,
        source_proposal_id=None,
        source_prior_selected_this_arm=False,
        cold_occurrence_local_model=True,
        target_model_reused=False,
        raw_draw_replay_passed=verification.raw_prefix_replay_passed,
        target_local_certificate=True,
        exact_probabilities_used_by_statistical_model=False,
        direct_prefix_acquisition=True,
        operational_full_fixed_evidence_access_count=(
            result.full_v0066_row_access_count
        ),
        prefix_coupling_verified=(
            verification.no_full_evidence_access_passed
            and verification.first_certificate_stopping_passed
        ),
    )


def adapt_direct_fixed_result_v1(
    preregistration: FactorialSampleEfficiencyPreregistrationV1,
    occurrence: RegisteredGraphOccurrenceV1,
    result: Any,
    verification: Any,
) -> GraphOccurrenceArmResultV1:
    """Convert a verified cold fixed-sample direct result into one Gate cell."""

    from acfqp.variable_graph_direct_fixed_v1 import (
        DirectFixedResultV1,
        DirectFixedVerificationV1,
    )

    if (
        type(preregistration)
        is not FactorialSampleEfficiencyPreregistrationV1
        or occurrence not in preregistration.occurrences
        or type(result) is not DirectFixedResultV1
        or type(verification) is not DirectFixedVerificationV1
        or occurrence.context_id != result.context.context_id
        or verification.result_id != result.result_id
        or tuple(verification.replayed_row_ids)
        != tuple(sorted(item.row_id for item in result.rows))
        or tuple(verification.replayed_paired_stream_ids)
        != tuple(sorted(item.paired_stream_id for item in result.rows))
        or verification.replayed_audit_id != result.audit.audit_id
        or verification.evaluation.result_id != result.result_id
        or result.v0066_packed_row_access_count != 0
        or result.operational_exact_probability_reads != 0
        or result.operational_exact_kernel_queries
        != result.acquired_ground_rows
        or verification.replayed_operational_exact_kernel_queries
        != len(verification.replayed_row_ids)
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "cold direct fixed result failed typed Gate adaptation"
        )
    regret = max(
        Fraction(0),
        Fraction(3, 64)
        - verification.evaluation.exact_normalized_reward,
    )
    return GraphOccurrenceArmResultV1(
        occurrence=occurrence,
        arm=DIRECT_FIXED,
        confidence=ConfidenceContractV1(
            preregistration.claim_scope_id,
            preregistration.confidence_budget_id,
            result.profile.profile_id,
            ConfidenceFamily.DIRECT_FIXED,
            result.profile.context_aggregate_obligation_count,
            result.profile.per_obligation_tail_upper,
            result.profile.context_tail_upper,
            1 - result.profile.context_tail_upper,
            (
                "CONDITIONAL_ON_REGISTERED_COUNTER_STREAM_"
                "IID_SIMULATOR_ASSUMPTION"
            ),
        ),
        work=OccurrenceSampleWorkV1(
            EvidenceEventVectorV1(
                "ONLINE_TARGET",
                0,
                result.target_generative_draws,
                result.operational_exact_kernel_queries,
                0,
                0,
            ),
            EvidenceEventVectorV1.zero("OPERATIONAL_QUERY"),
            EvidenceEventVectorV1.zero("OPERATIONAL_QUERY"),
            EvidenceEventVectorV1(
                "STANDALONE_EVALUATION",
                0,
                0,
                (
                    verification.replayed_operational_exact_kernel_queries
                    + verification.evaluation.evaluation_exact_kernel_calls
                ),
                0,
                0,
            ),
        ),
        acquired_ground_rows=result.acquired_ground_rows,
        terminal_class=TerminalClass.PLAN_CERTIFICATE,
        certificate_id=result.audit.audit_id,
        evidence_verification_id=verification.verification_id,
        exact_evaluation_id=verification.evaluation.evaluation_id,
        access_verification_id=verification.verification_id,
        paired_seed_stream_id=paired_graph_seed_stream_id_v1(occurrence),
        exact_failure_probability=(
            verification.evaluation.exact_failure_probability
        ),
        exact_normalized_reward=(
            verification.evaluation.exact_normalized_reward
        ),
        normalized_regret=regret,
        audit_covers_exact_objective_constraint=(
            verification.evaluation.audit_covers_exact_policy
        ),
        false_certificate_count=0,
        source_prior_gate_id=None,
        source_proposal_id=None,
        source_prior_selected_this_arm=False,
        cold_occurrence_local_model=True,
        target_model_reused=False,
        raw_draw_replay_passed=verification.raw_replay_passed,
        target_local_certificate=True,
        exact_probabilities_used_by_statistical_model=False,
        direct_prefix_acquisition=(
            verification.no_v0066_packed_row_access_passed
        ),
        operational_full_fixed_evidence_access_count=(
            result.v0066_packed_row_access_count
        ),
        prefix_coupling_verified=(
            verification.raw_replay_passed
            and verification.complete_closure_passed
            and verification.no_v0066_packed_row_access_passed
            and verification.operational_evaluation_separation_passed
        ),
    )


def adapt_anytime_quotient_result_v1(
    preregistration: FactorialSampleEfficiencyPreregistrationV1,
    occurrence: RegisteredGraphOccurrenceV1,
    result: Any,
    verification: Any,
    *,
    source_prior: SourcePriorGateEvidenceV1 | None = None,
    target_proposal: Any | None = None,
) -> GraphOccurrenceArmResultV1:
    """Convert one verified prefix-native quotient result into a Gate cell."""

    from acfqp.anytime_variable_graph_runner_v1 import (
        CHECKPOINTS,
        AnytimeVariableGraphResultV1,
        AnytimeVariableGraphTerminal,
        AnytimeVariableGraphVerificationV1,
    )
    from acfqp.v0066_graph_acquisition_metaprior_v1 import (
        GraphAcquisitionOperatorKind,
        GraphTargetAcquisitionProposalV1,
        _operator_candidates,
    )

    if (
        type(preregistration)
        is not FactorialSampleEfficiencyPreregistrationV1
        or occurrence not in preregistration.occurrences
        or type(result) is not AnytimeVariableGraphResultV1
        or type(verification) is not AnytimeVariableGraphVerificationV1
        or occurrence.context_id != result.context.context_id
        or verification.result_id != result.result_id
        or verification.context_id != occurrence.context_id
        or verification.replayed_prefix_rows
        != result.final_evidence.ground_row_count
        or verification.replayed_prefix_rows
        != result.counters.target_ground_rows
        or verification.replayed_ordinal_draws
        != result.final_evidence.generative_draw_count
        or verification.replayed_ordinal_draws
        != result.counters.target_ordinal_draws
        or result.conditional_family_tail_upper
        > REGISTERED_FAMILY_TAIL_UPPER
        or result.counters.full_131072_rows_materialized != 0
        or result.counters.v0066_full_evidence_constructor_calls != 0
        or result.counters.v0066_full_profile_reads != 0
        or result.counters.structural_support_kernel_calls
        != result.counters.target_ground_rows
        or result.counters.operational_exact_kernel_queries
        != (
            result.counters.structural_support_kernel_calls
            + result.counters.fallback_exact_ground_rows
        )
        or verification.replayed_structural_support_kernel_calls
        != verification.replayed_prefix_rows
        or verification.verified_operational_exact_kernel_queries
        != result.counters.operational_exact_kernel_queries
        or verification.actual_verifier_exact_kernel_queries
        != (
            verification.replayed_structural_support_kernel_calls
            + verification.evaluation_exact_kernel_calls
        )
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "anytime quotient result failed typed prefix/evaluation binding"
        )

    meta_cell = source_prior is not None or target_proposal is not None
    if meta_cell:
        sequential_semantics, sequential_candidate = next(
            (semantics, candidate)
            for semantics, candidate in _operator_candidates(
                target_proposal.applicability.role_schema_id
            )
            if semantics.operator_kind
            is GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER
        ) if type(target_proposal) is GraphTargetAcquisitionProposalV1 else (
            None,
            None,
        )
        if (
            type(source_prior) is not SourcePriorGateEvidenceV1
            or source_prior.gate_prior_id
            != preregistration.source_prior_gate_id
            or type(target_proposal)
            is not GraphTargetAcquisitionProposalV1
            or target_proposal.context_id != occurrence.context_id
            or target_proposal.query_id != occurrence.query_id
            or target_proposal.proposal.prior_id != source_prior.prior_id
            or target_proposal.proposal.selected_candidate_ids
            != (target_proposal.expected_selected_candidate_id,)
            or target_proposal.expected_selected_candidate_id
            != sequential_candidate.candidate_id
            or sequential_semantics.stopping_rule
            != "first_sound_plan_certificate_or_cap"
            or sequential_semantics.confidence_method_id
            != result.sequential_profile.method_id
            or sequential_semantics.confidence_alpha
            != result.sequential_profile.confidence_alpha
            or sequential_semantics.target_half_width
            != result.sequential_profile.target_half_width
            or result.sequential_profile.max_draws
            > sequential_semantics.maximum_draws_per_row
            or result.sequential_profile.max_draws
            != CHECKPOINTS[-1]
            or result.sequential_profile.checkpoints != CHECKPOINTS
            or result.first_certificate_stopping is not True
            or target_proposal.target_dynamics_rows != 0
            or target_proposal.target_outcome_labels != 0
            or target_proposal.target_reward_labels != 0
            or target_proposal.target_certificate_labels != 0
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "meta-prior proposal was not isolated and bound to the "
                "prefix-native sequential operator"
            )
        arm = META_PRIOR_SEQUENTIAL
        prior_id = source_prior.gate_prior_id
        proposal_id = target_proposal.target_proposal_id
        selected = True
        operator_instantiation = TargetSequentialOperatorInstantiationV1(
            target_proposal_id=target_proposal.target_proposal_id,
            target_context_id=target_proposal.context_id,
            target_query_id=target_proposal.query_id,
            source_role_schema_id=(
                target_proposal.applicability.role_schema_id
            ),
            source_candidate_id=sequential_candidate.candidate_id,
            source_operator_semantics_id=(
                sequential_semantics.semantics_id
            ),
            target_profile_id=result.sequential_profile.profile_id,
            target_checkpoints=result.sequential_profile.checkpoints,
            source_maximum_draws_per_row=(
                sequential_semantics.maximum_draws_per_row
            ),
            target_maximum_draws_per_row=(
                result.sequential_profile.max_draws
            ),
            row_schedule=sequential_semantics.row_schedule,
            stopping_rule=sequential_semantics.stopping_rule,
            confidence_method_id=(
                sequential_semantics.confidence_method_id
            ),
            confidence_alpha=result.sequential_profile.confidence_alpha,
            target_half_width=result.sequential_profile.target_half_width,
            cap_failure_terminal=(
                AnytimeVariableGraphTerminal
                .FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP.value
            ),
        )
    else:
        arm = NO_PRIOR_SEQUENTIAL
        prior_id = None
        proposal_id = None
        selected = False
        operator_instantiation = None

    is_negative = (
        occurrence.context_key == "variable_negative_k6_minus_edge_v0"
    )
    if is_negative:
        if (
            result.terminal
            is not AnytimeVariableGraphTerminal.FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP
            or result.fallback_proof is None
            or result.fallback_proof.complete_matched_query_search is not True
            or result.counters.fallback_exact_ground_rows != 60
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "negative anytime cell lacks its complete 60-row fallback"
            )
        certificate_id = result.fallback_proof.proof_id
    else:
        if (
            result.terminal
            is not AnytimeVariableGraphTerminal.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
            or result.fallback_proof is not None
            or result.counters.fallback_exact_ground_rows != 0
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "positive anytime cell did not stop at its first certificate"
            )
        certificate_id = result.final_audit.audit_id

    regret = max(
        Fraction(0),
        Fraction(3, 64) - verification.exact_normalized_reward,
    )
    full_access_count = (
        result.counters.full_131072_rows_materialized
        + result.counters.v0066_full_evidence_constructor_calls
        + result.counters.v0066_full_profile_reads
    )
    prefix_coupling = (
        verification.paired_seed_replay_passed
        and verification.prefix_generated_refinement_passed
        and verification.no_full_data_leakage_passed
        and verification.replayed_prefix_rows
        == result.final_evidence.ground_row_count
        and verification.replayed_ordinal_draws
        == result.counters.target_ordinal_draws
    )
    return GraphOccurrenceArmResultV1(
        occurrence=occurrence,
        arm=arm,
        confidence=ConfidenceContractV1(
            preregistration.claim_scope_id,
            preregistration.confidence_budget_id,
            result.final_evidence.evidence_id,
            ConfidenceFamily.QUOTIENT_SEQUENTIAL,
            (
                result.final_evidence
                .preregistered_aggregate_obligation_count
            ),
            result.sequential_profile.confidence_alpha,
            result.conditional_family_tail_upper,
            1 - result.conditional_family_tail_upper,
            (
                "CONDITIONAL_ON_REGISTERED_COUNTER_STREAM_"
                "IID_SIMULATOR_ASSUMPTION"
            ),
        ),
        work=OccurrenceSampleWorkV1(
            EvidenceEventVectorV1(
                "ONLINE_TARGET",
                0,
                result.counters.target_ordinal_draws,
                result.counters.structural_support_kernel_calls,
                0,
                0,
            ),
            EvidenceEventVectorV1.zero("OPERATIONAL_QUERY"),
            EvidenceEventVectorV1(
                "OPERATIONAL_QUERY",
                0,
                0,
                result.counters.fallback_exact_ground_rows,
                0,
                0,
            ),
            EvidenceEventVectorV1(
                "STANDALONE_EVALUATION",
                0,
                0,
                verification.actual_verifier_exact_kernel_queries,
                0,
                0,
            ),
        ),
        acquired_ground_rows=result.counters.target_ground_rows,
        terminal_class=TerminalClass.PLAN_CERTIFICATE,
        certificate_id=certificate_id,
        evidence_verification_id=verification.verification_id,
        exact_evaluation_id=verification.verification_id,
        access_verification_id=verification.verification_id,
        paired_seed_stream_id=paired_graph_seed_stream_id_v1(occurrence),
        exact_failure_probability=verification.exact_failure_probability,
        exact_normalized_reward=verification.exact_normalized_reward,
        normalized_regret=regret,
        audit_covers_exact_objective_constraint=(
            verification.exact_lift_or_fallback_check_passed
        ),
        false_certificate_count=0,
        source_prior_gate_id=prior_id,
        source_proposal_id=proposal_id,
        source_prior_selected_this_arm=selected,
        cold_occurrence_local_model=False,
        target_model_reused=False,
        target_operator_instantiation=operator_instantiation,
        raw_draw_replay_passed=verification.paired_seed_replay_passed,
        target_local_certificate=True,
        exact_probabilities_used_by_statistical_model=False,
        direct_prefix_acquisition=(full_access_count == 0),
        operational_full_fixed_evidence_access_count=full_access_count,
        prefix_coupling_verified=prefix_coupling,
        pretrained_source_skeleton_used=True,
    )


def adapt_v0066_fixed_quotient_result_v1(
    preregistration: FactorialSampleEfficiencyPreregistrationV1,
    occurrence: RegisteredGraphOccurrenceV1,
    campaign: Any,
    verification: Any,
    *,
    source_prior: SourcePriorGateEvidenceV1 | None = None,
    target_proposal: Any | None = None,
) -> GraphOccurrenceArmResultV1:
    """Adapt the verified historical fixed arm without rerunning it online."""

    from acfqp.variable_order_graph_rapm_v1 import (
        VariableOrderGraphCampaignV1,
        VariableOrderGraphCampaignVerificationV1,
    )
    from acfqp.v0066_graph_acquisition_metaprior_v1 import (
        GraphAcquisitionOperatorKind,
        GraphTargetAcquisitionProposalV1,
        _operator_candidates,
    )

    if (
        type(preregistration)
        is not FactorialSampleEfficiencyPreregistrationV1
        or occurrence not in preregistration.occurrences
        or occurrence.replica_index != 1
        or type(campaign) is not VariableOrderGraphCampaignV1
        or type(verification)
        is not VariableOrderGraphCampaignVerificationV1
        or verification.campaign_id != campaign.campaign_id
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "fixed V0-066 quotient result failed campaign binding"
        )
    result = next(
        (
            item
            for item in campaign.results
            if item.context.context_id == occurrence.context_id
        ),
        None,
    )
    evaluation = next(
        (
            item
            for item in campaign.evaluations
            if item.context_id == occurrence.context_id
        ),
        None,
    )
    if (
        result is None
        or evaluation is None
        or result.result_id not in verification.verified_result_ids
        or result.verification.verification_id
        not in verification.verified_raw_replay_ids
        or evaluation.evaluation_id
        not in verification.verified_evaluation_ids
        or result.evidence.generative_draw_count
        != result.evidence.ground_row_count * FIXED_SAMPLE_COUNT_PER_ROW
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "fixed V0-066 result lacks verified raw/evaluation authorities"
        )
    meta_cell = source_prior is not None or target_proposal is not None
    if meta_cell:
        sequential_candidate = (
            next(
                candidate
                for semantics, candidate in _operator_candidates(
                    target_proposal.applicability.role_schema_id
                )
                if semantics.operator_kind
                is GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER
            )
            if type(target_proposal) is GraphTargetAcquisitionProposalV1
            else None
        )
        if (
            type(source_prior) is not SourcePriorGateEvidenceV1
            or source_prior.gate_prior_id
            != preregistration.source_prior_gate_id
            or type(target_proposal)
            is not GraphTargetAcquisitionProposalV1
            or target_proposal.context_id != occurrence.context_id
            or target_proposal.query_id != occurrence.query_id
            or target_proposal.proposal.prior_id != source_prior.prior_id
            or target_proposal.proposal.selected_candidate_ids
            != (target_proposal.expected_selected_candidate_id,)
            or target_proposal.expected_selected_candidate_id
            != sequential_candidate.candidate_id
            or target_proposal.target_dynamics_rows != 0
            or target_proposal.target_outcome_labels != 0
            or target_proposal.target_reward_labels != 0
            or target_proposal.target_certificate_labels != 0
        ):
            raise FactorialSampleEfficiencyInvariantViolation(
                "fixed meta-prior ablation is not proposal/context bound"
            )
        arm = META_PRIOR_FIXED
        prior_id = source_prior.gate_prior_id
        proposal_id = target_proposal.target_proposal_id
    else:
        arm = NO_PRIOR_FIXED
        prior_id = None
        proposal_id = None
    fallback_rows = (
        0
        if result.fallback_proof is None
        else result.fallback_proof.evaluated_state_action_rows
    )
    is_negative = (
        occurrence.context_key == "variable_negative_k6_minus_edge_v0"
    )
    if (
        is_negative
        and (
            result.fallback_proof is None
            or result.fallback_proof.complete_matched_query_search is not True
            or fallback_rows != 60
        )
    ) or (not is_negative and result.fallback_proof is not None):
        raise FactorialSampleEfficiencyInvariantViolation(
            "fixed V0-066 terminal does not match its registered fallback role"
        )
    if result.fallback_proof is None:
        certificate_id = result.final_audit.audit_id
        exact_failure = evaluation.lifted_exact_failure_probability
        exact_reward = evaluation.lifted_exact_normalized_reward
    else:
        certificate_id = result.fallback_proof.proof_id
        exact_failure = result.fallback_proof.exact_failure_probability
        exact_reward = result.fallback_proof.exact_normalized_reward
    regret = max(
        Fraction(0),
        evaluation.matched_direct_control.selected_exact_reward
        - exact_reward,
    )
    return GraphOccurrenceArmResultV1(
        occurrence=occurrence,
        arm=arm,
        confidence=ConfidenceContractV1(
            preregistration.claim_scope_id,
            preregistration.confidence_budget_id,
            campaign.calibration.calibration_id,
            ConfidenceFamily.QUOTIENT_FIXED,
            campaign.calibration.family_aggregate_obligations,
            campaign.calibration.per_obligation_tail_upper,
            campaign.calibration.family_tail_upper,
            campaign.calibration.family_confidence_lower,
            (
                "CONDITIONAL_ON_REGISTERED_COUNTER_STREAM_"
                "IID_SIMULATOR_ASSUMPTION"
            ),
        ),
        work=OccurrenceSampleWorkV1(
            EvidenceEventVectorV1(
                "ONLINE_TARGET",
                0,
                result.evidence.generative_draw_count,
                result.evidence.ground_row_count,
                0,
                0,
            ),
            EvidenceEventVectorV1.zero("OPERATIONAL_QUERY"),
            EvidenceEventVectorV1(
                "OPERATIONAL_QUERY",
                0,
                0,
                fallback_rows,
                0,
                0,
            ),
            EvidenceEventVectorV1(
                "STANDALONE_EVALUATION",
                0,
                0,
                (
                    result.verification.replayed_ground_rows
                    + evaluation.matched_direct_control.matched_h2_row_count
                ),
                0,
                0,
            ),
        ),
        acquired_ground_rows=result.evidence.ground_row_count,
        terminal_class=TerminalClass.PLAN_CERTIFICATE,
        certificate_id=certificate_id,
        evidence_verification_id=result.verification.verification_id,
        exact_evaluation_id=evaluation.evaluation_id,
        access_verification_id=verification.verification_id,
        paired_seed_stream_id=paired_graph_seed_stream_id_v1(occurrence),
        exact_failure_probability=exact_failure,
        exact_normalized_reward=exact_reward,
        normalized_regret=regret,
        audit_covers_exact_objective_constraint=(
            evaluation.audit_bounds_cover_exact_lift
            and evaluation.exact_regret_check_passed
            and (
                not is_negative
                or result.fallback_proof.complete_matched_query_search
            )
        ),
        false_certificate_count=0,
        source_prior_gate_id=prior_id,
        source_proposal_id=proposal_id,
        source_prior_selected_this_arm=False,
        cold_occurrence_local_model=False,
        target_model_reused=False,
        raw_draw_replay_passed=result.verification.raw_replay_passed,
        target_local_certificate=True,
        exact_probabilities_used_by_statistical_model=False,
        direct_prefix_acquisition=(
            result.evidence.source_dynamics_rows_used == 0
            and result.evidence.complete_target_closure_rows_used == 0
        ),
        operational_full_fixed_evidence_access_count=(
            result.evidence.complete_target_closure_rows_used
        ),
        prefix_coupling_verified=(
            result.verification.raw_replay_passed
            and result.verification.sparse_chronology_passed
            and verification.typed_identity_chain_passed
            and verification.sparse_access_boundary_passed
        ),
        pretrained_source_skeleton_used=True,
    )


def _summary(
    arm: FactorialArmV1,
    results: tuple[GraphOccurrenceArmResultV1, ...],
) -> FactorialArmSummaryV1:
    selected = tuple(item for item in results if item.arm == arm)
    positive = tuple(
        item
        for item in selected
        if item.occurrence.context_key
        != "variable_negative_k6_minus_edge_v0"
    )
    negative = tuple(
        item
        for item in selected
        if item.occurrence.context_key
        == "variable_negative_k6_minus_edge_v0"
    )
    return FactorialArmSummaryV1(
        arm,
        len(selected),
        sum(item.work.acquisition_draws for item in selected),
        sum(item.work.operational_target_draws for item in selected),
        sum(item.work.certified_target_draws for item in selected),
        sum(item.work.certified_target_draws for item in positive),
        sum(item.work.certified_target_draws for item in negative),
        sum(item.work.operational_exact_kernel_queries for item in selected),
        sum(
            item.work.operational_exact_kernel_queries for item in negative
        ),
        sum(
            item.terminal_class is TerminalClass.PLAN_CERTIFICATE
            for item in selected
        ),
        sum(
            item.terminal_class
            is TerminalClass.INFEASIBILITY_CERTIFICATE
            for item in selected
        ),
        sum(item.false_certificate_count for item in selected),
        tuple(
            (
                context.context_key,
                sum(
                    item.work.certified_target_draws
                    for item in selected
                    if item.occurrence.context_id == context.context_id
                ),
            )
            for context in REGISTERED_GRAPH_CONTEXTS
        ),
    )


def _strictly_better_with_context_no_harm(
    left: FactorialArmSummaryV1,
    right: FactorialArmSummaryV1,
) -> bool:
    # Only W5/K6 are the matched generative-draw endpoint.  The negative
    # control is reported in the native family vector and never offsets it.
    return (
        left.positive_certified_target_draws
        < right.positive_certified_target_draws
        and all(
            left_value <= right_value
            for (left_key, left_value), (right_key, right_value) in zip(
                left.per_context_certified_draws[:2],
                right.per_context_certified_draws[:2],
            )
            if left_key == right_key
        )
    )


def _positive_context_no_harm(
    left: FactorialArmSummaryV1,
    right: FactorialArmSummaryV1,
) -> bool:
    return (
        left.positive_certified_target_draws
        <= right.positive_certified_target_draws
        and all(
            left_value <= right_value
            for (_, left_value), (_, right_value) in zip(
                left.per_context_certified_draws[:2],
                right.per_context_certified_draws[:2],
            )
        )
    )


def _offline_break_even(
    preregistration: FactorialSampleEfficiencyPreregistrationV1,
    results: tuple[GraphOccurrenceArmResultV1, ...],
    offline_draws: int,
) -> int | None:
    by_key = {
        (item.occurrence.occurrence_id, item.arm.arm_id): item
        for item in results
    }
    meta_total = offline_draws
    no_prior_sequential_total = 0
    positive_occurrence_index = 0
    for occurrence in preregistration.occurrences:
        if (
            occurrence.context_key
            == "variable_negative_k6_minus_edge_v0"
        ):
            continue
        positive_occurrence_index += 1
        meta_total += by_key[
            (occurrence.occurrence_id, META_PRIOR_SEQUENTIAL.arm_id)
        ].work.certified_target_draws
        no_prior_sequential_total += by_key[
            (occurrence.occurrence_id, NO_PRIOR_SEQUENTIAL.arm_id)
        ].work.certified_target_draws
        if meta_total < no_prior_sequential_total:
            return positive_occurrence_index
    return None


def evaluate_factorial_sample_efficiency_gate_v1(
    preregistration: FactorialSampleEfficiencyPreregistrationV1,
    source_prior: SourcePriorGateEvidenceV1,
    results: Iterable[GraphOccurrenceArmResultV1],
) -> FactorialSampleEfficiencyGateResultV1:
    """Evaluate the exact paired finite-workload Gate.

    The function deliberately refuses missing cells, weaker confidence,
    target/source identity overlap, positive-context operational exact access,
    mismatched negative fallback authority, or improvements obtained only by
    dropping the K6-minus-edge occurrence.
    """

    if (
        type(preregistration)
        is not FactorialSampleEfficiencyPreregistrationV1
        or type(source_prior) is not SourcePriorGateEvidenceV1
        or source_prior.gate_prior_id
        != preregistration.source_prior_gate_id
        or tuple(source_prior.target_context_ids)
        != tuple(sorted(item.context_id for item in REGISTERED_GRAPH_CONTEXTS))
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "Gate preregistration and frozen source prior do not match"
        )
    result_tuple = tuple(results)
    if (
        not result_tuple
        or any(
            type(item) is not GraphOccurrenceArmResultV1
            for item in result_tuple
        )
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "Gate results must be typed occurrence arm results"
        )
    expected_keys = {
        (occurrence.occurrence_id, arm.arm_id)
        for occurrence in preregistration.occurrences
        for arm in (
            REGISTERED_ARMS[:4]
            if occurrence.context_key
            == "variable_negative_k6_minus_edge_v0"
            else REGISTERED_ARMS
        )
    }
    observed_keys = {
        (item.occurrence.occurrence_id, item.arm.arm_id)
        for item in result_tuple
    }
    if (
        observed_keys != expected_keys
        or len(result_tuple) != len(expected_keys)
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "Gate requires four quotient cells on all contexts and two "
            "direct cells on both positive contexts exactly once"
        )
    if any(
        item.arm.proposal is ProposalMode.SOURCE_META_PRIOR
        and item.source_prior_gate_id != source_prior.gate_prior_id
        for item in result_tuple
    ):
        raise FactorialSampleEfficiencyInvariantViolation(
            "meta-prior arm referenced a different frozen source prior"
        )
    confidence_reconciliation = _reconcile_confidence_v1(result_tuple)
    equal_confidence = all(
        item.confidence.claim_scope_id == preregistration.claim_scope_id
        and item.confidence.confidence_budget_id
        == preregistration.confidence_budget_id
        for item in result_tuple
    ) and (
        confidence_reconciliation.joint_tail_upper
        == Fraction(97, 25_000)
    )
    paired_prefix_access = all(
        len(
            {
                item.paired_seed_stream_id
                for item in result_tuple
                if item.occurrence.occurrence_id
                == occurrence.occurrence_id
            }
        )
        == 1
        and all(
            item.direct_prefix_acquisition
            and item.operational_full_fixed_evidence_access_count == 0
            and item.prefix_coupling_verified
            for item in result_tuple
            if item.occurrence.occurrence_id
            == occurrence.occurrence_id
        )
        for occurrence in preregistration.occurrences
    )
    all_closed = all(
        item.terminal_class
        in (
            TerminalClass.PLAN_CERTIFICATE,
            TerminalClass.INFEASIBILITY_CERTIFICATE,
        )
        and item.false_certificate_count == 0
        for item in result_tuple
    )
    negative_exact_counts = {
        item.work.fallback.exact_kernel_queries
        for item in result_tuple
        if item.occurrence.context_key
        == "variable_negative_k6_minus_edge_v0"
    }
    oracle_matched = (
        paired_prefix_access
        and all(item.matched_oracle_authority for item in result_tuple)
        and negative_exact_counts == {60}
    )
    historical_exact_fallback = any(
        item.arm == NO_PRIOR_FIXED
        and item.occurrence.context_key
        == "variable_negative_k6_minus_edge_v0"
        and item.work.fallback.exact_kernel_queries > 0
        for item in result_tuple
    )

    by_occurrence: dict[
        str, tuple[GraphOccurrenceArmResultV1, ...]
    ] = {}
    for occurrence in preregistration.occurrences:
        by_occurrence[occurrence.occurrence_id] = tuple(
            item
            for item in result_tuple
            if item.occurrence.occurrence_id == occurrence.occurrence_id
        )
    exact_preservation = all(
        all(
            item.exact_normalized_reward == Fraction(3, 64)
            and item.normalized_regret <= Fraction(1, 20)
            and item.audit_covers_exact_objective_constraint
            and item.exact_failure_probability
            < next(
                context.risk_tolerance
                for context in REGISTERED_GRAPH_CONTEXTS
                if context.context_id == item.occurrence.context_id
            )
            for item in members
        )
        for members in by_occurrence.values()
    )

    summaries = tuple(
        _summary(arm, result_tuple) for arm in REGISTERED_ARMS
    )
    summary_by_arm = {item.arm.arm_id: item for item in summaries}
    no_fixed = summary_by_arm[NO_PRIOR_FIXED.arm_id]
    no_seq = summary_by_arm[NO_PRIOR_SEQUENTIAL.arm_id]
    meta_fixed = summary_by_arm[META_PRIOR_FIXED.arm_id]
    meta_seq = summary_by_arm[META_PRIOR_SEQUENTIAL.arm_id]
    direct_fixed = summary_by_arm[DIRECT_FIXED.arm_id]
    direct_seq = summary_by_arm[DIRECT_SEQUENTIAL.arm_id]

    expected_replicas = preregistration.replica_count
    fixed_v0066 = (
        no_fixed.acquisition_draws
        == 18_612_224 * expected_replicas
    )
    fixed_direct = (
        direct_fixed.acquisition_draws
        == 11_796_480 * expected_replicas
    )
    sequential_effect = (
        _strictly_better_with_context_no_harm(no_seq, no_fixed)
        and _strictly_better_with_context_no_harm(
            meta_seq,
            meta_fixed,
        )
        and _strictly_better_with_context_no_harm(
            direct_seq,
            direct_fixed,
        )
    )
    meta_effect = (
        _strictly_better_with_context_no_harm(meta_fixed, no_fixed)
        and _strictly_better_with_context_no_harm(meta_seq, no_seq)
    )
    meta_selection_valid = (
        all(
            item.source_prior_selected_this_arm
            for item in result_tuple
            if item.arm == META_PRIOR_SEQUENTIAL
        )
        and _positive_context_no_harm(meta_seq, no_seq)
    )
    combined_online = (
        _strictly_better_with_context_no_harm(meta_seq, no_fixed)
        and _strictly_better_with_context_no_harm(meta_seq, direct_seq)
    )
    per_context_no_harm = all(
        meta_value <= no_value and meta_value <= direct_value
        for (_, meta_value), (_, no_value), (_, direct_value) in zip(
            meta_seq.per_context_certified_draws[:2],
            no_seq.per_context_certified_draws[:2],
            direct_seq.per_context_certified_draws[:2],
        )
    )
    online_passed = all(
        (
            all_closed,
            equal_confidence,
            oracle_matched,
            exact_preservation,
            fixed_v0066,
            fixed_direct,
            sequential_effect,
            meta_selection_valid,
            combined_online,
            per_context_no_harm,
        )
    )
    break_even = (
        _offline_break_even(
            preregistration,
            result_tuple,
            source_prior.offline_source_draws,
        )
        if online_passed
        else None
    )
    offline_passed = break_even is not None
    return FactorialSampleEfficiencyGateResultV1(
        preregistration.preregistration_id,
        source_prior.gate_prior_id,
        tuple(sorted(item.result_id for item in result_tuple)),
        summaries,
        all_closed,
        equal_confidence,
        confidence_reconciliation,
        paired_prefix_access,
        oracle_matched,
        exact_preservation,
        False,
        fixed_v0066,
        fixed_direct,
        sequential_effect,
        meta_selection_valid,
        meta_effect,
        False,
        combined_online,
        per_context_no_harm,
        online_passed,
        source_prior.offline_source_draws,
        break_even,
        offline_passed,
        "ESTABLISHED" if offline_passed else "NOT_ESTABLISHED",
        online_passed,
        historical_exact_fallback,
        REGISTERED_CLAIM_SCOPE,
    )


__all__ = [
    "CONTRACT_VERSION",
    "ConfidenceContractV1",
    "ConfidenceFamily",
    "ConfidenceReconciliationV1",
    "DIRECT_FIXED",
    "DIRECT_SEQUENTIAL",
    "EvidenceEventVectorV1",
    "FactorialArmSummaryV1",
    "FactorialArmV1",
    "FactorialSampleEfficiencyGateResultV1",
    "FactorialSampleEfficiencyInvariantViolation",
    "FactorialSampleEfficiencyPreregistrationV1",
    "FIXED_SAMPLE_COUNT_PER_ROW",
    "GraphOccurrenceArmResultV1",
    "META_PRIOR_FIXED",
    "META_PRIOR_SEQUENTIAL",
    "NO_PRIOR_FIXED",
    "NO_PRIOR_SEQUENTIAL",
    "OccurrenceSampleWorkV1",
    "PlannerKind",
    "PROFILE_KEY",
    "ProposalMode",
    "REGISTERED_ARMS",
    "REGISTERED_CLAIM_SCOPE",
    "REGISTERED_CONFIDENCE_LOWER",
    "REGISTERED_FAMILY_TAIL_UPPER",
    "REGISTERED_GRAPH_CONTEXTS",
    "RegisteredGraphContextV1",
    "RegisteredGraphOccurrenceV1",
    "SCHEMA_VERSION",
    "SourcePriorGateEvidenceV1",
    "StoppingMode",
    "TargetSequentialOperatorInstantiationV1",
    "TerminalClass",
    "build_registered_graph_occurrences_v1",
    "build_source_prior_gate_evidence_v1",
    "build_v0066_source_prior_gate_evidence_v1",
    "adapt_anytime_quotient_result_v1",
    "adapt_direct_fixed_result_v1",
    "adapt_direct_sequential_result_v1",
    "adapt_v0066_fixed_quotient_result_v1",
    "evaluate_factorial_sample_efficiency_gate_v1",
    "paired_graph_seed_stream_id_v1",
]
