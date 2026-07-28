"""Typed cold DIRECT_FIXED authority for the V0-067 graph Gate.

This is intentionally not the sequential direct authority.  It constructs
the complete registered H=2 ground state-action closure, then generates
exactly 131,072 paired-stream target draws for every row directly from draw
zero.  It never slices a V0-066 packed row and it does not relax
``DirectPrefixRowV1``'s strict ``draw_count < 131072`` guard.

The operational result contains raw target transcripts, an exact-rational
uniform-beta Ville confidence sequence evaluated once at the fixed terminal
sample size, and a ground robust Bellman audit.  The estimator is identical
to DIRECT_SEQUENTIAL; only the acquisition schedule disables early stopping.
Exact kernel probabilities are not read by the operational runner.  The
standalone verifier replays raw streams, rebuilds the robust audit, and only
then evaluates the frozen policy against the exact kernel in a separately
identified evaluation lane.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import functools
import hashlib
import math
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
import acfqp.sequential_bernoulli_acquisition_v1 as sequential
import acfqp.variable_graph_direct_sequential_v1 as direct_seq
import acfqp.variable_order_graph_rapm_v1 as graph


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.31.0"
PROFILE_KEY = "v0067_cold_direct_ground_fixed_graph_v0"
FIXED_DRAWS_PER_ROW = 131_072
TARGET_HALF_WIDTH = Fraction(1, 140)
PER_OBLIGATION_TAIL_UPPER = Fraction(1, 250_000)
POSITIVE_FAMILY_OBLIGATION_COUNT = 198
PROVEN_POSITIVE_FAMILY_TAIL_UPPER = Fraction(198, 250_000)
REGISTERED_GATE_TAIL_BUDGET = Fraction(287, 250_000)

DOMAIN_TAGS = {
    "profile": "acfqp:v0067-direct-fixed-profile:v1",
    "stream": "acfqp:v0067-paired-direct-fixed-stream:v1",
    "row": "acfqp:v0067-direct-fixed-row:v1",
    "audit": "acfqp:v0067-direct-fixed-audit:v1",
    "result": "acfqp:v0067-direct-fixed-result:v1",
    "evaluation": "acfqp:v0067-direct-fixed-evaluation:v1",
    "verification": "acfqp:v0067-direct-fixed-verification:v1",
}


class VariableGraphDirectFixedInvariantViolation(ValueError):
    """A fixed row, calibration, robust audit, or replay invariant failed."""


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    raw_suffix: bytes = b"",
) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role].encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise VariableGraphDirectFixedInvariantViolation(str(error)) from error
    material = domain + b"\x00" + encoded
    if raw_suffix:
        material += b"\x00" + raw_suffix
    return hashlib.sha256(material).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise VariableGraphDirectFixedInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def paired_stream_identity_v1(
    context_id: str,
    catalogue_id: str,
    action: tuple[int, int, int],
    paired_v0066_seed: int,
) -> str:
    """Content identity shared with the matching direct-sequential row."""

    _cid(context_id, "paired stream context")
    _cid(catalogue_id, "paired stream catalogue")
    if (
        type(action) is not tuple
        or len(action) != 3
        or any(type(item) is not int for item in action)
        or type(paired_v0066_seed) is not int
        or not 0 <= paired_v0066_seed < (1 << 64)
    ):
        raise VariableGraphDirectFixedInvariantViolation(
            "paired stream identity input is invalid"
        )
    return _content_id(
        "stream",
        {
            "schema": "acfqp.v0067_paired_direct_stream.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "catalogue_id": catalogue_id,
            "action": list(action),
            "paired_v0066_seed": paired_v0066_seed,
            "prng_semantics_id": graph.REGISTERED_PRNG_SEMANTICS_ID,
        },
    )


@dataclass(frozen=True, slots=True)
class DirectFixedProfileV1:
    context_id: str
    context_aggregate_obligation_count: int
    family_aggregate_obligation_count: int
    sample_count_per_row: int
    target_half_width: Fraction
    per_obligation_tail_upper: Fraction
    context_tail_upper: Fraction
    proven_family_tail_upper: Fraction
    registered_gate_tail_budget: Fraction
    boundary_grid_bits: int
    complete_h2_closure: bool = True
    fixed_sample_stopping: bool = True
    anytime_valid_estimator: bool = True
    exact_probability_operational_access_forbidden: bool = True

    def __post_init__(self) -> None:
        _cid(self.context_id, "direct-fixed profile context")
        if (
            self.context_aggregate_obligation_count not in (66, 132)
            or self.family_aggregate_obligation_count
            != POSITIVE_FAMILY_OBLIGATION_COUNT
            or self.sample_count_per_row != FIXED_DRAWS_PER_ROW
            or self.target_half_width != TARGET_HALF_WIDTH
            or self.per_obligation_tail_upper
            != PER_OBLIGATION_TAIL_UPPER
            or self.context_tail_upper
            != self.context_aggregate_obligation_count
            * self.per_obligation_tail_upper
            or self.proven_family_tail_upper
            != self.family_aggregate_obligation_count
            * self.per_obligation_tail_upper
            or self.proven_family_tail_upper
            != PROVEN_POSITIVE_FAMILY_TAIL_UPPER
            or self.registered_gate_tail_budget
            != REGISTERED_GATE_TAIL_BUDGET
            or self.proven_family_tail_upper
            > self.registered_gate_tail_budget
            or self.boundary_grid_bits != 24
            or self.complete_h2_closure is not True
            or self.fixed_sample_stopping is not True
            or self.anytime_valid_estimator is not True
            or self.exact_probability_operational_access_forbidden
            is not True
        ):
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed exact-rational calibration changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_fixed_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "context_aggregate_obligation_count": (
                self.context_aggregate_obligation_count
            ),
            "family_aggregate_obligation_count": (
                self.family_aggregate_obligation_count
            ),
            "sample_count_per_row": self.sample_count_per_row,
            "target_half_width": _fdoc(self.target_half_width),
            "per_obligation_tail_upper": _fdoc(
                self.per_obligation_tail_upper
            ),
            "context_tail_upper": _fdoc(self.context_tail_upper),
            "proven_family_tail_upper": _fdoc(
                self.proven_family_tail_upper
            ),
            "registered_gate_tail_budget": _fdoc(
                self.registered_gate_tail_budget
            ),
            "boundary_grid_bits": self.boundary_grid_bits,
            "confidence_method_id": sequential.METHOD_ID,
            "confidence_accounting": (
                "ONE_ALPHA_VILLE_TIME_UNIFORM_NO_CHECKPOINT_ALPHA_SPENDING"
            ),
            "estimator_schedule": (
                "ANYTIME_VALID_ESTIMATOR_EVALUATED_ONLY_AT_FIXED_N"
            ),
            "complete_h2_closure": True,
            "fixed_sample_stopping": True,
            "anytime_valid_estimator": True,
            "exact_probability_operational_access_forbidden": True,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def _profile(
    context: graph.VariableOrderGraphContextV1,
    obligation_count: int,
) -> DirectFixedProfileV1:
    return DirectFixedProfileV1(
        context_id=context.context_id,
        context_aggregate_obligation_count=obligation_count,
        family_aggregate_obligation_count=(
            POSITIVE_FAMILY_OBLIGATION_COUNT
        ),
        sample_count_per_row=FIXED_DRAWS_PER_ROW,
        target_half_width=TARGET_HALF_WIDTH,
        per_obligation_tail_upper=PER_OBLIGATION_TAIL_UPPER,
        context_tail_upper=(
            obligation_count * PER_OBLIGATION_TAIL_UPPER
        ),
        proven_family_tail_upper=PROVEN_POSITIVE_FAMILY_TAIL_UPPER,
        registered_gate_tail_budget=REGISTERED_GATE_TAIL_BUDGET,
        boundary_grid_bits=24,
    )


@dataclass(frozen=True, slots=True)
class DirectFixedRowV1:
    context_id: str
    catalogue: graph.VariableGraphCatalogueV1
    action: tuple[int, int, int]
    atom_descriptors: tuple[graph.ObservedVariableGraphAtomV1, ...]
    draw_count: int
    random_word_count: int
    rejection_count: int
    ordinal_counts: tuple[int, ...]
    packed_ordinals: bytes
    packed_rejection_flags: bytes
    paired_v0066_seed: int
    generated_directly_from_draw_zero: bool = True
    v0066_packed_row_access_count: int = 0
    operational_exact_probability_reads: int = 0

    def __post_init__(self) -> None:
        _cid(self.context_id, "direct-fixed row context")
        atom_count = 2 * (len(self.catalogue.state.ranks) - 2)
        if (
            type(self.catalogue) is not graph.VariableGraphCatalogueV1
            or self.catalogue.context_id != self.context_id
            or self.action not in self.catalogue.actions
            or type(self.atom_descriptors) is not tuple
            or len(self.atom_descriptors) != atom_count
            or any(
                type(item) is not graph.ObservedVariableGraphAtomV1
                for item in self.atom_descriptors
            )
            or tuple(item.ordinal for item in self.atom_descriptors)
            != tuple(range(atom_count))
            or self.draw_count != FIXED_DRAWS_PER_ROW
            or type(self.random_word_count) is not int
            or self.random_word_count < self.draw_count
            or self.rejection_count
            != self.random_word_count - self.draw_count
            or type(self.ordinal_counts) is not tuple
            or len(self.ordinal_counts) != atom_count
            or any(type(item) is not int or item < 0 for item in self.ordinal_counts)
            or sum(self.ordinal_counts) != self.draw_count
            or type(self.packed_ordinals) is not bytes
            or len(self.packed_ordinals)
            != math.ceil(3 * self.draw_count / 8)
            or type(self.packed_rejection_flags) is not bytes
            or len(self.packed_rejection_flags)
            != math.ceil(self.random_word_count / 8)
            or type(self.paired_v0066_seed) is not int
            or not 0 <= self.paired_v0066_seed < (1 << 64)
            or self.generated_directly_from_draw_zero is not True
            or self.v0066_packed_row_access_count != 0
            or self.operational_exact_probability_reads != 0
        ):
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed row shape or authority changed"
            )
        decoded = graph._unpack_three_bit_ordinals(
            self.packed_ordinals,
            self.draw_count,
            atom_count,
        )
        counts = [0] * atom_count
        for ordinal in decoded:
            counts[ordinal] += 1
        flags = graph._unpack_rejection_flags(
            self.packed_rejection_flags,
            self.random_word_count,
        )
        if (
            tuple(counts) != self.ordinal_counts
            or sum(flags) != self.rejection_count
        ):
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed packed transcript failed replay"
            )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_fixed_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "action": list(self.action),
            "atom_descriptors": [
                item.to_document() for item in self.atom_descriptors
            ],
            "draw_count": self.draw_count,
            "random_word_count": self.random_word_count,
            "rejection_count": self.rejection_count,
            "ordinal_counts": list(self.ordinal_counts),
            "packed_ordinals_sha256": hashlib.sha256(
                self.packed_ordinals
            ).hexdigest(),
            "packed_rejection_flags_sha256": hashlib.sha256(
                self.packed_rejection_flags
            ).hexdigest(),
            "paired_v0066_seed": self.paired_v0066_seed,
            "paired_stream_id": self.paired_stream_id,
            "generated_directly_from_draw_zero": True,
            "v0066_packed_row_access_count": 0,
            "operational_exact_probability_reads": 0,
        }

    @property
    def paired_stream_id(self) -> str:
        return paired_stream_identity_v1(
            self.context_id,
            self.catalogue.catalogue_id,
            self.action,
            self.paired_v0066_seed,
        )

    @property
    def row_id(self) -> str:
        return _content_id(
            "row",
            self._identity_payload(),
            self.packed_ordinals
            + b"\x00"
            + self.packed_rejection_flags,
        )

    def to_document(self, *, include_raw: bool = False) -> dict[str, Any]:
        document = {**self._identity_payload(), "row_id": self.row_id}
        if include_raw:
            document["packed_ordinals_hex"] = self.packed_ordinals.hex()
            document["packed_rejection_flags_hex"] = (
                self.packed_rejection_flags.hex()
            )
        return document


@dataclass(slots=True)
class _MutableDirectFixedStream:
    context: graph.VariableOrderGraphContextV1
    catalogue: graph.VariableGraphCatalogueV1
    action: tuple[int, int, int]
    descriptors: tuple[graph.ObservedVariableGraphAtomV1, ...]
    seed: int
    ordinals: list[int]
    rejection_flags: list[bool]
    counts: list[int]
    random_word_index: int = 0

    @classmethod
    def create(
        cls,
        context: graph.VariableOrderGraphContextV1,
        catalogue: graph.VariableGraphCatalogueV1,
        action: tuple[int, int, int],
        descriptors: tuple[graph.ObservedVariableGraphAtomV1, ...],
    ) -> "_MutableDirectFixedStream":
        return cls(
            context=context,
            catalogue=catalogue,
            action=action,
            descriptors=descriptors,
            seed=graph._row_seed(context, catalogue, action),
            ordinals=[],
            rejection_flags=[],
            counts=[0] * (2 * (context.vertex_count - 2)),
        )

    def generate(self) -> None:
        if self.ordinals:
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed stream cannot resume or reuse a prefix"
            )
        gamma = 0x9E3779B97F4A7C15
        while len(self.ordinals) < FIXED_DRAWS_PER_ROW:
            random_uint64 = graph._splitmix64(
                self.seed + gamma * (self.random_word_index + 1)
            )
            self.random_word_index += 1
            mapped = graph.exact_rejection_ordinal_v1(
                len(self.descriptors) // 2,
                random_uint64,
            )
            rejected = mapped is None
            self.rejection_flags.append(rejected)
            if rejected:
                continue
            self.ordinals.append(mapped)
            self.counts[mapped] += 1

    def freeze(self) -> DirectFixedRowV1:
        if len(self.ordinals) != FIXED_DRAWS_PER_ROW:
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed row froze before its registered sample count"
            )
        return DirectFixedRowV1(
            context_id=self.context.context_id,
            catalogue=self.catalogue,
            action=self.action,
            atom_descriptors=self.descriptors,
            draw_count=len(self.ordinals),
            random_word_count=self.random_word_index,
            rejection_count=(
                self.random_word_index - len(self.ordinals)
            ),
            ordinal_counts=tuple(self.counts),
            packed_ordinals=graph._pack_three_bit_ordinals(
                self.ordinals
            ),
            packed_rejection_flags=graph._pack_rejection_flags(
                self.rejection_flags
            ),
            paired_v0066_seed=self.seed,
        )


def verify_direct_fixed_row_v1(
    context: graph.VariableOrderGraphContextV1,
    row: DirectFixedRowV1,
) -> bool:
    if (
        type(context) is not graph.VariableOrderGraphContextV1
        or type(row) is not DirectFixedRowV1
        or row.context_id != context.context_id
    ):
        raise VariableGraphDirectFixedInvariantViolation(
            "direct-fixed row replay binding is invalid"
        )
    stream = _MutableDirectFixedStream.create(
        context,
        row.catalogue,
        row.action,
        direct_seq._descriptors(
            context,
            row.catalogue,
            row.action,
        ),
    )
    stream.generate()
    expected = stream.freeze()
    if (
        expected.row_id != row.row_id
        or expected.packed_ordinals != row.packed_ordinals
        or expected.packed_rejection_flags != row.packed_rejection_flags
    ):
        raise VariableGraphDirectFixedInvariantViolation(
            "direct-fixed raw row failed paired-seed replay"
        )
    return True


def _fixed_intervals(
    row: DirectFixedRowV1,
    profile: DirectFixedProfileV1,
) -> tuple[graph.StatisticalDestinationIntervalV1, ...]:
    counts: dict[tuple[Any, ...], int] = defaultdict(int)
    ordinals: dict[tuple[Any, ...], set[int]] = defaultdict(set)
    for atom in row.atom_descriptors:
        destination = direct_seq._destination(row, atom)
        counts[destination] += row.ordinal_counts[atom.ordinal]
        ordinals[destination].add(atom.ordinal)
    intervals: list[graph.StatisticalDestinationIntervalV1] = []
    for destination in sorted(counts, key=repr):
        if len(ordinals[destination]) == len(row.atom_descriptors):
            lower = upper = Fraction(1)
        else:
            checkpoint = sequential.build_anytime_bernoulli_checkpoint_v1(
                row.draw_count,
                counts[destination],
                sequential.SequentialBernoulliProfileV1(
                    profile.per_obligation_tail_upper,
                    profile.target_half_width,
                    (profile.sample_count_per_row,),
                    profile.boundary_grid_bits,
                ),
            )
            lower = checkpoint.lower_probability
            upper = checkpoint.upper_probability
        intervals.append(
            graph.StatisticalDestinationIntervalV1(
                destination,
                lower,
                upper,
            )
        )
    return tuple(intervals)


class DirectFixedAuditOutcome(str, Enum):
    CONDITIONALLY_CERTIFIED = "CONDITIONALLY_CERTIFIED_FIXED_N_VILLE_CS"
    FAILED_ROBUST_GROUND_AUDIT = "FAILED_ROBUST_GROUND_AUDIT"


@dataclass(frozen=True, slots=True)
class DirectFixedAuditV1:
    context_id: str
    profile_id: str
    row_ids: tuple[str, ...]
    ground_row_count: int
    target_generative_draws: int
    outcome: DirectFixedAuditOutcome
    root_failure_upper: Fraction
    root_reward_lower: Fraction
    normalized_regret_upper: Fraction
    policy: tuple[direct_seq.DirectPolicyBoundV1, ...]
    aggregate_obligations_evaluated: int
    exact_probability_reads: int = 0

    def __post_init__(self) -> None:
        _cid(self.context_id, "direct-fixed audit context")
        _cid(self.profile_id, "direct-fixed audit profile")
        if (
            self.row_ids != tuple(sorted(set(self.row_ids)))
            or not self.row_ids
            or self.ground_row_count != len(self.row_ids)
            or self.ground_row_count not in (30, 60)
            or self.target_generative_draws
            != self.ground_row_count * FIXED_DRAWS_PER_ROW
            or type(self.outcome) is not DirectFixedAuditOutcome
            or type(self.root_failure_upper) is not Fraction
            or not 0 <= self.root_failure_upper <= 1
            or type(self.root_reward_lower) is not Fraction
            or not 0 <= self.root_reward_lower <= 1
            or type(self.normalized_regret_upper) is not Fraction
            or not 0 <= self.normalized_regret_upper <= 1
            or type(self.policy) is not tuple
            or not self.policy
            or any(
                type(item) is not direct_seq.DirectPolicyBoundV1
                for item in self.policy
            )
            or self.aggregate_obligations_evaluated not in (66, 132)
            or self.exact_probability_reads != 0
            or (
                self.outcome is DirectFixedAuditOutcome.CONDITIONALLY_CERTIFIED
                and (
                    self.root_failure_upper >= Fraction(1, 20)
                    or self.normalized_regret_upper > Fraction(1, 20)
                )
            )
        ):
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed robust audit is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_fixed_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "profile_id": self.profile_id,
            "row_ids": list(self.row_ids),
            "ground_row_count": self.ground_row_count,
            "target_generative_draws": self.target_generative_draws,
            "outcome": self.outcome.value,
            "root_failure_upper": _fdoc(self.root_failure_upper),
            "root_reward_lower": _fdoc(self.root_reward_lower),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "policy": [item.to_document() for item in self.policy],
            "aggregate_obligations_evaluated": (
                self.aggregate_obligations_evaluated
            ),
            "exact_probability_reads": 0,
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())


def _robust_audit(
    context: graph.VariableOrderGraphContextV1,
    profile: DirectFixedProfileV1,
    rows: tuple[DirectFixedRowV1, ...],
) -> DirectFixedAuditV1:
    by_key = {
        direct_seq._row_key(row.catalogue, row.action): row
        for row in rows
    }
    root, continuations = direct_seq._catalogues_from_rows(context, rows)
    child_decisions: dict[str, direct_seq.DirectPolicyBoundV1] = {}
    obligations = 0
    for catalogue in continuations:
        candidates: list[direct_seq.DirectPolicyBoundV1] = []
        for action in catalogue.actions:
            row = by_key[direct_seq._row_key(catalogue, action)]
            intervals = _fixed_intervals(row, profile)
            obligations += sum(
                not (
                    interval.lower == 1
                    and interval.upper == 1
                )
                for interval in intervals
            )
            failure = next(
                (
                    item.upper
                    for item in intervals
                    if item.destination == ("FAILURE",)
                ),
                Fraction(0),
            )
            reward = next(
                iter(
                    {
                        atom.normalized_reward
                        for atom in row.atom_descriptors
                    }
                )
            )
            candidates.append(
                direct_seq.DirectPolicyBoundV1(
                    catalogue.state.state_id,
                    1,
                    action,
                    failure,
                    reward,
                )
            )
        child_decisions[catalogue.state.state_id] = min(
            candidates,
            key=lambda item: (
                item.failure_upper,
                -item.reward_lower,
                item.action,
            ),
        )

    root_candidates: list[direct_seq.DirectPolicyBoundV1] = []
    for action in root.actions:
        row = by_key[direct_seq._row_key(root, action)]
        intervals = _fixed_intervals(row, profile)
        obligations += sum(
            not (
                interval.lower == 1
                and interval.upper == 1
            )
            for interval in intervals
        )
        risk_values: dict[tuple[Any, ...], Fraction] = {}
        reward_values: dict[tuple[Any, ...], Fraction] = {}
        for interval in intervals:
            destination = interval.destination
            if destination == ("FAILURE",):
                risk_values[destination] = Fraction(1)
                reward_values[destination] = Fraction(0)
            elif destination == ("SAFE_TERMINAL",):
                risk_values[destination] = Fraction(0)
                reward_values[destination] = Fraction(0)
            else:
                child = child_decisions[destination[1]]
                risk_values[destination] = child.failure_upper
                reward_values[destination] = child.reward_lower
        immediate = next(
            iter(
                {
                    atom.normalized_reward
                    for atom in row.atom_descriptors
                }
            )
        )
        root_candidates.append(
            direct_seq.DirectPolicyBoundV1(
                root.state.state_id,
                graph.HORIZON,
                action,
                graph._maximize_interval_expectation(
                    intervals,
                    risk_values,
                ),
                immediate
                + graph._minimize_interval_expectation(
                    intervals,
                    reward_values,
                ),
            )
        )
    feasible = tuple(
        item
        for item in root_candidates
        if item.failure_upper < context.risk_tolerance
    )
    selected = min(
        feasible if feasible else tuple(root_candidates),
        key=lambda item: (
            -item.reward_lower if feasible else item.failure_upper,
            item.failure_upper if feasible else -item.reward_lower,
            item.action,
        ),
    )
    regret = max(
        Fraction(0),
        graph._registered_query_reward_ceiling(context)
        - selected.reward_lower,
    )
    outcome = (
        DirectFixedAuditOutcome.CONDITIONALLY_CERTIFIED
        if (
            selected.failure_upper < context.risk_tolerance
            and regret <= Fraction(1, 20)
        )
        else DirectFixedAuditOutcome.FAILED_ROBUST_GROUND_AUDIT
    )
    policy = tuple(
        sorted(
            (selected,) + tuple(child_decisions.values()),
            key=lambda item: (-item.remaining_horizon, item.state_id),
        )
    )
    if obligations != profile.context_aggregate_obligation_count:
        raise VariableGraphDirectFixedInvariantViolation(
            "direct-fixed audit did not cover its registered event family"
        )
    return DirectFixedAuditV1(
        context_id=context.context_id,
        profile_id=profile.profile_id,
        row_ids=tuple(sorted(row.row_id for row in rows)),
        ground_row_count=len(rows),
        target_generative_draws=sum(row.draw_count for row in rows),
        outcome=outcome,
        root_failure_upper=selected.failure_upper,
        root_reward_lower=selected.reward_lower,
        normalized_regret_upper=regret,
        policy=policy,
        aggregate_obligations_evaluated=obligations,
    )


@dataclass(frozen=True, slots=True)
class DirectFixedResultV1:
    context: graph.VariableOrderGraphContextV1
    profile: DirectFixedProfileV1
    rows: tuple[DirectFixedRowV1, ...]
    audit: DirectFixedAuditV1
    acquired_ground_rows: int
    target_generative_draws: int
    target_random_word_calls: int
    structural_support_kernel_calls: int
    operational_exact_kernel_queries: int
    complete_h2_closure: bool = True
    v0066_packed_row_access_count: int = 0
    operational_exact_probability_reads: int = 0
    standalone_evaluation_embedded: bool = False

    def __post_init__(self) -> None:
        expected_rows = 30 if self.context.context_key == "variable_target_w5_v0" else 60
        if (
            type(self.context) is not graph.VariableOrderGraphContextV1
            or self.context.context_key
            not in ("variable_target_w5_v0", "variable_target_k6_v0")
            or type(self.profile) is not DirectFixedProfileV1
            or type(self.rows) is not tuple
            or len(self.rows) != expected_rows
            or any(type(item) is not DirectFixedRowV1 for item in self.rows)
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or type(self.audit) is not DirectFixedAuditV1
            or self.audit.outcome
            is not DirectFixedAuditOutcome.CONDITIONALLY_CERTIFIED
            or self.audit.row_ids
            != tuple(sorted(item.row_id for item in self.rows))
            or self.acquired_ground_rows != len(self.rows)
            or self.target_generative_draws
            != len(self.rows) * FIXED_DRAWS_PER_ROW
            or self.target_random_word_calls
            != sum(item.random_word_count for item in self.rows)
            or self.structural_support_kernel_calls
            != self.acquired_ground_rows
            or self.operational_exact_kernel_queries
            != self.structural_support_kernel_calls
            or self.complete_h2_closure is not True
            or self.v0066_packed_row_access_count != 0
            or self.operational_exact_probability_reads != 0
            or self.standalone_evaluation_embedded is not False
        ):
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed result is incomplete or crossed evaluation lanes"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_fixed_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context.context_id,
            "profile_id": self.profile.profile_id,
            "row_ids": [item.row_id for item in self.rows],
            "audit_id": self.audit.audit_id,
            "acquired_ground_rows": self.acquired_ground_rows,
            "target_generative_draws": self.target_generative_draws,
            "target_random_word_calls": self.target_random_word_calls,
            "structural_support_kernel_calls": (
                self.structural_support_kernel_calls
            ),
            "operational_exact_kernel_queries": (
                self.operational_exact_kernel_queries
            ),
            "complete_h2_closure": True,
            "v0066_packed_row_access_count": 0,
            "operational_exact_probability_reads": 0,
            "standalone_evaluation_embedded": False,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())


@functools.lru_cache(maxsize=2)
def run_direct_fixed_context_v1(
    context: graph.VariableOrderGraphContextV1,
) -> DirectFixedResultV1:
    """Generate one complete positive H2 closure directly at fixed n."""

    if (
        type(context) is not graph.VariableOrderGraphContextV1
        or context.context_key
        not in ("variable_target_w5_v0", "variable_target_k6_v0")
    ):
        raise VariableGraphDirectFixedInvariantViolation(
            "DIRECT_FIXED accepts exactly the two positive graph contexts"
        )
    manifest = direct_seq._build_structural_manifest(context)
    obligation_count = direct_seq._obligation_count(context)
    if direct_seq._manifest_obligation_count(manifest) != obligation_count:
        raise VariableGraphDirectFixedInvariantViolation(
            "DIRECT_FIXED structural manifest changed registered obligations"
        )
    profile = _profile(context, obligation_count)
    streams = tuple(
        _MutableDirectFixedStream.create(
            context,
            spec.catalogue,
            spec.action,
            spec.descriptors,
        )
        for spec in manifest.row_specs
    )
    for stream in streams:
        stream.generate()
    rows = tuple(
        sorted(
            (stream.freeze() for stream in streams),
            key=lambda item: item.row_id,
        )
    )
    audit = _robust_audit(context, profile, rows)
    if audit.outcome is not DirectFixedAuditOutcome.CONDITIONALLY_CERTIFIED:
        raise VariableGraphDirectFixedInvariantViolation(
            "registered DIRECT_FIXED positive control did not certify"
        )
    return DirectFixedResultV1(
        context=context,
        profile=profile,
        rows=rows,
        audit=audit,
        acquired_ground_rows=len(rows),
        target_generative_draws=sum(item.draw_count for item in rows),
        target_random_word_calls=sum(
            item.random_word_count for item in rows
        ),
        structural_support_kernel_calls=(
            manifest.structural_support_kernel_calls
        ),
        operational_exact_kernel_queries=(
            manifest.structural_support_kernel_calls
        ),
    )


@dataclass(frozen=True, slots=True)
class DirectFixedEvaluationV1:
    result_id: str
    audit_id: str
    exact_failure_probability: Fraction
    exact_normalized_reward: Fraction
    exact_policy_rows_evaluated: int
    evaluation_exact_kernel_calls: int
    audit_covers_exact_policy: bool
    evaluation_lane: str = "STANDALONE_EVALUATION"

    def __post_init__(self) -> None:
        _cid(self.result_id, "direct-fixed evaluation result")
        _cid(self.audit_id, "direct-fixed evaluation audit")
        if (
            type(self.exact_failure_probability) is not Fraction
            or not 0 <= self.exact_failure_probability <= 1
            or type(self.exact_normalized_reward) is not Fraction
            or not 0 <= self.exact_normalized_reward <= 1
            or type(self.exact_policy_rows_evaluated) is not int
            or self.exact_policy_rows_evaluated <= 0
            or self.evaluation_exact_kernel_calls
            != self.exact_policy_rows_evaluated
            or self.audit_covers_exact_policy is not True
            or self.evaluation_lane != "STANDALONE_EVALUATION"
        ):
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed exact evaluation is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_fixed_evaluation.v1",
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "audit_id": self.audit_id,
            "exact_failure_probability": _fdoc(
                self.exact_failure_probability
            ),
            "exact_normalized_reward": _fdoc(
                self.exact_normalized_reward
            ),
            "exact_policy_rows_evaluated": (
                self.exact_policy_rows_evaluated
            ),
            "evaluation_exact_kernel_calls": (
                self.evaluation_exact_kernel_calls
            ),
            "audit_covers_exact_policy": True,
            "evaluation_lane": self.evaluation_lane,
        }

    @property
    def evaluation_id(self) -> str:
        return _content_id("evaluation", self._payload())


def _evaluate_exact_policy(
    result: DirectFixedResultV1,
) -> DirectFixedEvaluationV1:
    assignments = {
        (item.state_id, item.remaining_horizon): item
        for item in result.audit.policy
    }
    kernel = graph.RelationalGraphMergeKernelV2(result.context)
    memo: dict[
        tuple[str, int],
        tuple[Fraction, Fraction],
    ] = {}
    exact_kernel_calls = 0

    def solve(
        state: graph.VariableGraphStateV1,
        remaining: int,
    ) -> tuple[Fraction, Fraction]:
        nonlocal exact_kernel_calls
        key = (state.state_id, remaining)
        if key in memo:
            return memo[key]
        assignment = assignments[key]
        atoms = kernel.atoms(state, assignment.action)
        exact_kernel_calls += 1
        risk = Fraction(0)
        reward = atoms[0].normalized_reward
        for atom in atoms:
            if atom.failure:
                risk += atom.probability
            elif remaining > 1:
                child_risk, child_reward = solve(
                    atom.next_state,
                    remaining - 1,
                )
                risk += atom.probability * child_risk
                reward += atom.probability * child_reward
        memo[key] = (risk, reward)
        return risk, reward

    risk, reward = solve(
        kernel.root_state(),
        graph.HORIZON,
    )
    return DirectFixedEvaluationV1(
        result_id=result.result_id,
        audit_id=result.audit.audit_id,
        exact_failure_probability=risk,
        exact_normalized_reward=reward,
        exact_policy_rows_evaluated=exact_kernel_calls,
        evaluation_exact_kernel_calls=exact_kernel_calls,
        audit_covers_exact_policy=(
            risk <= result.audit.root_failure_upper
            and reward >= result.audit.root_reward_lower
        ),
    )


@dataclass(frozen=True, slots=True)
class DirectFixedVerificationV1:
    result_id: str
    replayed_row_ids: tuple[str, ...]
    replayed_paired_stream_ids: tuple[str, ...]
    replayed_audit_id: str
    replayed_structural_support_kernel_calls: int
    replayed_operational_exact_kernel_queries: int
    evaluation: DirectFixedEvaluationV1
    raw_replay_passed: bool
    complete_closure_passed: bool
    no_v0066_packed_row_access_passed: bool
    operational_evaluation_separation_passed: bool

    def __post_init__(self) -> None:
        _cid(self.result_id, "direct-fixed verification result")
        _cid(self.replayed_audit_id, "direct-fixed verification audit")
        if (
            self.replayed_row_ids
            != tuple(sorted(set(self.replayed_row_ids)))
            or not self.replayed_row_ids
            or self.replayed_paired_stream_ids
            != tuple(sorted(set(self.replayed_paired_stream_ids)))
            or len(self.replayed_paired_stream_ids)
            != len(self.replayed_row_ids)
            or self.replayed_structural_support_kernel_calls
            != len(self.replayed_row_ids)
            or self.replayed_operational_exact_kernel_queries
            != self.replayed_structural_support_kernel_calls
            or type(self.evaluation) is not DirectFixedEvaluationV1
            or self.evaluation.result_id != self.result_id
            or self.evaluation.audit_id != self.replayed_audit_id
            or self.raw_replay_passed is not True
            or self.complete_closure_passed is not True
            or self.no_v0066_packed_row_access_passed is not True
            or self.operational_evaluation_separation_passed is not True
        ):
            raise VariableGraphDirectFixedInvariantViolation(
                "direct-fixed verification is incomplete"
            )

    @property
    def verification_id(self) -> str:
        return _content_id(
            "verification",
            {
                "schema": "acfqp.v0067_direct_fixed_verification.v1",
                "schema_version": SCHEMA_VERSION,
                "result_id": self.result_id,
                "replayed_row_ids": list(self.replayed_row_ids),
                "replayed_paired_stream_ids": list(
                    self.replayed_paired_stream_ids
                ),
                "replayed_audit_id": self.replayed_audit_id,
                "replayed_structural_support_kernel_calls": (
                    self.replayed_structural_support_kernel_calls
                ),
                "replayed_operational_exact_kernel_queries": (
                    self.replayed_operational_exact_kernel_queries
                ),
                "evaluation_id": self.evaluation.evaluation_id,
                "raw_replay_passed": True,
                "complete_closure_passed": True,
                "no_v0066_packed_row_access_passed": True,
                "operational_evaluation_separation_passed": True,
            },
        )


def verify_direct_fixed_result_v1(
    result: DirectFixedResultV1,
) -> DirectFixedVerificationV1:
    if type(result) is not DirectFixedResultV1:
        raise VariableGraphDirectFixedInvariantViolation(
            "DIRECT_FIXED verifier rejects runtime substitutions"
        )
    expected = run_direct_fixed_context_v1(result.context)
    if expected.result_id != result.result_id:
        raise VariableGraphDirectFixedInvariantViolation(
            "DIRECT_FIXED result failed canonical operational replay"
        )
    for row in result.rows:
        verify_direct_fixed_row_v1(result.context, row)
    replayed_audit = _robust_audit(
        result.context,
        result.profile,
        result.rows,
    )
    if replayed_audit.audit_id != result.audit.audit_id:
        raise VariableGraphDirectFixedInvariantViolation(
            "DIRECT_FIXED robust audit failed replay"
        )
    evaluation = _evaluate_exact_policy(result)
    return DirectFixedVerificationV1(
        result_id=result.result_id,
        replayed_row_ids=tuple(sorted(item.row_id for item in result.rows)),
        replayed_paired_stream_ids=tuple(
            sorted(item.paired_stream_id for item in result.rows)
        ),
        replayed_audit_id=replayed_audit.audit_id,
        replayed_structural_support_kernel_calls=len(result.rows),
        replayed_operational_exact_kernel_queries=len(result.rows),
        evaluation=evaluation,
        raw_replay_passed=True,
        complete_closure_passed=True,
        no_v0066_packed_row_access_passed=True,
        operational_evaluation_separation_passed=True,
    )


__all__ = [
    "CONTRACT_VERSION",
    "DirectFixedAuditOutcome",
    "DirectFixedAuditV1",
    "DirectFixedEvaluationV1",
    "DirectFixedProfileV1",
    "DirectFixedResultV1",
    "DirectFixedRowV1",
    "DirectFixedVerificationV1",
    "FIXED_DRAWS_PER_ROW",
    "PER_OBLIGATION_TAIL_UPPER",
    "PROFILE_KEY",
    "PROVEN_POSITIVE_FAMILY_TAIL_UPPER",
    "REGISTERED_GATE_TAIL_BUDGET",
    "SCHEMA_VERSION",
    "TARGET_HALF_WIDTH",
    "VariableGraphDirectFixedInvariantViolation",
    "paired_stream_identity_v1",
    "run_direct_fixed_context_v1",
    "verify_direct_fixed_result_v1",
    "verify_direct_fixed_row_v1",
]
