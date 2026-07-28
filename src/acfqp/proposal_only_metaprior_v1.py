"""Identity-bound, proposal-only source meta-prior for V0-067.

This module implements one deliberately narrow intervention against the
sample tax observed in V0-066.  Query-neutral source observations may rank
registered predicate, support, and refinement candidates.  A target request
may consume that frozen ordering only when its registered family, adapter,
role schema, candidate registry, query, model epoch, and proof frontier are
identity-bound.

The meta-prior is never an acceptance or certification authority.  It cannot
narrow a statistical envelope, declare a plan feasible, or replace
target-local acquisition, audit, and fallback.  Out-of-distribution targets,
identity mismatches, and missing structural capabilities produce an empty
fail-closed proposal.

Source and target accounting are kept in distinct native lanes.  No combined
``total observations`` or scalar economics field is defined here.
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
PROFILE_KEY = "v0067_proposal_only_source_consensus_metaprior_v0"
RANKING_SEMANTICS = (
    "within_source_midrank_then_mean_worst_span_complexity_v1"
)

DOMAIN_TAGS = {
    "candidate": "acfqp:proposal-only-metaprior-candidate:v1",
    "registry": "acfqp:proposal-only-metaprior-registry:v1",
    "envelope": "acfqp:proposal-only-metaprior-transfer-envelope:v1",
    "source_observation": (
        "acfqp:proposal-only-metaprior-source-observation:v1"
    ),
    "source_log": "acfqp:proposal-only-metaprior-source-log:v1",
    "offline_accounting": (
        "acfqp:proposal-only-metaprior-offline-accounting:v1"
    ),
    "consensus_score": (
        "acfqp:proposal-only-metaprior-consensus-score:v1"
    ),
    "prior": "acfqp:proposal-only-metaprior-source-prior:v1",
    "target_evidence": (
        "acfqp:proposal-only-metaprior-target-applicability:v1"
    ),
    "online_accounting": (
        "acfqp:proposal-only-metaprior-online-accounting:v1"
    ),
    "request": "acfqp:proposal-only-metaprior-request:v1",
    "proposal": "acfqp:proposal-only-metaprior-ranking:v1",
    "verification": (
        "acfqp:proposal-only-metaprior-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("proposal-only meta-prior content domains must be unique")


class ProposalOnlyMetaPriorInvariantViolation(ValueError):
    """A schema, identity, accounting, or authority invariant failed."""


class ProposalCandidateKind(str, Enum):
    PREDICATE = "PREDICATE"
    SUPPORT = "SUPPORT"
    REFINEMENT = "REFINEMENT"


class ProposalStatus(str, Enum):
    PROPOSAL_READY = "PROPOSAL_READY"
    IDENTITY_MISMATCH_REFUSED = "IDENTITY_MISMATCH_REFUSED"
    OOD_TARGET_REFUSED = "OOD_TARGET_REFUSED"
    MISSING_CAPABILITY_REFUSED = "MISSING_CAPABILITY_REFUSED"
    NO_REGISTERED_CANDIDATE_REFUSED = "NO_REGISTERED_CANDIDATE_REFUSED"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ProposalOnlyMetaPriorInvariantViolation(str(error)) from error
    return hashlib.sha256(
        tag.encode("utf-8") + b"\x00" + encoded
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ProposalOnlyMetaPriorInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _text(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise ProposalOnlyMetaPriorInvariantViolation(
            f"{field} must be nonempty text"
        )
    return value


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ProposalOnlyMetaPriorInvariantViolation(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def _canonical_ids(
    values: tuple[str, ...],
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or (not allow_empty and not values)
        or values != tuple(sorted(set(values)))
    ):
        raise ProposalOnlyMetaPriorInvariantViolation(
            f"{field} must be a canonical ID set"
        )
    for value in values:
        _cid(value, field)
    return values


def _canonical_kinds(
    values: tuple[ProposalCandidateKind, ...],
) -> tuple[ProposalCandidateKind, ...]:
    if (
        type(values) is not tuple
        or not values
        or any(type(value) is not ProposalCandidateKind for value in values)
        or tuple(sorted(set(values), key=lambda item: item.value)) != values
    ):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "allowed candidate kinds must be canonical"
        )
    return values


@dataclass(frozen=True, slots=True)
class ProposalCandidateV1:
    candidate_key: str
    kind: ProposalCandidateKind
    semantics_id: str
    required_capability_ids: tuple[str, ...]
    complexity: int

    def __post_init__(self) -> None:
        _text(self.candidate_key, "candidate key")
        if type(self.kind) is not ProposalCandidateKind:
            raise ProposalOnlyMetaPriorInvariantViolation(
                "candidate kind must use the registered enum"
            )
        _cid(self.semantics_id, "candidate semantics")
        _canonical_ids(
            self.required_capability_ids,
            "candidate capabilities",
        )
        _integer(self.complexity, "candidate complexity", 1)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proposal_only_metaprior_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_key": self.candidate_key,
            "kind": self.kind.value,
            "semantics_id": self.semantics_id,
            "required_capability_ids": list(
                self.required_capability_ids
            ),
            "complexity": self.complexity,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class ProposalCandidateRegistryV1:
    role_schema_id: str
    candidates: tuple[ProposalCandidateV1, ...]

    def __post_init__(self) -> None:
        _cid(self.role_schema_id, "candidate registry role schema")
        if (
            type(self.candidates) is not tuple
            or not self.candidates
            or any(
                type(candidate) is not ProposalCandidateV1
                for candidate in self.candidates
            )
            or tuple(
                sorted(self.candidates, key=lambda item: item.candidate_id)
            )
            != self.candidates
            or len({item.candidate_id for item in self.candidates})
            != len(self.candidates)
            or len({item.candidate_key for item in self.candidates})
            != len(self.candidates)
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "candidate registry must be a canonical exact candidate set"
            )

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(item.candidate_id for item in self.candidates)

    def candidate_by_id(self, candidate_id: str) -> ProposalCandidateV1:
        _cid(candidate_id, "candidate lookup")
        for candidate in self.candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ProposalOnlyMetaPriorInvariantViolation(
            "candidate is absent from the bound registry"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proposal_only_metaprior_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "role_schema_id": self.role_schema_id,
            "candidate_ids": list(self.candidate_ids),
        }

    @property
    def registry_id(self) -> str:
        return _content_id("registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidates": [
                candidate.to_document() for candidate in self.candidates
            ],
            "registry_id": self.registry_id,
        }


def build_proposal_candidate_registry_v1(
    role_schema_id: str,
    candidates: Iterable[ProposalCandidateV1],
) -> ProposalCandidateRegistryV1:
    rows = tuple(candidates)
    if any(type(item) is not ProposalCandidateV1 for item in rows):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "candidate builder rejects runtime substitutions"
        )
    return ProposalCandidateRegistryV1(
        role_schema_id,
        tuple(sorted(rows, key=lambda item: item.candidate_id)),
    )


@dataclass(frozen=True, slots=True)
class ProposalTransferEnvelopeV1:
    candidate_registry_id: str
    role_schema_id: str
    source_family_ids: tuple[str, ...]
    allowed_target_family_ids: tuple[str, ...]
    allowed_target_adapter_ids: tuple[str, ...]
    maximum_proposals: int = 8
    family_membership_is_only_ood_authority: bool = True
    observational_ood_generalization_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.candidate_registry_id, "transfer candidate registry")
        _cid(self.role_schema_id, "transfer role schema")
        _canonical_ids(self.source_family_ids, "source families")
        _canonical_ids(
            self.allowed_target_family_ids,
            "allowed target families",
        )
        _canonical_ids(
            self.allowed_target_adapter_ids,
            "allowed target adapters",
        )
        if (
            self.maximum_proposals != 8
            or self.family_membership_is_only_ood_authority is not True
            or self.observational_ood_generalization_claimed is not False
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "transfer envelope or OOD claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.proposal_only_metaprior_transfer_envelope.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "candidate_registry_id": self.candidate_registry_id,
            "role_schema_id": self.role_schema_id,
            "source_family_ids": list(self.source_family_ids),
            "allowed_target_family_ids": list(
                self.allowed_target_family_ids
            ),
            "allowed_target_adapter_ids": list(
                self.allowed_target_adapter_ids
            ),
            "maximum_proposals": self.maximum_proposals,
            "family_membership_is_only_ood_authority": (
                self.family_membership_is_only_ood_authority
            ),
            "observational_ood_generalization_claimed": (
                self.observational_ood_generalization_claimed
            ),
        }

    @property
    def envelope_id(self) -> str:
        return _content_id("envelope", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "envelope_id": self.envelope_id}


@dataclass(frozen=True, slots=True)
class SourceProposalObservationV1:
    source_context_id: str
    source_family_id: str
    candidate_id: str
    proposal_score: Fraction
    logged_observation_count: int
    generative_draw_count: int
    environment_interaction_count: int
    exact_kernel_call_count: int
    source_scoring_proxy_id: str | None = None
    source_scoring_proxy_rule: str | None = None
    source_scoring_proxy_may_certify: bool = False
    source_oracle_aided: bool = False
    target_channels_used: bool = False
    certificate_outcomes_used: bool = False
    observation_semantics: str = (
        "query_neutral_source_observed_proposal_utility_v1"
    )

    def __post_init__(self) -> None:
        _cid(self.source_context_id, "source context")
        _cid(self.source_family_id, "source family")
        _cid(self.candidate_id, "source candidate")
        if type(self.proposal_score) is not Fraction:
            raise ProposalOnlyMetaPriorInvariantViolation(
                "proposal score must be an exact Fraction"
            )
        _integer(
            self.logged_observation_count,
            "source logged observations",
            1,
        )
        _integer(self.generative_draw_count, "source generative draws")
        _integer(
            self.environment_interaction_count,
            "source environment interactions",
        )
        _integer(
            self.exact_kernel_call_count,
            "source exact kernel calls",
        )
        if self.source_scoring_proxy_id is None:
            if self.source_scoring_proxy_rule is not None:
                raise ProposalOnlyMetaPriorInvariantViolation(
                    "source scoring proxy rule lacks a proxy identity"
                )
        else:
            _cid(self.source_scoring_proxy_id, "source scoring proxy")
            _text(self.source_scoring_proxy_rule, "source scoring proxy rule")
        if (
            self.source_scoring_proxy_may_certify is not False
            or self.source_oracle_aided is not False
            or self.target_channels_used is not False
            or self.certificate_outcomes_used is not False
            or self.observation_semantics
            != "query_neutral_source_observed_proposal_utility_v1"
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "source observation leaked an oracle, target, or certificate channel"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.proposal_only_metaprior_source_observation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "source_family_id": self.source_family_id,
            "candidate_id": self.candidate_id,
            "proposal_score": _fdoc(self.proposal_score),
            "logged_observation_count": self.logged_observation_count,
            "generative_draw_count": self.generative_draw_count,
            "environment_interaction_count": (
                self.environment_interaction_count
            ),
            "exact_kernel_call_count": self.exact_kernel_call_count,
            "source_scoring_proxy_id": self.source_scoring_proxy_id,
            "source_scoring_proxy_rule": self.source_scoring_proxy_rule,
            "source_scoring_proxy_may_certify": False,
            "source_oracle_aided": self.source_oracle_aided,
            "target_channels_used": self.target_channels_used,
            "certificate_outcomes_used": self.certificate_outcomes_used,
            "observation_semantics": self.observation_semantics,
        }

    @property
    def observation_id(self) -> str:
        return _content_id("source_observation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observation_id": self.observation_id}


@dataclass(frozen=True, slots=True)
class OfflineSourceObservationAccountingV1:
    source_context_count: int
    candidate_observation_count: int
    logged_observation_count: int
    generative_draw_count: int
    environment_interaction_count: int
    exact_kernel_call_count: int
    lane: str = "OFFLINE_SOURCE"

    def __post_init__(self) -> None:
        _integer(self.source_context_count, "source context count", 1)
        _integer(
            self.candidate_observation_count,
            "source candidate observations",
            1,
        )
        _integer(
            self.logged_observation_count,
            "source logged observations",
            1,
        )
        _integer(self.generative_draw_count, "source generative draws")
        _integer(
            self.environment_interaction_count,
            "source environment interactions",
        )
        _integer(
            self.exact_kernel_call_count,
            "source exact kernel calls",
        )
        if self.lane != "OFFLINE_SOURCE":
            raise ProposalOnlyMetaPriorInvariantViolation(
                "offline source accounting changed lane"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.proposal_only_metaprior_offline_accounting.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "lane": self.lane,
            "source_context_count": self.source_context_count,
            "candidate_observation_count": (
                self.candidate_observation_count
            ),
            "logged_observation_count": self.logged_observation_count,
            "generative_draw_count": self.generative_draw_count,
            "environment_interaction_count": (
                self.environment_interaction_count
            ),
            "exact_kernel_call_count": self.exact_kernel_call_count,
        }

    @property
    def accounting_id(self) -> str:
        return _content_id("offline_accounting", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_id": self.accounting_id}


@dataclass(frozen=True, slots=True)
class SourceProposalObservationLogV1:
    candidate_registry_id: str
    transfer_envelope_id: str
    observations: tuple[SourceProposalObservationV1, ...]
    offline_accounting: OfflineSourceObservationAccountingV1

    def __post_init__(self) -> None:
        _cid(self.candidate_registry_id, "source log registry")
        _cid(self.transfer_envelope_id, "source log envelope")
        if (
            type(self.observations) is not tuple
            or not self.observations
            or any(
                type(item) is not SourceProposalObservationV1
                for item in self.observations
            )
            or tuple(
                sorted(
                    self.observations,
                    key=lambda item: (
                        item.source_context_id,
                        item.candidate_id,
                    ),
                )
            )
            != self.observations
            or len(
                {
                    (item.source_context_id, item.candidate_id)
                    for item in self.observations
                }
            )
            != len(self.observations)
            or type(self.offline_accounting)
            is not OfflineSourceObservationAccountingV1
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "source log must contain canonical unique exact observations"
            )
        contexts = {item.source_context_id for item in self.observations}
        families_by_context: dict[str, set[str]] = {}
        for item in self.observations:
            families_by_context.setdefault(
                item.source_context_id, set()
            ).add(item.source_family_id)
        expected = OfflineSourceObservationAccountingV1(
            source_context_count=len(contexts),
            candidate_observation_count=len(self.observations),
            logged_observation_count=sum(
                item.logged_observation_count for item in self.observations
            ),
            generative_draw_count=sum(
                item.generative_draw_count for item in self.observations
            ),
            environment_interaction_count=sum(
                item.environment_interaction_count
                for item in self.observations
            ),
            exact_kernel_call_count=sum(
                item.exact_kernel_call_count for item in self.observations
            ),
        )
        if (
            len(contexts) < 2
            or any(len(families) != 1 for families in families_by_context.values())
            or self.offline_accounting != expected
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "source contexts or offline accounting are inconsistent"
            )

    @property
    def source_context_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted({item.source_context_id for item in self.observations})
        )

    @property
    def source_family_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted({item.source_family_id for item in self.observations})
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proposal_only_metaprior_source_log.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_registry_id": self.candidate_registry_id,
            "transfer_envelope_id": self.transfer_envelope_id,
            "observation_ids": [
                item.observation_id for item in self.observations
            ],
            "source_context_ids": list(self.source_context_ids),
            "source_family_ids": list(self.source_family_ids),
            "offline_accounting_id": (
                self.offline_accounting.accounting_id
            ),
        }

    @property
    def source_log_id(self) -> str:
        return _content_id("source_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "observations": [
                item.to_document() for item in self.observations
            ],
            "offline_accounting": self.offline_accounting.to_document(),
            "source_log_id": self.source_log_id,
        }


def build_source_proposal_observation_log_v1(
    registry: ProposalCandidateRegistryV1,
    envelope: ProposalTransferEnvelopeV1,
    observations: Iterable[SourceProposalObservationV1],
) -> SourceProposalObservationLogV1:
    if (
        type(registry) is not ProposalCandidateRegistryV1
        or type(envelope) is not ProposalTransferEnvelopeV1
    ):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "source-log builder rejects runtime substitutions"
        )
    if (
        envelope.candidate_registry_id != registry.registry_id
        or envelope.role_schema_id != registry.role_schema_id
    ):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "source-log registry/envelope identity mismatch"
        )
    rows = tuple(observations)
    if any(type(item) is not SourceProposalObservationV1 for item in rows):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "source-log observations changed runtime type"
        )
    rows = tuple(
        sorted(
            rows,
            key=lambda item: (item.source_context_id, item.candidate_id),
        )
    )
    contexts = tuple(sorted({item.source_context_id for item in rows}))
    if len(contexts) < 2:
        raise ProposalOnlyMetaPriorInvariantViolation(
            "source consensus requires at least two source contexts"
        )
    candidate_ids = set(registry.candidate_ids)
    for context_id in contexts:
        context_rows = tuple(
            item for item in rows if item.source_context_id == context_id
        )
        if {item.candidate_id for item in context_rows} != candidate_ids:
            raise ProposalOnlyMetaPriorInvariantViolation(
                "every source context must observe the full candidate registry"
            )
    source_families = {item.source_family_id for item in rows}
    if source_families != set(envelope.source_family_ids):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "source log does not exactly cover registered source families"
        )
    accounting = OfflineSourceObservationAccountingV1(
        source_context_count=len(contexts),
        candidate_observation_count=len(rows),
        logged_observation_count=sum(
            item.logged_observation_count for item in rows
        ),
        generative_draw_count=sum(
            item.generative_draw_count for item in rows
        ),
        environment_interaction_count=sum(
            item.environment_interaction_count for item in rows
        ),
        exact_kernel_call_count=sum(
            item.exact_kernel_call_count for item in rows
        ),
    )
    return SourceProposalObservationLogV1(
        registry.registry_id,
        envelope.envelope_id,
        rows,
        accounting,
    )


@dataclass(frozen=True, slots=True)
class SourceConsensusScoreV1:
    candidate_id: str
    mean_rank: Fraction
    worst_rank: Fraction
    rank_span: Fraction
    source_context_count: int
    complexity: int

    def __post_init__(self) -> None:
        _cid(self.candidate_id, "consensus candidate")
        if (
            type(self.mean_rank) is not Fraction
            or type(self.worst_rank) is not Fraction
            or type(self.rank_span) is not Fraction
            or self.mean_rank < 1
            or self.worst_rank < self.mean_rank
            or self.rank_span < 0
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "consensus ranks must be exact nonnegative Fractions"
            )
        _integer(
            self.source_context_count,
            "consensus source contexts",
            2,
        )
        _integer(self.complexity, "consensus complexity", 1)

    @property
    def ordering_key(self) -> tuple[Fraction, Fraction, Fraction, int, str]:
        return (
            self.mean_rank,
            self.worst_rank,
            self.rank_span,
            self.complexity,
            self.candidate_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.proposal_only_metaprior_consensus_score.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "mean_rank": _fdoc(self.mean_rank),
            "worst_rank": _fdoc(self.worst_rank),
            "rank_span": _fdoc(self.rank_span),
            "source_context_count": self.source_context_count,
            "complexity": self.complexity,
            "ranking_semantics": RANKING_SEMANTICS,
        }

    @property
    def score_id(self) -> str:
        return _content_id("consensus_score", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "score_id": self.score_id}


@dataclass(frozen=True, slots=True)
class SourceConsensusMetaPriorV1:
    candidate_registry_id: str
    transfer_envelope_id: str
    source_log_id: str
    scores: tuple[SourceConsensusScoreV1, ...]
    source_context_ids: tuple[str, ...]
    offline_accounting: OfflineSourceObservationAccountingV1
    ranking_semantics: str = RANKING_SEMANTICS
    proposal_only: bool = True
    may_certify: bool = False
    may_narrow_target_envelopes: bool = False
    target_context_ids_seen: tuple[str, ...] = ()
    target_observation_ids_seen: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _cid(self.candidate_registry_id, "prior candidate registry")
        _cid(self.transfer_envelope_id, "prior transfer envelope")
        _cid(self.source_log_id, "prior source log")
        _canonical_ids(self.source_context_ids, "prior source contexts")
        _canonical_ids(
            self.target_context_ids_seen,
            "prior target contexts",
            allow_empty=True,
        )
        _canonical_ids(
            self.target_observation_ids_seen,
            "prior target observations",
            allow_empty=True,
        )
        if (
            type(self.scores) is not tuple
            or not self.scores
            or any(
                type(item) is not SourceConsensusScoreV1
                for item in self.scores
            )
            or tuple(sorted(self.scores, key=lambda item: item.ordering_key))
            != self.scores
            or len({item.candidate_id for item in self.scores})
            != len(self.scores)
            or any(
                item.source_context_count != len(self.source_context_ids)
                for item in self.scores
            )
            or type(self.offline_accounting)
            is not OfflineSourceObservationAccountingV1
            or self.offline_accounting.source_context_count
            != len(self.source_context_ids)
            or self.ranking_semantics != RANKING_SEMANTICS
            or self.proposal_only is not True
            or self.may_certify is not False
            or self.may_narrow_target_envelopes is not False
            or self.target_context_ids_seen != ()
            or self.target_observation_ids_seen != ()
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "source prior ordering, accounting, or authority changed"
            )

    @property
    def ranked_candidate_ids(self) -> tuple[str, ...]:
        return tuple(item.candidate_id for item in self.scores)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proposal_only_metaprior_source_prior.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "candidate_registry_id": self.candidate_registry_id,
            "transfer_envelope_id": self.transfer_envelope_id,
            "source_log_id": self.source_log_id,
            "score_ids": [item.score_id for item in self.scores],
            "ranked_candidate_ids": list(self.ranked_candidate_ids),
            "source_context_ids": list(self.source_context_ids),
            "offline_accounting_id": (
                self.offline_accounting.accounting_id
            ),
            "ranking_semantics": self.ranking_semantics,
            "proposal_only": self.proposal_only,
            "may_certify": self.may_certify,
            "may_narrow_target_envelopes": (
                self.may_narrow_target_envelopes
            ),
            "target_context_ids_seen": list(self.target_context_ids_seen),
            "target_observation_ids_seen": list(
                self.target_observation_ids_seen
            ),
        }

    @property
    def prior_id(self) -> str:
        return _content_id("prior", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "scores": [item.to_document() for item in self.scores],
            "offline_accounting": self.offline_accounting.to_document(),
            "prior_id": self.prior_id,
        }


def _context_midranks(
    observations: tuple[SourceProposalObservationV1, ...],
) -> dict[str, Fraction]:
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (-item.proposal_score, item.candidate_id),
        )
    )
    result: dict[str, Fraction] = {}
    start = 0
    while start < len(ordered):
        end = start + 1
        while (
            end < len(ordered)
            and ordered[end].proposal_score == ordered[start].proposal_score
        ):
            end += 1
        # Positions are one-based.  A tie receives its exact average rank.
        midrank = Fraction((start + 1) + end, 2)
        for item in ordered[start:end]:
            result[item.candidate_id] = midrank
        start = end
    return result


def build_source_consensus_metaprior_v1(
    registry: ProposalCandidateRegistryV1,
    envelope: ProposalTransferEnvelopeV1,
    source_log: SourceProposalObservationLogV1,
) -> SourceConsensusMetaPriorV1:
    if (
        type(registry) is not ProposalCandidateRegistryV1
        or type(envelope) is not ProposalTransferEnvelopeV1
        or type(source_log) is not SourceProposalObservationLogV1
    ):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "source-prior builder rejects runtime substitutions"
        )
    if (
        envelope.candidate_registry_id != registry.registry_id
        or envelope.role_schema_id != registry.role_schema_id
        or source_log.candidate_registry_id != registry.registry_id
        or source_log.transfer_envelope_id != envelope.envelope_id
        or source_log.source_family_ids != envelope.source_family_ids
    ):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "source prior identity chain is inconsistent"
        )
    ranks_by_context: dict[str, dict[str, Fraction]] = {}
    for context_id in source_log.source_context_ids:
        rows = tuple(
            item
            for item in source_log.observations
            if item.source_context_id == context_id
        )
        ranks_by_context[context_id] = _context_midranks(rows)
    scores = []
    for candidate in registry.candidates:
        ranks = tuple(
            ranks_by_context[context_id][candidate.candidate_id]
            for context_id in source_log.source_context_ids
        )
        scores.append(
            SourceConsensusScoreV1(
                candidate_id=candidate.candidate_id,
                mean_rank=sum(ranks, Fraction(0)) / len(ranks),
                worst_rank=max(ranks),
                rank_span=max(ranks) - min(ranks),
                source_context_count=len(ranks),
                complexity=candidate.complexity,
            )
        )
    return SourceConsensusMetaPriorV1(
        candidate_registry_id=registry.registry_id,
        transfer_envelope_id=envelope.envelope_id,
        source_log_id=source_log.source_log_id,
        scores=tuple(sorted(scores, key=lambda item: item.ordering_key)),
        source_context_ids=source_log.source_context_ids,
        offline_accounting=source_log.offline_accounting,
    )


@dataclass(frozen=True, slots=True)
class OnlineTargetContextAccountingV1:
    structural_observation_count: int
    generative_draw_count: int = 0
    environment_interaction_count: int = 0
    exact_kernel_call_count: int = 0
    dynamics_outcome_count: int = 0
    reward_label_count: int = 0
    certificate_label_count: int = 0
    lane: str = "ONLINE_TARGET_APPLICABILITY"

    def __post_init__(self) -> None:
        _integer(
            self.structural_observation_count,
            "target structural observations",
            1,
        )
        for value, field in (
            (self.generative_draw_count, "target generative draws"),
            (
                self.environment_interaction_count,
                "target environment interactions",
            ),
            (self.exact_kernel_call_count, "target exact kernel calls"),
            (self.dynamics_outcome_count, "target dynamics outcomes"),
            (self.reward_label_count, "target reward labels"),
            (
                self.certificate_label_count,
                "target certificate labels",
            ),
        ):
            _integer(value, field)
        if (
            any(
                value != 0
                for value in (
                    self.generative_draw_count,
                    self.environment_interaction_count,
                    self.exact_kernel_call_count,
                    self.dynamics_outcome_count,
                    self.reward_label_count,
                    self.certificate_label_count,
                )
            )
            or self.lane != "ONLINE_TARGET_APPLICABILITY"
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "target applicability may contain structural observations only"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.proposal_only_metaprior_online_accounting.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "lane": self.lane,
            "structural_observation_count": (
                self.structural_observation_count
            ),
            "generative_draw_count": self.generative_draw_count,
            "environment_interaction_count": (
                self.environment_interaction_count
            ),
            "exact_kernel_call_count": self.exact_kernel_call_count,
            "dynamics_outcome_count": self.dynamics_outcome_count,
            "reward_label_count": self.reward_label_count,
            "certificate_label_count": self.certificate_label_count,
        }

    @property
    def accounting_id(self) -> str:
        return _content_id("online_accounting", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_id": self.accounting_id}


@dataclass(frozen=True, slots=True)
class TargetProposalApplicabilityV1:
    target_context_id: str
    target_family_id: str
    target_adapter_id: str
    role_schema_id: str
    candidate_registry_id: str
    query_id: str
    build_epoch_id: str
    frontier_snapshot_id: str
    structural_observation_ids: tuple[str, ...]
    available_capability_ids: tuple[str, ...]
    online_accounting: OnlineTargetContextAccountingV1
    target_outcomes_used: bool = False
    target_rewards_used: bool = False
    target_certificates_used: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.target_context_id, "target context"),
            (self.target_family_id, "target family"),
            (self.target_adapter_id, "target adapter"),
            (self.role_schema_id, "target role schema"),
            (self.candidate_registry_id, "target candidate registry"),
            (self.query_id, "target query"),
            (self.build_epoch_id, "target build epoch"),
            (self.frontier_snapshot_id, "target frontier"),
        ):
            _cid(value, field)
        _canonical_ids(
            self.structural_observation_ids,
            "target structural observations",
        )
        _canonical_ids(
            self.available_capability_ids,
            "target available capabilities",
        )
        if (
            type(self.online_accounting)
            is not OnlineTargetContextAccountingV1
            or self.online_accounting.structural_observation_count
            != len(self.structural_observation_ids)
            or self.target_outcomes_used is not False
            or self.target_rewards_used is not False
            or self.target_certificates_used is not False
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "target applicability leaked outcomes, rewards, or certificates"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.proposal_only_metaprior_target_applicability.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "target_context_id": self.target_context_id,
            "target_family_id": self.target_family_id,
            "target_adapter_id": self.target_adapter_id,
            "role_schema_id": self.role_schema_id,
            "candidate_registry_id": self.candidate_registry_id,
            "query_id": self.query_id,
            "build_epoch_id": self.build_epoch_id,
            "frontier_snapshot_id": self.frontier_snapshot_id,
            "structural_observation_ids": list(
                self.structural_observation_ids
            ),
            "available_capability_ids": list(
                self.available_capability_ids
            ),
            "online_accounting_id": self.online_accounting.accounting_id,
            "target_outcomes_used": self.target_outcomes_used,
            "target_rewards_used": self.target_rewards_used,
            "target_certificates_used": self.target_certificates_used,
        }

    @property
    def applicability_id(self) -> str:
        return _content_id("target_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "online_accounting": self.online_accounting.to_document(),
            "applicability_id": self.applicability_id,
        }


@dataclass(frozen=True, slots=True)
class TargetProposalRequestV1:
    prior_id: str
    target_applicability_id: str
    allowed_kinds: tuple[ProposalCandidateKind, ...]
    maximum_proposals: int

    def __post_init__(self) -> None:
        _cid(self.prior_id, "proposal request prior")
        _cid(
            self.target_applicability_id,
            "proposal request applicability",
        )
        _canonical_kinds(self.allowed_kinds)
        if (
            type(self.maximum_proposals) is not int
            or not 1 <= self.maximum_proposals <= 8
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "proposal request exceeds the bounded profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proposal_only_metaprior_request.v1",
            "schema_version": SCHEMA_VERSION,
            "prior_id": self.prior_id,
            "target_applicability_id": self.target_applicability_id,
            "allowed_kinds": [item.value for item in self.allowed_kinds],
            "maximum_proposals": self.maximum_proposals,
            "ranking_semantics": RANKING_SEMANTICS,
        }

    @property
    def request_id(self) -> str:
        return _content_id("request", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class ProposalOnlyRankingV1:
    status: ProposalStatus
    refusal_reason: str | None
    prior_id: str
    request_id: str
    target_applicability_id: str
    target_context_id: str
    query_id: str
    build_epoch_id: str
    frontier_snapshot_id: str
    eligible_ranked_candidate_ids: tuple[str, ...]
    selected_candidate_ids: tuple[str, ...]
    offline_accounting: OfflineSourceObservationAccountingV1
    online_accounting: OnlineTargetContextAccountingV1
    proposal_only: bool = True
    may_certify: bool = False
    may_narrow_target_envelopes: bool = False
    target_local_acquisition_required: bool = True
    target_local_certificate_required: bool = True
    certificate_authority: str = "NONE"
    official_execution_allowed: bool = False
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not ProposalStatus:
            raise ProposalOnlyMetaPriorInvariantViolation(
                "proposal status changed runtime type"
            )
        for value, field in (
            (self.prior_id, "proposal prior"),
            (self.request_id, "proposal request"),
            (self.target_applicability_id, "proposal applicability"),
            (self.target_context_id, "proposal target context"),
            (self.query_id, "proposal query"),
            (self.build_epoch_id, "proposal build epoch"),
            (self.frontier_snapshot_id, "proposal frontier"),
        ):
            _cid(value, field)
        if (
            type(self.eligible_ranked_candidate_ids) is not tuple
            or any(
                type(item) is not str
                for item in self.eligible_ranked_candidate_ids
            )
            or len(set(self.eligible_ranked_candidate_ids))
            != len(self.eligible_ranked_candidate_ids)
            or type(self.selected_candidate_ids) is not tuple
            or any(
                type(item) is not str for item in self.selected_candidate_ids
            )
            or len(set(self.selected_candidate_ids))
            != len(self.selected_candidate_ids)
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "eligible and selected candidate IDs must be ordered unique tuples"
            )
        for item in self.eligible_ranked_candidate_ids:
            _cid(item, "eligible ranked candidate")
        for item in self.selected_candidate_ids:
            _cid(item, "selected candidate")
        if (
            not set(self.selected_candidate_ids)
            <= set(self.eligible_ranked_candidate_ids)
            or self.selected_candidate_ids
            != self.eligible_ranked_candidate_ids[
                : len(self.selected_candidate_ids)
            ]
            or type(self.offline_accounting)
            is not OfflineSourceObservationAccountingV1
            or type(self.online_accounting)
            is not OnlineTargetContextAccountingV1
            or self.proposal_only is not True
            or self.may_certify is not False
            or self.may_narrow_target_envelopes is not False
            or self.target_local_acquisition_required is not True
            or self.target_local_certificate_required is not True
            or self.certificate_authority != "NONE"
            or self.official_execution_allowed is not False
            or self.sample_efficiency_claimed is not False
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "proposal authority, accounting, or selection changed"
            )
        ready = self.status is ProposalStatus.PROPOSAL_READY
        if (
            ready
            and (
                self.refusal_reason is not None
                or not self.eligible_ranked_candidate_ids
                or not self.selected_candidate_ids
            )
        ) or (
            not ready
            and (
                type(self.refusal_reason) is not str
                or not self.refusal_reason
                or self.eligible_ranked_candidate_ids
                or self.selected_candidate_ids
            )
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "ready/refused proposal shape is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.proposal_only_metaprior_ranking.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": self.status.value,
            "refusal_reason": self.refusal_reason,
            "prior_id": self.prior_id,
            "request_id": self.request_id,
            "target_applicability_id": self.target_applicability_id,
            "target_context_id": self.target_context_id,
            "query_id": self.query_id,
            "build_epoch_id": self.build_epoch_id,
            "frontier_snapshot_id": self.frontier_snapshot_id,
            "eligible_ranked_candidate_ids": list(
                self.eligible_ranked_candidate_ids
            ),
            "selected_candidate_ids": list(
                self.selected_candidate_ids
            ),
            "offline_accounting_id": (
                self.offline_accounting.accounting_id
            ),
            "online_accounting_id": self.online_accounting.accounting_id,
            "proposal_only": self.proposal_only,
            "may_certify": self.may_certify,
            "may_narrow_target_envelopes": (
                self.may_narrow_target_envelopes
            ),
            "target_local_acquisition_required": (
                self.target_local_acquisition_required
            ),
            "target_local_certificate_required": (
                self.target_local_certificate_required
            ),
            "certificate_authority": self.certificate_authority,
            "official_execution_allowed": self.official_execution_allowed,
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
        }

    @property
    def proposal_id(self) -> str:
        return _content_id("proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "offline_accounting": self.offline_accounting.to_document(),
            "online_accounting": self.online_accounting.to_document(),
            "proposal_id": self.proposal_id,
        }


def _refused_proposal(
    status: ProposalStatus,
    reason: str,
    prior: SourceConsensusMetaPriorV1,
    target: TargetProposalApplicabilityV1,
    request: TargetProposalRequestV1,
) -> ProposalOnlyRankingV1:
    if status is ProposalStatus.PROPOSAL_READY:
        raise ProposalOnlyMetaPriorInvariantViolation(
            "refusal helper cannot issue a ready proposal"
        )
    return ProposalOnlyRankingV1(
        status=status,
        refusal_reason=_text(reason, "proposal refusal reason"),
        prior_id=prior.prior_id,
        request_id=request.request_id,
        target_applicability_id=target.applicability_id,
        target_context_id=target.target_context_id,
        query_id=target.query_id,
        build_epoch_id=target.build_epoch_id,
        frontier_snapshot_id=target.frontier_snapshot_id,
        eligible_ranked_candidate_ids=(),
        selected_candidate_ids=(),
        offline_accounting=prior.offline_accounting,
        online_accounting=target.online_accounting,
    )


def rank_target_proposals_v1(
    registry: ProposalCandidateRegistryV1,
    envelope: ProposalTransferEnvelopeV1,
    prior: SourceConsensusMetaPriorV1,
    target: TargetProposalApplicabilityV1,
    request: TargetProposalRequestV1,
) -> ProposalOnlyRankingV1:
    """Return a bounded ranking or an empty fail-closed refusal.

    This function receives no kernel, transition outcomes, rewards, plans,
    value estimates, risk estimates, audits, or certificates.
    """

    exact_types = (
        (registry, ProposalCandidateRegistryV1),
        (envelope, ProposalTransferEnvelopeV1),
        (prior, SourceConsensusMetaPriorV1),
        (target, TargetProposalApplicabilityV1),
        (request, TargetProposalRequestV1),
    )
    if any(type(value) is not expected for value, expected in exact_types):
        raise ProposalOnlyMetaPriorInvariantViolation(
            "proposal runner rejects runtime substitutions"
        )
    identity_matches = (
        envelope.candidate_registry_id == registry.registry_id
        and envelope.role_schema_id == registry.role_schema_id
        and prior.candidate_registry_id == registry.registry_id
        and prior.transfer_envelope_id == envelope.envelope_id
        and target.candidate_registry_id == registry.registry_id
        and target.role_schema_id == registry.role_schema_id
        and request.prior_id == prior.prior_id
        and request.target_applicability_id == target.applicability_id
        and request.maximum_proposals <= envelope.maximum_proposals
    )
    if not identity_matches:
        return _refused_proposal(
            ProposalStatus.IDENTITY_MISMATCH_REFUSED,
            "candidate/prior/request/target identity chain mismatch",
            prior,
            target,
            request,
        )
    if (
        target.target_family_id
        not in envelope.allowed_target_family_ids
        or target.target_adapter_id
        not in envelope.allowed_target_adapter_ids
        or target.target_context_id in prior.source_context_ids
    ):
        return _refused_proposal(
            ProposalStatus.OOD_TARGET_REFUSED,
            (
                "target family/adapter is outside the frozen transfer "
                "envelope or target context overlaps source evidence"
            ),
            prior,
            target,
            request,
        )
    available = set(target.available_capability_ids)
    allowed_kinds = set(request.allowed_kinds)
    compatible_candidate_ids = {
        candidate.candidate_id
        for candidate in registry.candidates
        if candidate.kind in allowed_kinds
        and set(candidate.required_capability_ids) <= available
    }
    if not compatible_candidate_ids:
        kind_candidate_exists = any(
            candidate.kind in allowed_kinds
            for candidate in registry.candidates
        )
        return _refused_proposal(
            (
                ProposalStatus.MISSING_CAPABILITY_REFUSED
                if kind_candidate_exists
                else ProposalStatus.NO_REGISTERED_CANDIDATE_REFUSED
            ),
            (
                "no allowed candidate has target-observed structural support"
                if kind_candidate_exists
                else "the registry has no candidate of an allowed kind"
            ),
            prior,
            target,
            request,
        )
    ranked = tuple(
        candidate_id
        for candidate_id in prior.ranked_candidate_ids
        if candidate_id in compatible_candidate_ids
    )
    selected = ranked[: request.maximum_proposals]
    return ProposalOnlyRankingV1(
        status=ProposalStatus.PROPOSAL_READY,
        refusal_reason=None,
        prior_id=prior.prior_id,
        request_id=request.request_id,
        target_applicability_id=target.applicability_id,
        target_context_id=target.target_context_id,
        query_id=target.query_id,
        build_epoch_id=target.build_epoch_id,
        frontier_snapshot_id=target.frontier_snapshot_id,
        eligible_ranked_candidate_ids=ranked,
        selected_candidate_ids=selected,
        offline_accounting=prior.offline_accounting,
        online_accounting=target.online_accounting,
    )


@dataclass(frozen=True, slots=True)
class ProposalOnlyMetaPriorVerificationV1:
    proposal_id: str
    prior_id: str
    request_id: str
    target_applicability_id: str
    status: ProposalStatus
    ranking_replayed: bool = True
    identity_chain_verified: bool = True
    proposal_only_lock_verified: bool = True
    accounting_lanes_separate: bool = True
    certificate_verified: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.proposal_id, "verified proposal"),
            (self.prior_id, "verified prior"),
            (self.request_id, "verified request"),
            (
                self.target_applicability_id,
                "verified target applicability",
            ),
        ):
            _cid(value, field)
        if (
            type(self.status) is not ProposalStatus
            or self.ranking_replayed is not True
            or self.identity_chain_verified is not True
            or self.proposal_only_lock_verified is not True
            or self.accounting_lanes_separate is not True
            or self.certificate_verified is not False
        ):
            raise ProposalOnlyMetaPriorInvariantViolation(
                "proposal-only verification claim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.proposal_only_metaprior_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposal_id": self.proposal_id,
            "prior_id": self.prior_id,
            "request_id": self.request_id,
            "target_applicability_id": self.target_applicability_id,
            "status": self.status.value,
            "ranking_replayed": self.ranking_replayed,
            "identity_chain_verified": self.identity_chain_verified,
            "proposal_only_lock_verified": (
                self.proposal_only_lock_verified
            ),
            "accounting_lanes_separate": (
                self.accounting_lanes_separate
            ),
            "certificate_verified": self.certificate_verified,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_proposal_only_metaprior_v1(
    registry: ProposalCandidateRegistryV1,
    envelope: ProposalTransferEnvelopeV1,
    source_log: SourceProposalObservationLogV1,
    prior: SourceConsensusMetaPriorV1,
    target: TargetProposalApplicabilityV1,
    request: TargetProposalRequestV1,
    claimed: ProposalOnlyRankingV1,
) -> ProposalOnlyMetaPriorVerificationV1:
    """Rebuild source ranks and target proposal; never verify a certificate."""

    if type(claimed) is not ProposalOnlyRankingV1:
        raise ProposalOnlyMetaPriorInvariantViolation(
            "proposal verifier rejects runtime substitutions"
        )
    expected_prior = build_source_consensus_metaprior_v1(
        registry,
        envelope,
        source_log,
    )
    if prior.to_document() != expected_prior.to_document():
        raise ProposalOnlyMetaPriorInvariantViolation(
            "source meta-prior replay mismatch"
        )
    expected = rank_target_proposals_v1(
        registry,
        envelope,
        prior,
        target,
        request,
    )
    if claimed.to_document() != expected.to_document():
        raise ProposalOnlyMetaPriorInvariantViolation(
            "proposal ranking replay mismatch"
        )
    return ProposalOnlyMetaPriorVerificationV1(
        proposal_id=claimed.proposal_id,
        prior_id=prior.prior_id,
        request_id=request.request_id,
        target_applicability_id=target.applicability_id,
        status=claimed.status,
    )


__all__ = [
    "CONTRACT_VERSION",
    "PROFILE_KEY",
    "RANKING_SEMANTICS",
    "OfflineSourceObservationAccountingV1",
    "OnlineTargetContextAccountingV1",
    "ProposalCandidateKind",
    "ProposalCandidateRegistryV1",
    "ProposalCandidateV1",
    "ProposalOnlyMetaPriorInvariantViolation",
    "ProposalOnlyMetaPriorVerificationV1",
    "ProposalOnlyRankingV1",
    "ProposalStatus",
    "ProposalTransferEnvelopeV1",
    "SourceConsensusMetaPriorV1",
    "SourceConsensusScoreV1",
    "SourceProposalObservationLogV1",
    "SourceProposalObservationV1",
    "TargetProposalApplicabilityV1",
    "TargetProposalRequestV1",
    "build_proposal_candidate_registry_v1",
    "build_source_consensus_metaprior_v1",
    "build_source_proposal_observation_log_v1",
    "rank_target_proposals_v1",
    "verify_proposal_only_metaprior_v1",
]
