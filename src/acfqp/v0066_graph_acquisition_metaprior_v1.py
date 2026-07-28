"""Source-only acquisition-operator meta-prior for the V0-066 graph arm.

The portable ``n=4`` source authority contains three registered graph
contexts.  This module preregisters a matched source-only experiment on every
root (remaining-horizon two) row in those contexts:

* the V0-066 fixed 131072-draw Hoeffding acquisition; and
* a source scoring proxy for the V0-067 sequential variance-adaptive
  proof-frontier operator.

The proxy arms use the same deterministic row seed, confidence alpha, target
half-width, hard cap, and failure-event semantics.  Arm work is charged
separately even though replay can derive both results from one common-random-
number stream.  Source transition probabilities are never read to score an
operator.  The registered source simulator supplies every Bernoulli draw.
The proxy stops when the failure-event CS width is at most twice the
registered radius; the actual target operator instead stops at the first
sound plan certificate or its cap.  Proxy success is never a certificate.

The learned ordering is proposal-only.  W5, K6, and K6-minus-edge contribute
only structural, query, epoch, and pre-acquisition frontier identities.  No
target transition, reward, failure label, audit, plan value, or certificate
enters the proposal.  Target-local acquisition and certification remain
mandatory.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import functools
import hashlib
from typing import Any, Mapping

import acfqp.cross_graph_relational_support_v1 as source_graph
import acfqp.proposal_only_metaprior_v1 as meta
import acfqp.sequential_bernoulli_acquisition_v1 as sequential
import acfqp.variable_order_graph_rapm_v1 as target_graph
from acfqp.domains.g2048 import G2048Action, G2048State
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.portable_relational_skeleton_v1 import (
    AnonymousRelationalObservationLogV1,
    PortableRelationalSkeletonV1,
    RelationalObservedRowV1,
    verify_portable_relational_skeleton_v1,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.31.0"
PROFILE_KEY = "v0067_v0066_graph_acquisition_metaprior_v0"
SOURCE_TRIAL_SEED = "acfqp-v0067-v0066-graph-source-paired-seed-v1"
SOURCE_PRNG_SEMANTICS = (
    "splitmix64_counter_rejection_uniform_cell_rank_v1"
)
SOURCE_CLAIM_SCOPE = (
    "DESCRIPTIVE_REGISTERED_SOURCE_CONTEXTS_AND_PAIRED_SEEDS_ONLY"
)
SOURCE_SCORING_PROXY_RULE = "first_failure_event_cs_width_le_2radius"
SUCCESS_STATUS = "SOURCE_RANKED_GRAPH_ACQUISITION_PROPOSALS_READY"


DOMAIN_TAGS = {
    "semantics": "acfqp:v0066-graph-acquisition-operator-semantics:v1",
    "capability": "acfqp:v0066-graph-acquisition-capability:v1",
    "source_family": "acfqp:v0066-graph-source-trial-family:v1",
    "seed": "acfqp:v0066-graph-source-trial-seed:v1",
    "row_trial": "acfqp:v0066-graph-paired-source-row-trial:v1",
    "source_evidence": (
        "acfqp:v0066-graph-paired-source-acquisition-evidence:v1"
    ),
    "source_proxy": "acfqp:v0066-graph-source-scoring-proxy:v1",
    "target_adapter": "acfqp:v0066-graph-target-acquisition-adapter:v1",
    "build_epoch": (
        "acfqp:v0066-graph-preacquisition-build-epoch:v1"
    ),
    "frontier": "acfqp:v0066-graph-preacquisition-frontier:v1",
    "structural_observation": (
        "acfqp:v0066-graph-target-structural-observation:v1"
    ),
    "target_proposal": (
        "acfqp:v0066-graph-target-acquisition-proposal:v1"
    ),
    "campaign": "acfqp:v0066-graph-acquisition-metaprior-campaign:v1",
    "verification": (
        "acfqp:v0066-graph-acquisition-metaprior-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("graph acquisition meta-prior domains must be unique")


class V0066GraphAcquisitionMetaPriorInvariantViolation(ValueError):
    """A source trial, target isolation, identity, or authority failed."""


class GraphAcquisitionOperatorKind(str, Enum):
    FIXED_FULL_ROW_HOEFFDING = "FIXED_FULL_ROW_HOEFFDING"
    SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER = (
        "SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER"
    )


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(
        tag.encode("utf-8") + b"\x00" + encoded
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


SOURCE_SCORING_PROXY_ID = _content_id(
    "source_proxy",
    {
        "schema": "acfqp.v0066_graph_source_scoring_proxy.v1",
        "schema_version": SCHEMA_VERSION,
        "rule": SOURCE_SCORING_PROXY_RULE,
        "event_semantics": "postmerge_failure_indicator",
        "target_operator_stopping_rule": (
            "first_sound_plan_certificate_or_cap"
        ),
        "may_certify": False,
    },
)


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def _ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or not values
        or values != tuple(sorted(set(values)))
    ):
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            f"{field} must be a nonempty canonical ID set"
        )
    for value in values:
        _cid(value, field)
    return values


def _capability_id(capability_key: str) -> str:
    return _content_id(
        "capability",
        {
            "schema": "acfqp.v0066_graph_acquisition_capability.v1",
            "schema_version": SCHEMA_VERSION,
            "capability_key": capability_key,
        },
    )


BOUNDED_BERNOULLI_EVENT_CAPABILITY_ID = _capability_id(
    "bounded_bernoulli_failure_event"
)
PROOF_FRONTIER_IDENTITY_CAPABILITY_ID = _capability_id(
    "identity_bound_preacquisition_proof_frontier"
)
FIXED_HOEFFDING_PROFILE_CAPABILITY_ID = _capability_id(
    "fixed_hoeffding_alpha_radius_cap"
)
TARGET_LOCAL_IID_STREAM_CAPABILITY_ID = _capability_id(
    "target_local_registered_iid_stream"
)
TIME_UNIFORM_CS_CAPABILITY_ID = _capability_id(
    "time_uniform_ville_confidence_sequence"
)


@dataclass(frozen=True, slots=True)
class GraphAcquisitionOperatorSemanticsV1:
    operator_kind: GraphAcquisitionOperatorKind
    row_schedule: str
    stopping_rule: str
    confidence_alpha: Fraction
    target_half_width: Fraction
    maximum_draws_per_row: int
    confidence_method_id: str
    target_local_evidence_required: bool = True
    proposal_may_certify: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.operator_kind) is not GraphAcquisitionOperatorKind
            or type(self.confidence_alpha) is not Fraction
            or self.confidence_alpha != target_graph.PER_OBLIGATION_TAIL_UPPER
            or type(self.target_half_width) is not Fraction
            or self.target_half_width != target_graph.HOEFFDING_RADIUS
            or self.maximum_draws_per_row
            != target_graph.SAMPLE_COUNT_PER_ROW
            or self.target_local_evidence_required is not True
            or self.proposal_may_certify is not False
        ):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "graph acquisition operator profile changed"
            )
        if self.operator_kind is (
            GraphAcquisitionOperatorKind.FIXED_FULL_ROW_HOEFFDING
        ):
            expected = (
                "every_authorized_row",
                "fixed_draw_count",
                "fixed_time_hoeffding_v1",
            )
        else:
            expected = (
                "earliest_failed_proof_frontier",
                "first_sound_plan_certificate_or_cap",
                sequential.METHOD_ID,
            )
        if (
            self.row_schedule,
            self.stopping_rule,
            self.confidence_method_id,
        ) != expected:
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "operator semantics do not match their registered kind"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v0066_graph_acquisition_operator_semantics.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "operator_kind": self.operator_kind.value,
            "row_schedule": self.row_schedule,
            "stopping_rule": self.stopping_rule,
            "confidence_alpha": _fdoc(self.confidence_alpha),
            "target_half_width": _fdoc(self.target_half_width),
            "maximum_draws_per_row": self.maximum_draws_per_row,
            "confidence_method_id": self.confidence_method_id,
            "target_local_evidence_required": (
                self.target_local_evidence_required
            ),
            "proposal_may_certify": self.proposal_may_certify,
        }

    @property
    def semantics_id(self) -> str:
        return _content_id("semantics", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantics_id": self.semantics_id}


def registered_graph_acquisition_operator_semantics_v1(
) -> tuple[GraphAcquisitionOperatorSemanticsV1, ...]:
    profile = sequential.v0067_default_sequential_profile_v1()
    if (
        profile.confidence_alpha
        != target_graph.PER_OBLIGATION_TAIL_UPPER
        or profile.target_half_width != target_graph.HOEFFDING_RADIUS
        or profile.max_draws != target_graph.SAMPLE_COUNT_PER_ROW
    ):
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "sequential profile is not matched to V0-066"
        )
    return (
        GraphAcquisitionOperatorSemanticsV1(
            GraphAcquisitionOperatorKind.FIXED_FULL_ROW_HOEFFDING,
            "every_authorized_row",
            "fixed_draw_count",
            profile.confidence_alpha,
            profile.target_half_width,
            profile.max_draws,
            "fixed_time_hoeffding_v1",
        ),
        GraphAcquisitionOperatorSemanticsV1(
            GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER,
            "earliest_failed_proof_frontier",
            "first_sound_plan_certificate_or_cap",
            profile.confidence_alpha,
            profile.target_half_width,
            profile.max_draws,
            profile.method_id,
        ),
    )


def _operator_candidates(
    role_schema_id: str,
) -> tuple[
    tuple[GraphAcquisitionOperatorSemanticsV1, meta.ProposalCandidateV1],
    ...,
]:
    _cid(role_schema_id, "operator candidate role schema")
    rows = []
    for semantics in registered_graph_acquisition_operator_semantics_v1():
        if semantics.operator_kind is (
            GraphAcquisitionOperatorKind.FIXED_FULL_ROW_HOEFFDING
        ):
            required = (
                BOUNDED_BERNOULLI_EVENT_CAPABILITY_ID,
                FIXED_HOEFFDING_PROFILE_CAPABILITY_ID,
                PROOF_FRONTIER_IDENTITY_CAPABILITY_ID,
            )
        else:
            required = (
                BOUNDED_BERNOULLI_EVENT_CAPABILITY_ID,
                PROOF_FRONTIER_IDENTITY_CAPABILITY_ID,
                TARGET_LOCAL_IID_STREAM_CAPABILITY_ID,
                TIME_UNIFORM_CS_CAPABILITY_ID,
            )
        candidate = meta.ProposalCandidateV1(
            candidate_key=semantics.operator_kind.value,
            kind=meta.ProposalCandidateKind.SUPPORT,
            semantics_id=semantics.semantics_id,
            required_capability_ids=tuple(sorted(required)),
            complexity=1,
        )
        rows.append((semantics, candidate))
    return tuple(rows)


def _source_family_id(
    source_log_id: str,
    source_context_id: str,
) -> str:
    return _content_id(
        "source_family",
        {
            "schema": "acfqp.v0066_graph_source_trial_family.v1",
            "schema_version": SCHEMA_VERSION,
            "source_log_id": source_log_id,
            "source_context_id": source_context_id,
            "remaining_horizon": 2,
            "event_semantics": "postmerge_failure_indicator",
        },
    )


def _source_contexts_by_id(
) -> dict[str, source_graph.CrossGraphStructuralContextV1]:
    return {
        item.context_id: item
        for item in source_graph.registered_cross_graph_contexts_v1(
            source_graph.CrossGraphSplit.SOURCE
        )
    }


def _source_root_rows(
    source_log: AnonymousRelationalObservationLogV1,
) -> tuple[RelationalObservedRowV1, ...]:
    if type(source_log) is not AnonymousRelationalObservationLogV1:
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "source root-row projection requires the exact log type"
        )
    rows = tuple(
        item
        for item in source_log.rows
        if item.state.remaining_horizon == 2
    )
    contexts = _source_contexts_by_id()
    if (
        not rows
        or any(
            item.state.structural_context_id not in contexts for item in rows
        )
        or tuple(item.observed_row_id for item in rows)
        != tuple(sorted({item.observed_row_id for item in rows}))
    ):
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "source H2 rows are incomplete or noncanonical"
        )
    return rows


_MASK64 = (1 << 64) - 1
_GAMMA64 = 0x9E3779B97F4A7C15
_UNIFORM_DENOMINATOR = 200
_UNIFORM_ACCEPT_LIMIT = (
    (1 << 64) - ((1 << 64) % _UNIFORM_DENOMINATOR)
)


def _splitmix64(value: int) -> int:
    value = (value + _GAMMA64) & _MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
    return (value ^ (value >> 31)) & _MASK64


def _row_seed(row_id: str) -> tuple[int, str]:
    _cid(row_id, "source trial row")
    payload = {
        "schema": "acfqp.v0066_graph_source_trial_seed.v1",
        "schema_version": SCHEMA_VERSION,
        "source_trial_seed": SOURCE_TRIAL_SEED,
        "source_row_id": row_id,
        "prng_semantics": SOURCE_PRNG_SEMANTICS,
    }
    digest = hashlib.sha256(
        DOMAIN_TAGS["seed"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).digest()
    return int.from_bytes(digest[:8], "big"), digest.hex()


def _ground_action(row: RelationalObservedRowV1) -> G2048Action:
    parts = row.action.opaque_action_key.split(":")
    if (
        len(parts) != 4
        or parts[0] != "merge"
        or any(not item.isdigit() for item in parts[1:])
    ):
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "source action key is not the frozen merge encoding"
        )
    return G2048Action(*(int(item) for item in parts[1:]))


def _pack_boolean_prefix(draws: bytearray, value: bool, index: int) -> None:
    if index % 8 == 0:
        draws.append(0)
    if value:
        draws[-1] |= 1 << (index % 8)


@dataclass(frozen=True, slots=True)
class SourceSequentialCheckpointSummaryV1:
    """Compact source-trial projection of the authoritative CS checkpoint."""

    draw_count: int
    failure_count: int
    lower_probability: Fraction
    upper_probability: Fraction
    interval_width: Fraction
    exact_likelihood_comparisons: int
    log_search_evaluations: int

    def __post_init__(self) -> None:
        if (
            type(self.draw_count) is not int
            or self.draw_count <= 0
            or type(self.failure_count) is not int
            or not 0 <= self.failure_count <= self.draw_count
            or any(
                type(item) is not Fraction
                for item in (
                    self.lower_probability,
                    self.upper_probability,
                    self.interval_width,
                )
            )
            or not 0
            <= self.lower_probability
            <= Fraction(self.failure_count, self.draw_count)
            <= self.upper_probability
            <= 1
            or self.interval_width
            != self.upper_probability - self.lower_probability
            or type(self.exact_likelihood_comparisons) is not int
            or self.exact_likelihood_comparisons < 0
            or type(self.log_search_evaluations) is not int
            or self.log_search_evaluations < 0
        ):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "source sequential checkpoint summary is inconsistent"
            )

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: sequential.AnytimeBernoulliCheckpointV1,
    ) -> "SourceSequentialCheckpointSummaryV1":
        if type(checkpoint) is not sequential.AnytimeBernoulliCheckpointV1:
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "source checkpoint projection rejects substitutions"
            )
        return cls(
            draw_count=checkpoint.draw_count,
            failure_count=checkpoint.success_count,
            lower_probability=checkpoint.lower_probability,
            upper_probability=checkpoint.upper_probability,
            interval_width=checkpoint.interval_width,
            exact_likelihood_comparisons=(
                checkpoint.exact_likelihood_comparisons
            ),
            log_search_evaluations=checkpoint.log_search_evaluations,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "draw_count": self.draw_count,
            "failure_count": self.failure_count,
            "lower_probability": _fdoc(self.lower_probability),
            "upper_probability": _fdoc(self.upper_probability),
            "interval_width": _fdoc(self.interval_width),
            "exact_likelihood_comparisons": (
                self.exact_likelihood_comparisons
            ),
            "log_search_evaluations": self.log_search_evaluations,
            "authoritative_method_id": sequential.METHOD_ID,
        }


@dataclass(frozen=True, slots=True)
class PairedSourceRowAcquisitionTrialV1:
    source_context_id: str
    source_family_id: str
    source_row_id: str
    seed_id: str
    fixed_candidate_id: str
    sequential_candidate_id: str
    sequential_profile_id: str
    fixed_draw_count: int
    fixed_failure_count: int
    sequential_draw_count: int
    sequential_failure_count: int
    sequential_checkpoints: tuple[SourceSequentialCheckpointSummaryV1, ...]
    random_word_count: int
    rejection_count: int
    full_transcript_sha256: str
    sequential_prefix_sha256: str
    sequential_certified_width: bool
    source_scoring_proxy_id: str = SOURCE_SCORING_PROXY_ID
    source_scoring_proxy_rule: str = SOURCE_SCORING_PROXY_RULE
    source_scoring_proxy_may_certify: bool = False
    exact_probability_values_used_for_score: bool = False
    target_inputs_used: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.source_context_id, "source trial context"),
            (self.source_family_id, "source trial family"),
            (self.source_row_id, "source trial row"),
            (self.seed_id, "source trial seed"),
            (self.fixed_candidate_id, "fixed trial candidate"),
            (self.sequential_candidate_id, "sequential trial candidate"),
            (self.sequential_profile_id, "sequential trial profile"),
        ):
            _cid(value, field)
        if (
            self.fixed_draw_count != target_graph.SAMPLE_COUNT_PER_ROW
            or type(self.fixed_failure_count) is not int
            or not 0 <= self.fixed_failure_count <= self.fixed_draw_count
            or type(self.sequential_draw_count) is not int
            or not 0 < self.sequential_draw_count <= self.fixed_draw_count
            or type(self.sequential_failure_count) is not int
            or not 0
            <= self.sequential_failure_count
            <= self.sequential_draw_count
            or type(self.sequential_checkpoints) is not tuple
            or not self.sequential_checkpoints
            or any(
                type(item) is not SourceSequentialCheckpointSummaryV1
                for item in self.sequential_checkpoints
            )
            or self.sequential_checkpoints[-1].draw_count
            != self.sequential_draw_count
            or self.sequential_checkpoints[-1].failure_count
            != self.sequential_failure_count
            or type(self.random_word_count) is not int
            or self.random_word_count < self.fixed_draw_count
            or self.rejection_count
            != self.random_word_count - self.fixed_draw_count
            or any(
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
                for value in (
                    self.full_transcript_sha256,
                    self.sequential_prefix_sha256,
                )
            )
            or self.sequential_certified_width
            != (
                self.sequential_checkpoints[-1].interval_width
                <= 2 * target_graph.HOEFFDING_RADIUS
            )
            or self.source_scoring_proxy_id != SOURCE_SCORING_PROXY_ID
            or self.source_scoring_proxy_rule != SOURCE_SCORING_PROXY_RULE
            or self.source_scoring_proxy_may_certify is not False
            or self.exact_probability_values_used_for_score is not False
            or self.target_inputs_used != 0
        ):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "paired source row trial is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0066_graph_paired_source_row_trial.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "source_family_id": self.source_family_id,
            "source_row_id": self.source_row_id,
            "seed_id": self.seed_id,
            "fixed_candidate_id": self.fixed_candidate_id,
            "sequential_candidate_id": self.sequential_candidate_id,
            "sequential_profile_id": self.sequential_profile_id,
            "fixed_draw_count": self.fixed_draw_count,
            "fixed_failure_count": self.fixed_failure_count,
            "sequential_draw_count": self.sequential_draw_count,
            "sequential_failure_count": self.sequential_failure_count,
            "sequential_checkpoints": [
                item.to_document() for item in self.sequential_checkpoints
            ],
            "random_word_count": self.random_word_count,
            "rejection_count": self.rejection_count,
            "full_transcript_sha256": self.full_transcript_sha256,
            "sequential_prefix_sha256": self.sequential_prefix_sha256,
            "sequential_certified_width": (
                self.sequential_certified_width
            ),
            "source_scoring_proxy_id": self.source_scoring_proxy_id,
            "source_scoring_proxy_rule": self.source_scoring_proxy_rule,
            "source_scoring_proxy_may_certify": False,
            "exact_probability_values_used_for_score": False,
            "target_inputs_used": 0,
            "paired_seed": True,
            "event_semantics": "postmerge_failure_indicator",
            "source_prng_semantics": SOURCE_PRNG_SEMANTICS,
        }

    @property
    def trial_id(self) -> str:
        return _content_id("row_trial", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trial_id": self.trial_id}


def _run_paired_source_row_trial(
    row: RelationalObservedRowV1,
    source_log_id: str,
    fixed_candidate_id: str,
    sequential_candidate_id: str,
) -> PairedSourceRowAcquisitionTrialV1:
    if type(row) is not RelationalObservedRowV1:
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "paired trial requires an exact source row"
        )
    _cid(source_log_id, "paired trial source log")
    contexts = _source_contexts_by_id()
    context = contexts[row.state.structural_context_id]
    kernel = source_graph.GraphMergeKernelV1(context)
    state = G2048State(row.state.resource_attributes)
    action = _ground_action(row)
    # One exact source-kernel call registers the failure label attached to
    # each structural atom.  Its probability field is deliberately ignored.
    failure_by_atom = tuple(
        outcome.failure for outcome in kernel.step(state, action)
    )
    if len(failure_by_atom) != 4:
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "registered n=4 source row no longer has four structural atoms"
        )
    profile = sequential.v0067_default_sequential_profile_v1()
    seed, seed_id = _row_seed(row.observed_row_id)
    full_bits = bytearray()
    failure_count = 0
    sequential_draw_count: int | None = None
    sequential_failure_count: int | None = None
    sequential_checkpoints = []
    sequential_prefix_sha256: str | None = None
    accepted_draws = 0
    random_words = 0
    while accepted_draws < profile.max_draws:
        random_words += 1
        word = _splitmix64(
            seed + _GAMMA64 * random_words
        )
        if word >= _UNIFORM_ACCEPT_LIMIT:
            continue
        residue = word % _UNIFORM_DENOMINATOR
        cell_ordinal, rank_residue = divmod(residue, 100)
        atom_ordinal = (
            2 * cell_ordinal + (0 if rank_residue < 99 else 1)
        )
        failure = failure_by_atom[atom_ordinal]
        _pack_boolean_prefix(full_bits, failure, accepted_draws)
        accepted_draws += 1
        failure_count += int(failure)
        if (
            sequential_draw_count is None
            and accepted_draws in profile.checkpoints
        ):
            checkpoint = (
                sequential.build_anytime_bernoulli_checkpoint_v1(
                    accepted_draws,
                    failure_count,
                    profile,
                )
            )
            sequential_checkpoints.append(
                SourceSequentialCheckpointSummaryV1.from_checkpoint(
                    checkpoint
                )
            )
            if (
                checkpoint.interval_width
                <= 2 * profile.target_half_width
            ):
                sequential_draw_count = accepted_draws
                sequential_failure_count = failure_count
                sequential_prefix_sha256 = hashlib.sha256(
                    bytes(full_bits)
                ).hexdigest()
    if sequential_draw_count is None:
        sequential_draw_count = profile.max_draws
        sequential_failure_count = failure_count
        sequential_prefix_sha256 = hashlib.sha256(
            bytes(full_bits)
        ).hexdigest()
    return PairedSourceRowAcquisitionTrialV1(
        source_context_id=context.context_id,
        source_family_id=_source_family_id(
            source_log_id,
            context.context_id,
        ),
        source_row_id=row.observed_row_id,
        seed_id=seed_id,
        fixed_candidate_id=fixed_candidate_id,
        sequential_candidate_id=sequential_candidate_id,
        sequential_profile_id=profile.profile_id,
        fixed_draw_count=profile.max_draws,
        fixed_failure_count=failure_count,
        sequential_draw_count=sequential_draw_count,
        sequential_failure_count=sequential_failure_count,
        sequential_checkpoints=tuple(sequential_checkpoints),
        random_word_count=random_words,
        rejection_count=random_words - profile.max_draws,
        full_transcript_sha256=hashlib.sha256(bytes(full_bits)).hexdigest(),
        sequential_prefix_sha256=sequential_prefix_sha256,
        sequential_certified_width=(
            sequential_checkpoints[-1].interval_width
            <= 2 * profile.target_half_width
        ),
    )


@dataclass(frozen=True, slots=True)
class PairedSourceAcquisitionEvidenceV1:
    portable_source_log_id: str
    portable_skeleton_id: str
    fixed_candidate_id: str
    sequential_candidate_id: str
    trials: tuple[PairedSourceRowAcquisitionTrialV1, ...]
    fixed_arm_draws: int
    sequential_arm_draws: int
    comparison_accounted_draws: int
    physical_common_stream_draws: int
    fixed_arm_exact_row_setups: int
    sequential_arm_exact_row_setups: int
    checkpoint_evaluations: int
    exact_likelihood_comparisons: int
    log_search_evaluations: int
    source_context_count: int
    source_root_row_count: int
    source_scoring_proxy_id: str = SOURCE_SCORING_PROXY_ID
    source_scoring_proxy_rule: str = SOURCE_SCORING_PROXY_RULE
    source_proxy_ranking_only: bool = True
    source_scoring_proxy_may_certify: bool = False
    target_draws: int = 0
    target_rows: int = 0
    target_labels: int = 0
    source_probability_values_used_for_score: bool = False
    paired_stream_replayed_but_arm_costs_charged_separately: bool = True
    full_multinomial_row_reconstruction_compared: bool = False
    end_to_end_planning_work_compared: bool = False
    unconditional_iid_claimed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.portable_source_log_id, "paired evidence source log"),
            (self.portable_skeleton_id, "paired evidence skeleton"),
            (self.fixed_candidate_id, "paired evidence fixed candidate"),
            (
                self.sequential_candidate_id,
                "paired evidence sequential candidate",
            ),
        ):
            _cid(value, field)
        if (
            type(self.trials) is not tuple
            or not self.trials
            or any(
                type(item) is not PairedSourceRowAcquisitionTrialV1
                for item in self.trials
            )
            or tuple(
                sorted(self.trials, key=lambda item: item.trial_id)
            )
            != self.trials
            or len({item.source_row_id for item in self.trials})
            != len(self.trials)
            or self.fixed_arm_draws
            != sum(item.fixed_draw_count for item in self.trials)
            or self.sequential_arm_draws
            != sum(item.sequential_draw_count for item in self.trials)
            or self.comparison_accounted_draws
            != self.fixed_arm_draws + self.sequential_arm_draws
            or self.physical_common_stream_draws != self.fixed_arm_draws
            or self.fixed_arm_exact_row_setups != len(self.trials)
            or self.sequential_arm_exact_row_setups != len(self.trials)
            or self.checkpoint_evaluations
            != sum(len(item.sequential_checkpoints) for item in self.trials)
            or self.exact_likelihood_comparisons
            != sum(
                checkpoint.exact_likelihood_comparisons
                for item in self.trials
                for checkpoint in item.sequential_checkpoints
            )
            or self.log_search_evaluations
            != sum(
                checkpoint.log_search_evaluations
                for item in self.trials
                for checkpoint in item.sequential_checkpoints
            )
            or self.source_context_count
            != len({item.source_context_id for item in self.trials})
            or self.source_root_row_count != len(self.trials)
            or self.source_scoring_proxy_id != SOURCE_SCORING_PROXY_ID
            or self.source_scoring_proxy_rule != SOURCE_SCORING_PROXY_RULE
            or self.source_proxy_ranking_only is not True
            or self.source_scoring_proxy_may_certify is not False
            or any(
                item.source_scoring_proxy_id
                != self.source_scoring_proxy_id
                or item.source_scoring_proxy_rule
                != self.source_scoring_proxy_rule
                or item.source_scoring_proxy_may_certify
                for item in self.trials
            )
            or any(
                value != 0
                for value in (
                    self.target_draws,
                    self.target_rows,
                    self.target_labels,
                )
            )
            or self.source_probability_values_used_for_score is not False
            or self.paired_stream_replayed_but_arm_costs_charged_separately
            is not True
            or self.full_multinomial_row_reconstruction_compared is not False
            or self.end_to_end_planning_work_compared is not False
            or self.unconditional_iid_claimed is not False
        ):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "paired source evidence counters or claim boundary changed"
            )

    @property
    def source_draw_reduction(self) -> Fraction:
        return 1 - Fraction(
            self.sequential_arm_draws,
            self.fixed_arm_draws,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v0066_graph_paired_source_acquisition_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "portable_source_log_id": self.portable_source_log_id,
            "portable_skeleton_id": self.portable_skeleton_id,
            "fixed_candidate_id": self.fixed_candidate_id,
            "sequential_candidate_id": self.sequential_candidate_id,
            "trial_ids": [item.trial_id for item in self.trials],
            "fixed_arm_draws": self.fixed_arm_draws,
            "sequential_arm_draws": self.sequential_arm_draws,
            "comparison_accounted_draws": (
                self.comparison_accounted_draws
            ),
            "physical_common_stream_draws": (
                self.physical_common_stream_draws
            ),
            "fixed_arm_exact_row_setups": (
                self.fixed_arm_exact_row_setups
            ),
            "sequential_arm_exact_row_setups": (
                self.sequential_arm_exact_row_setups
            ),
            "checkpoint_evaluations": self.checkpoint_evaluations,
            "exact_likelihood_comparisons": (
                self.exact_likelihood_comparisons
            ),
            "log_search_evaluations": self.log_search_evaluations,
            "source_context_count": self.source_context_count,
            "source_root_row_count": self.source_root_row_count,
            "source_draw_reduction": _fdoc(self.source_draw_reduction),
            "source_scoring_proxy_id": self.source_scoring_proxy_id,
            "source_scoring_proxy_rule": self.source_scoring_proxy_rule,
            "source_proxy_ranking_only": True,
            "source_scoring_proxy_may_certify": False,
            "target_draws": 0,
            "target_rows": 0,
            "target_labels": 0,
            "source_probability_values_used_for_score": False,
            "paired_stream_replayed_but_arm_costs_charged_separately": True,
            "source_obligation_semantics": (
                "postmerge_failure_indicator_per_registered_root_row"
            ),
            "full_multinomial_row_reconstruction_compared": False,
            "end_to_end_planning_work_compared": False,
            "source_prng_semantics": SOURCE_PRNG_SEMANTICS,
            "source_claim_scope": SOURCE_CLAIM_SCOPE,
            "unconditional_iid_claimed": False,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("source_evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "trials": [item.to_document() for item in self.trials],
            "evidence_id": self.evidence_id,
        }


def _acquire_paired_source_evidence(
    source_log: AnonymousRelationalObservationLogV1,
    skeleton: PortableRelationalSkeletonV1,
    registry: meta.ProposalCandidateRegistryV1,
) -> PairedSourceAcquisitionEvidenceV1:
    if (
        type(source_log) is not AnonymousRelationalObservationLogV1
        or type(skeleton) is not PortableRelationalSkeletonV1
        or type(registry) is not meta.ProposalCandidateRegistryV1
    ):
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "paired source acquisition rejects runtime substitutions"
        )
    by_key = {item.candidate_key: item for item in registry.candidates}
    fixed = by_key[
        GraphAcquisitionOperatorKind.FIXED_FULL_ROW_HOEFFDING.value
    ]
    adaptive = by_key[
        GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER.value
    ]
    source_log_id = source_log.observation_log_id
    trials = tuple(
        sorted(
            (
                _run_paired_source_row_trial(
                    row,
                    source_log_id,
                    fixed.candidate_id,
                    adaptive.candidate_id,
                )
                for row in _source_root_rows(source_log)
            ),
            key=lambda item: item.trial_id,
        )
    )
    return PairedSourceAcquisitionEvidenceV1(
        portable_source_log_id=source_log_id,
        portable_skeleton_id=skeleton.skeleton_id,
        fixed_candidate_id=fixed.candidate_id,
        sequential_candidate_id=adaptive.candidate_id,
        trials=trials,
        fixed_arm_draws=sum(item.fixed_draw_count for item in trials),
        sequential_arm_draws=sum(
            item.sequential_draw_count for item in trials
        ),
        comparison_accounted_draws=sum(
            item.fixed_draw_count + item.sequential_draw_count
            for item in trials
        ),
        physical_common_stream_draws=sum(
            item.fixed_draw_count for item in trials
        ),
        fixed_arm_exact_row_setups=len(trials),
        sequential_arm_exact_row_setups=len(trials),
        checkpoint_evaluations=sum(
            len(item.sequential_checkpoints) for item in trials
        ),
        exact_likelihood_comparisons=sum(
            checkpoint.exact_likelihood_comparisons
            for item in trials
            for checkpoint in item.sequential_checkpoints
        ),
        log_search_evaluations=sum(
            checkpoint.log_search_evaluations
            for item in trials
            for checkpoint in item.sequential_checkpoints
        ),
        source_context_count=len(
            {item.source_context_id for item in trials}
        ),
        source_root_row_count=len(trials),
    )


def _target_adapter_id(
    source_log: AnonymousRelationalObservationLogV1,
    skeleton: PortableRelationalSkeletonV1,
    registry: meta.ProposalCandidateRegistryV1,
) -> str:
    return _content_id(
        "target_adapter",
        {
            "schema": "acfqp.v0066_graph_target_acquisition_adapter.v1",
            "schema_version": SCHEMA_VERSION,
            "source_log_id": source_log.observation_log_id,
            "skeleton_id": skeleton.skeleton_id,
            "candidate_registry_id": registry.registry_id,
            "target_graph_profile": target_graph.PROFILE_KEY,
            "target_kernel_access": 0,
        },
    )


def _target_identity_chain(
    context: target_graph.VariableOrderGraphContextV1,
    source_log: AnonymousRelationalObservationLogV1,
    skeleton: PortableRelationalSkeletonV1,
    registry: meta.ProposalCandidateRegistryV1,
) -> tuple[str, str, tuple[str, ...]]:
    if (
        type(context) is not target_graph.VariableOrderGraphContextV1
        or context not in target_graph.registered_variable_order_contexts_v1()
    ):
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "target identity chain requires a registered V0-066 context"
        )
    # This frozen V0-066 authority depends only on context, horizon, risk,
    # reward semantics, and replica index.  It does not access the kernel.
    query_id = target_graph._registered_query_id(context, 1)
    epoch_id = _content_id(
        "build_epoch",
        {
            "schema": (
                "acfqp.v0066_graph_preacquisition_build_epoch.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "target_context_id": context.context_id,
            "sampling_context_id": context.sampling_context_id,
            "query_id": query_id,
            "source_log_id": source_log.observation_log_id,
            "skeleton_id": skeleton.skeleton_id,
            "candidate_registry_id": registry.registry_id,
            "stage": "BEFORE_TARGET_DYNAMICS_ACQUISITION",
        },
    )
    frontier_id = _content_id(
        "frontier",
        {
            "schema": (
                "acfqp.v0066_graph_preacquisition_frontier.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "target_context_id": context.context_id,
            "sampling_context_id": context.sampling_context_id,
            "query_id": query_id,
            "build_epoch_id": epoch_id,
            "remaining_horizon": target_graph.HORIZON,
            "frontier_stage": "ROOT_PROOF_OBLIGATIONS_UNMATERIALIZED",
            "target_row_ids": [],
            "target_outcome_ids": [],
        },
    )
    observations = tuple(
        sorted(
            _content_id(
                "structural_observation",
                {
                    "schema": (
                        "acfqp.v0066_graph_target_structural_observation.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "observation_kind": kind,
                    "target_context_id": context.context_id,
                    "bound_id": bound_id,
                    "target_dynamics_rows": 0,
                    "target_labels": 0,
                },
            )
            for kind, bound_id in (
                ("STRUCTURAL_CONTEXT", context.context_id),
                ("QUERY", query_id),
                ("PREACQUISITION_FRONTIER", frontier_id),
            )
        )
    )
    return query_id, epoch_id, (frontier_id, *observations)


@dataclass(frozen=True, slots=True)
class GraphTargetAcquisitionProposalV1:
    context_key: str
    context_id: str
    sampling_context_id: str
    query_id: str
    build_epoch_id: str
    frontier_snapshot_id: str
    applicability: meta.TargetProposalApplicabilityV1
    request: meta.TargetProposalRequestV1
    proposal: meta.ProposalOnlyRankingV1
    expected_selected_candidate_id: str
    target_kernel_calls: int = 0
    target_dynamics_rows: int = 0
    target_outcome_labels: int = 0
    target_reward_labels: int = 0
    target_certificate_labels: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.context_key) is not str
            or not self.context_key
        ):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "target proposal context key is invalid"
            )
        for value, field in (
            (self.context_id, "target proposal context"),
            (self.sampling_context_id, "target proposal sampling context"),
            (self.query_id, "target proposal query"),
            (self.build_epoch_id, "target proposal epoch"),
            (self.frontier_snapshot_id, "target proposal frontier"),
            (
                self.expected_selected_candidate_id,
                "target expected candidate",
            ),
        ):
            _cid(value, field)
        if (
            type(self.applicability)
            is not meta.TargetProposalApplicabilityV1
            or type(self.request) is not meta.TargetProposalRequestV1
            or type(self.proposal) is not meta.ProposalOnlyRankingV1
            or self.applicability.target_context_id != self.context_id
            or self.applicability.query_id != self.query_id
            or self.applicability.build_epoch_id != self.build_epoch_id
            or self.applicability.frontier_snapshot_id
            != self.frontier_snapshot_id
            or self.request.target_applicability_id
            != self.applicability.applicability_id
            or self.proposal.status
            is not meta.ProposalStatus.PROPOSAL_READY
            or self.proposal.selected_candidate_ids
            != (self.expected_selected_candidate_id,)
            or self.proposal.may_certify is not False
            or self.proposal.target_local_acquisition_required is not True
            or self.proposal.target_local_certificate_required is not True
            or any(
                value != 0
                for value in (
                    self.target_kernel_calls,
                    self.target_dynamics_rows,
                    self.target_outcome_labels,
                    self.target_reward_labels,
                    self.target_certificate_labels,
                )
            )
        ):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "target proposal identity, authority, or isolation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v0066_graph_target_acquisition_proposal.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_key": self.context_key,
            "context_id": self.context_id,
            "sampling_context_id": self.sampling_context_id,
            "query_id": self.query_id,
            "build_epoch_id": self.build_epoch_id,
            "frontier_snapshot_id": self.frontier_snapshot_id,
            "applicability_id": self.applicability.applicability_id,
            "request_id": self.request.request_id,
            "proposal_id": self.proposal.proposal_id,
            "expected_selected_candidate_id": (
                self.expected_selected_candidate_id
            ),
            "target_kernel_calls": 0,
            "target_dynamics_rows": 0,
            "target_outcome_labels": 0,
            "target_reward_labels": 0,
            "target_certificate_labels": 0,
            "proposal_only": True,
        }

    @property
    def target_proposal_id(self) -> str:
        return _content_id("target_proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "applicability": self.applicability.to_document(),
            "request": self.request.to_document(),
            "proposal": self.proposal.to_document(),
            "target_proposal_id": self.target_proposal_id,
        }


def build_graph_target_acquisition_proposals_v1(
    source_log: AnonymousRelationalObservationLogV1,
    skeleton: PortableRelationalSkeletonV1,
    registry: meta.ProposalCandidateRegistryV1,
    envelope: meta.ProposalTransferEnvelopeV1,
    prior: meta.SourceConsensusMetaPriorV1,
) -> tuple[GraphTargetAcquisitionProposalV1, ...]:
    exact_types = (
        (source_log, AnonymousRelationalObservationLogV1),
        (skeleton, PortableRelationalSkeletonV1),
        (registry, meta.ProposalCandidateRegistryV1),
        (envelope, meta.ProposalTransferEnvelopeV1),
        (prior, meta.SourceConsensusMetaPriorV1),
    )
    if any(type(value) is not expected for value, expected in exact_types):
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "target proposal builder rejects runtime substitutions"
        )
    sequential_candidate = next(
        item
        for item in registry.candidates
        if item.candidate_key
        == GraphAcquisitionOperatorKind.SEQUENTIAL_VARIANCE_ADAPTIVE_PROOF_FRONTIER.value
    )
    available_capabilities = tuple(
        sorted(
            {
                capability_id
                for candidate in registry.candidates
                for capability_id in candidate.required_capability_ids
            }
        )
    )
    target_family_id = (
        target_graph.registered_variable_order_family_v1().family_id
    )
    target_adapter_id = _target_adapter_id(
        source_log,
        skeleton,
        registry,
    )
    rows = []
    for context in target_graph.registered_variable_order_contexts_v1():
        query_id, epoch_id, identity_rows = _target_identity_chain(
            context,
            source_log,
            skeleton,
            registry,
        )
        frontier_id = identity_rows[0]
        structural_observation_ids = tuple(sorted(identity_rows[1:]))
        applicability = meta.TargetProposalApplicabilityV1(
            target_context_id=context.context_id,
            target_family_id=target_family_id,
            target_adapter_id=target_adapter_id,
            role_schema_id=source_log.role_schema.role_schema_id,
            candidate_registry_id=registry.registry_id,
            query_id=query_id,
            build_epoch_id=epoch_id,
            frontier_snapshot_id=frontier_id,
            structural_observation_ids=structural_observation_ids,
            available_capability_ids=available_capabilities,
            online_accounting=meta.OnlineTargetContextAccountingV1(
                len(structural_observation_ids)
            ),
        )
        request = meta.TargetProposalRequestV1(
            prior_id=prior.prior_id,
            target_applicability_id=applicability.applicability_id,
            allowed_kinds=(meta.ProposalCandidateKind.SUPPORT,),
            maximum_proposals=1,
        )
        proposal = meta.rank_target_proposals_v1(
            registry,
            envelope,
            prior,
            applicability,
            request,
        )
        rows.append(
            GraphTargetAcquisitionProposalV1(
                context_key=context.context_key,
                context_id=context.context_id,
                sampling_context_id=context.sampling_context_id,
                query_id=query_id,
                build_epoch_id=epoch_id,
                frontier_snapshot_id=frontier_id,
                applicability=applicability,
                request=request,
                proposal=proposal,
                expected_selected_candidate_id=(
                    sequential_candidate.candidate_id
                ),
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class V0066GraphAcquisitionMetaPriorCampaignV1:
    source_log: AnonymousRelationalObservationLogV1
    source_skeleton: PortableRelationalSkeletonV1
    operator_semantics: tuple[GraphAcquisitionOperatorSemanticsV1, ...]
    candidate_registry: meta.ProposalCandidateRegistryV1
    transfer_envelope: meta.ProposalTransferEnvelopeV1
    source_evidence: PairedSourceAcquisitionEvidenceV1
    source_observation_log: meta.SourceProposalObservationLogV1
    source_prior: meta.SourceConsensusMetaPriorV1
    target_proposals: tuple[GraphTargetAcquisitionProposalV1, ...]
    status: str = SUCCESS_STATUS
    source_only_nonneutral_proxy_ranking: bool = True
    end_to_end_operator_ranking_claimed: bool = False
    target_sample_efficiency_claimed: bool = False
    broad_sample_efficiency_claimed: bool = False
    plan_certificate_claimed: bool = False
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        exact_types = (
            (self.source_log, AnonymousRelationalObservationLogV1),
            (self.source_skeleton, PortableRelationalSkeletonV1),
            (self.candidate_registry, meta.ProposalCandidateRegistryV1),
            (self.transfer_envelope, meta.ProposalTransferEnvelopeV1),
            (
                self.source_evidence,
                PairedSourceAcquisitionEvidenceV1,
            ),
            (
                self.source_observation_log,
                meta.SourceProposalObservationLogV1,
            ),
            (self.source_prior, meta.SourceConsensusMetaPriorV1),
        )
        if any(type(value) is not expected for value, expected in exact_types):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "campaign runtime authority changed"
            )
        if (
            type(self.operator_semantics) is not tuple
            or self.operator_semantics
            != registered_graph_acquisition_operator_semantics_v1()
            or type(self.target_proposals) is not tuple
            or len(self.target_proposals) != 3
            or any(
                type(item) is not GraphTargetAcquisitionProposalV1
                for item in self.target_proposals
            )
            or self.source_skeleton.source_observation_log_id
            != self.source_log.observation_log_id
            or self.transfer_envelope.candidate_registry_id
            != self.candidate_registry.registry_id
            or self.source_evidence.portable_source_log_id
            != self.source_log.observation_log_id
            or self.source_observation_log.source_log_id
            != self.source_prior.source_log_id
            or self.source_prior.ranked_candidate_ids[0]
            != self.source_evidence.sequential_candidate_id
            or self.source_evidence.sequential_arm_draws
            >= self.source_evidence.fixed_arm_draws
            or self.status != SUCCESS_STATUS
            or self.source_only_nonneutral_proxy_ranking is not True
            or self.end_to_end_operator_ranking_claimed is not False
            or self.target_sample_efficiency_claimed is not False
            or self.broad_sample_efficiency_claimed is not False
            or self.plan_certificate_claimed is not False
            or self.official_execution_allowed is not False
            or any(
                item.target_dynamics_rows != 0
                or item.target_outcome_labels != 0
                or item.proposal.may_certify
                for item in self.target_proposals
            )
        ):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "campaign identity, ordering, isolation, or claim lock changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v0066_graph_acquisition_metaprior_campaign.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_log_id": self.source_log.observation_log_id,
            "source_skeleton_id": self.source_skeleton.skeleton_id,
            "operator_semantics_ids": [
                item.semantics_id for item in self.operator_semantics
            ],
            "candidate_registry_id": self.candidate_registry.registry_id,
            "transfer_envelope_id": self.transfer_envelope.envelope_id,
            "source_evidence_id": self.source_evidence.evidence_id,
            "source_observation_log_id": (
                self.source_observation_log.source_log_id
            ),
            "source_prior_id": self.source_prior.prior_id,
            "target_proposal_ids": [
                item.target_proposal_id for item in self.target_proposals
            ],
            "status": self.status,
            "source_only_nonneutral_proxy_ranking": (
                self.source_only_nonneutral_proxy_ranking
            ),
            "end_to_end_operator_ranking_claimed": False,
            "target_sample_efficiency_claimed": False,
            "broad_sample_efficiency_claimed": False,
            "plan_certificate_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def campaign_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "operator_semantics": [
                item.to_document() for item in self.operator_semantics
            ],
            "candidate_registry": self.candidate_registry.to_document(),
            "transfer_envelope": self.transfer_envelope.to_document(),
            "source_evidence": self.source_evidence.to_document(),
            "source_observation_log": (
                self.source_observation_log.to_document()
            ),
            "source_prior": self.source_prior.to_document(),
            "target_proposals": [
                item.to_document() for item in self.target_proposals
            ],
            "campaign_id": self.campaign_id,
        }


def _build_campaign_v1() -> V0066GraphAcquisitionMetaPriorCampaignV1:
    source_log = target_graph.build_portable_graph_source_log_v1()
    source_skeleton = target_graph.portable_graph_source_skeleton_v1()
    # The frozen source-skeleton constructor performs its own full replay.
    # Avoid a second identical synthesis verification in the producer.
    semantics_candidates = _operator_candidates(
        source_log.role_schema.role_schema_id
    )
    semantics = tuple(item[0] for item in semantics_candidates)
    registry = meta.build_proposal_candidate_registry_v1(
        source_log.role_schema.role_schema_id,
        (item[1] for item in semantics_candidates),
    )
    source_context_ids = tuple(
        sorted(
            {
                item.state.structural_context_id
                for item in _source_root_rows(source_log)
            }
        )
    )
    source_family_ids = tuple(
        sorted(
            _source_family_id(
                source_log.observation_log_id,
                context_id,
            )
            for context_id in source_context_ids
        )
    )
    target_adapter_id = _target_adapter_id(
        source_log,
        source_skeleton,
        registry,
    )
    envelope = meta.ProposalTransferEnvelopeV1(
        candidate_registry_id=registry.registry_id,
        role_schema_id=source_log.role_schema.role_schema_id,
        source_family_ids=source_family_ids,
        allowed_target_family_ids=(
            target_graph.registered_variable_order_family_v1().family_id,
        ),
        allowed_target_adapter_ids=(target_adapter_id,),
    )
    evidence = _acquire_paired_source_evidence(
        source_log,
        source_skeleton,
        registry,
    )
    by_context: dict[
        str, tuple[PairedSourceRowAcquisitionTrialV1, ...]
    ] = {
        context_id: tuple(
            item
            for item in evidence.trials
            if item.source_context_id == context_id
        )
        for context_id in source_context_ids
    }
    generic_observations = []
    for context_id in source_context_ids:
        trials = by_context[context_id]
        fixed_draws = sum(item.fixed_draw_count for item in trials)
        sequential_draws = sum(
            item.sequential_draw_count for item in trials
        )
        source_family_id = _source_family_id(
            source_log.observation_log_id,
            context_id,
        )
        generic_observations.extend(
            (
                meta.SourceProposalObservationV1(
                    source_context_id=context_id,
                    source_family_id=source_family_id,
                    candidate_id=evidence.fixed_candidate_id,
                    proposal_score=Fraction(0),
                    logged_observation_count=len(trials),
                    generative_draw_count=fixed_draws,
                    environment_interaction_count=0,
                    exact_kernel_call_count=len(trials),
                    source_scoring_proxy_id=SOURCE_SCORING_PROXY_ID,
                    source_scoring_proxy_rule=SOURCE_SCORING_PROXY_RULE,
                ),
                meta.SourceProposalObservationV1(
                    source_context_id=context_id,
                    source_family_id=source_family_id,
                    candidate_id=evidence.sequential_candidate_id,
                    proposal_score=1
                    - Fraction(sequential_draws, fixed_draws),
                    logged_observation_count=len(trials),
                    generative_draw_count=sequential_draws,
                    environment_interaction_count=0,
                    exact_kernel_call_count=len(trials),
                    source_scoring_proxy_id=SOURCE_SCORING_PROXY_ID,
                    source_scoring_proxy_rule=SOURCE_SCORING_PROXY_RULE,
                ),
            )
        )
    source_observation_log = (
        meta.build_source_proposal_observation_log_v1(
            registry,
            envelope,
            generic_observations,
        )
    )
    source_prior = meta.build_source_consensus_metaprior_v1(
        registry,
        envelope,
        source_observation_log,
    )
    target_proposals = build_graph_target_acquisition_proposals_v1(
        source_log,
        source_skeleton,
        registry,
        envelope,
        source_prior,
    )
    return V0066GraphAcquisitionMetaPriorCampaignV1(
        source_log=source_log,
        source_skeleton=source_skeleton,
        operator_semantics=semantics,
        candidate_registry=registry,
        transfer_envelope=envelope,
        source_evidence=evidence,
        source_observation_log=source_observation_log,
        source_prior=source_prior,
        target_proposals=target_proposals,
    )


@functools.lru_cache(maxsize=1)
def run_v0066_graph_acquisition_metaprior_v1(
) -> V0066GraphAcquisitionMetaPriorCampaignV1:
    return _build_campaign_v1()


@dataclass(frozen=True, slots=True)
class V0066GraphAcquisitionMetaPriorVerificationV1:
    campaign_id: str
    source_evidence_id: str
    source_prior_id: str
    verified_target_proposal_ids: tuple[str, ...]
    paired_source_streams_replayed: int
    source_draw_accounting_reconciled: bool = True
    nonneutral_source_proxy_ordering_replayed: bool = True
    source_proxy_noncertification_verified: bool = True
    zero_target_dynamics_verified: bool = True
    proposal_only_authority_verified: bool = True
    certificate_verified: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.campaign_id, "verification campaign"),
            (self.source_evidence_id, "verification source evidence"),
            (self.source_prior_id, "verification source prior"),
        ):
            _cid(value, field)
        _ids(
            self.verified_target_proposal_ids,
            "verified target proposals",
        )
        if (
            self.paired_source_streams_replayed != 40
            or self.source_draw_accounting_reconciled is not True
            or self.nonneutral_source_proxy_ordering_replayed is not True
            or self.source_proxy_noncertification_verified is not True
            or self.zero_target_dynamics_verified is not True
            or self.proposal_only_authority_verified is not True
            or self.certificate_verified is not False
        ):
            raise V0066GraphAcquisitionMetaPriorInvariantViolation(
                "graph acquisition verification claim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v0066_graph_acquisition_metaprior_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "source_evidence_id": self.source_evidence_id,
            "source_prior_id": self.source_prior_id,
            "verified_target_proposal_ids": list(
                self.verified_target_proposal_ids
            ),
            "paired_source_streams_replayed": (
                self.paired_source_streams_replayed
            ),
            "source_draw_accounting_reconciled": True,
            "nonneutral_source_proxy_ordering_replayed": True,
            "source_proxy_noncertification_verified": True,
            "zero_target_dynamics_verified": True,
            "proposal_only_authority_verified": True,
            "certificate_verified": False,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v0066_graph_acquisition_metaprior_v1(
    claimed: V0066GraphAcquisitionMetaPriorCampaignV1,
) -> V0066GraphAcquisitionMetaPriorVerificationV1:
    if type(claimed) is not V0066GraphAcquisitionMetaPriorCampaignV1:
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "campaign verifier rejects runtime substitutions"
        )
    claimed.__post_init__()
    verify_portable_relational_skeleton_v1(
        claimed.source_log,
        claimed.source_skeleton,
    )
    # Rebuilding the full campaign below replays every paired source stream
    # once.  A separate evidence replay here would double evaluation work.
    replayed = _build_campaign_v1()
    if replayed.to_document() != claimed.to_document():
        raise V0066GraphAcquisitionMetaPriorInvariantViolation(
            "graph acquisition meta-prior campaign replay mismatch"
        )
    for target in claimed.target_proposals:
        meta.verify_proposal_only_metaprior_v1(
            claimed.candidate_registry,
            claimed.transfer_envelope,
            claimed.source_observation_log,
            claimed.source_prior,
            target.applicability,
            target.request,
            target.proposal,
        )
    return V0066GraphAcquisitionMetaPriorVerificationV1(
        campaign_id=claimed.campaign_id,
        source_evidence_id=claimed.source_evidence.evidence_id,
        source_prior_id=claimed.source_prior.prior_id,
        verified_target_proposal_ids=tuple(
            sorted(
                item.target_proposal_id
                for item in claimed.target_proposals
            )
        ),
        paired_source_streams_replayed=len(
            claimed.source_evidence.trials
        ),
    )


__all__ = [
    "CONTRACT_VERSION",
    "PROFILE_KEY",
    "SOURCE_CLAIM_SCOPE",
    "SOURCE_PRNG_SEMANTICS",
    "SOURCE_SCORING_PROXY_ID",
    "SOURCE_SCORING_PROXY_RULE",
    "GraphAcquisitionOperatorKind",
    "GraphAcquisitionOperatorSemanticsV1",
    "GraphTargetAcquisitionProposalV1",
    "PairedSourceAcquisitionEvidenceV1",
    "PairedSourceRowAcquisitionTrialV1",
    "SourceSequentialCheckpointSummaryV1",
    "V0066GraphAcquisitionMetaPriorCampaignV1",
    "V0066GraphAcquisitionMetaPriorInvariantViolation",
    "V0066GraphAcquisitionMetaPriorVerificationV1",
    "build_graph_target_acquisition_proposals_v1",
    "registered_graph_acquisition_operator_semantics_v1",
    "run_v0066_graph_acquisition_metaprior_v1",
    "verify_v0066_graph_acquisition_metaprior_v1",
]
