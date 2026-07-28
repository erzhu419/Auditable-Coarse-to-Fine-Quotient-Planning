"""Cold direct-ground sequential controls for the V0-067 graph Gate.

The controls in this module are deliberately separate from the quotient
runner.  They construct the complete registered H2 ground state-action
closure for one target occurrence, acquire every row directly from the
paired V0-066 counter stream, and solve the resulting ground robust dynamic
program after each preregistered checkpoint.

Only the prefix needed by the first target-local certificate is generated.
The operational path never constructs a 131,072-draw row and never reads a
V0-066 packed row.  Exact probabilities are used only after the statistical
result is frozen, in the standalone evaluation object.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import math
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
import acfqp.sequential_bernoulli_acquisition_v1 as sequential
import acfqp.variable_order_graph_rapm_v1 as graph


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.31.0"
PROFILE_KEY = "v0067_cold_direct_ground_anytime_graph_v0"
CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
MAX_DRAWS_PER_ROW = CHECKPOINTS[-1]
PER_OBLIGATION_ALPHA = Fraction(1, 250_000)
POSITIVE_FAMILY_OBLIGATION_COUNT = 198
FAMILY_TAIL_UPPER = Fraction(198, 250_000)


DOMAIN_TAGS = {
    "profile": "acfqp:v0067-direct-sequential-profile:v1",
    "row": "acfqp:v0067-direct-sequential-row:v1",
    "audit": "acfqp:v0067-direct-sequential-audit:v1",
    "evaluation": "acfqp:v0067-direct-sequential-evaluation:v1",
    "result": "acfqp:v0067-direct-sequential-result:v1",
    "verification": "acfqp:v0067-direct-sequential-verification:v1",
}


class VariableGraphDirectSequentialInvariantViolation(ValueError):
    """A direct prefix, interval, policy, or evaluation is invalid."""


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    raw_suffix: bytes = b"",
) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise VariableGraphDirectSequentialInvariantViolation(
            str(error)
        ) from error
    material = tag + b"\x00" + body
    if raw_suffix:
        material += b"\x00" + raw_suffix
    return hashlib.sha256(material).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise VariableGraphDirectSequentialInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def _row_key(
    catalogue: graph.VariableGraphCatalogueV1,
    action: tuple[int, int, int],
) -> tuple[str, tuple[int, int, int]]:
    return catalogue.catalogue_id, action


@dataclass(frozen=True, slots=True)
class DirectSequentialProfileV1:
    context_id: str
    context_aggregate_obligation_count: int
    family_aggregate_obligation_count: int
    per_obligation_alpha: Fraction
    context_tail_upper: Fraction
    registered_family_tail_upper: Fraction
    checkpoints: tuple[int, ...] = CHECKPOINTS
    boundary_grid_bits: int = 24
    fixed_full_row_draws_forbidden: bool = True
    exact_probability_operational_access_forbidden: bool = True

    def __post_init__(self) -> None:
        _cid(self.context_id, "direct profile context")
        if (
            type(self.context_aggregate_obligation_count) is not int
            or self.context_aggregate_obligation_count <= 0
            or type(self.family_aggregate_obligation_count) is not int
            or self.family_aggregate_obligation_count
            < self.context_aggregate_obligation_count
            or type(self.per_obligation_alpha) is not Fraction
            or not 0 < self.per_obligation_alpha < 1
            or self.context_tail_upper
            != self.context_aggregate_obligation_count
            * self.per_obligation_alpha
            or self.registered_family_tail_upper
            != self.family_aggregate_obligation_count
            * self.per_obligation_alpha
            or self.registered_family_tail_upper != FAMILY_TAIL_UPPER
            or self.checkpoints != CHECKPOINTS
            or self.boundary_grid_bits != 24
            or self.fixed_full_row_draws_forbidden is not True
            or self.exact_probability_operational_access_forbidden is not True
        ):
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct sequential profile changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_sequential_profile.v1",
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
            "per_obligation_alpha": _fdoc(
                self.per_obligation_alpha
            ),
            "context_tail_upper": _fdoc(self.context_tail_upper),
            "registered_family_tail_upper": _fdoc(
                self.registered_family_tail_upper
            ),
            "checkpoints": list(self.checkpoints),
            "boundary_grid_bits": self.boundary_grid_bits,
            "confidence_method_id": sequential.METHOD_ID,
            "fixed_full_row_draws_forbidden": True,
            "exact_probability_operational_access_forbidden": True,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


@dataclass(frozen=True, slots=True)
class DirectPrefixRowV1:
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
    maximum_generated_draw_index: int

    def __post_init__(self) -> None:
        _cid(self.context_id, "direct row context")
        if (
            type(self.catalogue) is not graph.VariableGraphCatalogueV1
            or self.catalogue.context_id != self.context_id
            or self.action not in self.catalogue.actions
            or type(self.atom_descriptors) is not tuple
            or len(self.atom_descriptors)
            != 2 * (len(self.catalogue.state.ranks) - 2)
            or any(
                type(item) is not graph.ObservedVariableGraphAtomV1
                for item in self.atom_descriptors
            )
            or tuple(item.ordinal for item in self.atom_descriptors)
            != tuple(range(len(self.atom_descriptors)))
            or self.draw_count not in CHECKPOINTS
            or self.draw_count >= graph.SAMPLE_COUNT_PER_ROW
            or self.random_word_count
            != self.draw_count + self.rejection_count
            or self.rejection_count < 0
            or type(self.ordinal_counts) is not tuple
            or len(self.ordinal_counts) != len(self.atom_descriptors)
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
            or self.maximum_generated_draw_index != self.draw_count - 1
        ):
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct prefix row shape or no-lookahead boundary changed"
            )
        decoded = graph._unpack_three_bit_ordinals(
            self.packed_ordinals,
            self.draw_count,
            len(self.atom_descriptors),
        )
        counts = [0] * len(self.atom_descriptors)
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
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct prefix packed replay failed"
            )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_prefix_row.v1",
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
            "packed_ordinal_sha256": hashlib.sha256(
                self.packed_ordinals
            ).hexdigest(),
            "packed_rejection_sha256": hashlib.sha256(
                self.packed_rejection_flags
            ).hexdigest(),
            "paired_v0066_seed": self.paired_v0066_seed,
            "maximum_generated_draw_index": (
                self.maximum_generated_draw_index
            ),
            "v0066_full_row_access_count": 0,
            "exact_probability_reads": 0,
        }

    @property
    def row_id(self) -> str:
        return _content_id(
            "row",
            self._identity_payload(),
            self.packed_ordinals + b"\x00" + self.packed_rejection_flags,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._identity_payload(), "row_id": self.row_id}


def _descriptors(
    context: graph.VariableOrderGraphContextV1,
    catalogue: graph.VariableGraphCatalogueV1,
    action: tuple[int, int, int],
) -> tuple[graph.ObservedVariableGraphAtomV1, ...]:
    # Only structural support, reward, and failure flags are projected.  The
    # exact probability field of VariableGraphAtomV1 is never read here.
    return tuple(
        graph.ObservedVariableGraphAtomV1(
            atom.ordinal,
            atom.next_state,
            atom.normalized_reward,
            atom.failure,
        )
        for atom in graph.RelationalGraphMergeKernelV2(context).atoms(
            catalogue.state,
            action,
        )
    )


@dataclass(frozen=True, slots=True)
class _StructuralRowSpecV1:
    catalogue: graph.VariableGraphCatalogueV1
    action: tuple[int, int, int]
    descriptors: tuple[graph.ObservedVariableGraphAtomV1, ...]


@dataclass(frozen=True, slots=True)
class _DirectStructuralManifestV1:
    root: graph.VariableGraphCatalogueV1
    continuations: tuple[graph.VariableGraphCatalogueV1, ...]
    row_specs: tuple[_StructuralRowSpecV1, ...]
    structural_support_kernel_calls: int


def _build_structural_manifest(
    context: graph.VariableOrderGraphContextV1,
) -> _DirectStructuralManifestV1:
    """Query each structural state-action support exactly once per run."""

    kernel = graph.RelationalGraphMergeKernelV2(context)
    root = graph._catalogue(context, kernel.root_state(), graph.HORIZON)
    root_specs = tuple(
        _StructuralRowSpecV1(
            root,
            action,
            _descriptors(context, root, action),
        )
        for action in root.actions
    )
    successors = {
        atom.next_state
        for spec in root_specs
        for atom in spec.descriptors
        if not atom.failure
    }
    continuations = tuple(
        sorted(
            (
                graph._catalogue(context, state, 1)
                for state in successors
            ),
            key=lambda item: item.catalogue_id,
        )
    )
    continuation_specs = tuple(
        _StructuralRowSpecV1(
            catalogue,
            action,
            _descriptors(context, catalogue, action),
        )
        for catalogue in continuations
        for action in catalogue.actions
    )
    row_specs = tuple(
        sorted(
            root_specs + continuation_specs,
            key=lambda item: (
                -item.catalogue.remaining_horizon,
                item.catalogue.catalogue_id,
                item.action,
            ),
        )
    )
    return _DirectStructuralManifestV1(
        root,
        continuations,
        row_specs,
        len(row_specs),
    )


def _complete_h2_catalogues(
    context: graph.VariableOrderGraphContextV1,
) -> tuple[
    graph.VariableGraphCatalogueV1,
    tuple[graph.VariableGraphCatalogueV1, ...],
]:
    manifest = _build_structural_manifest(context)
    return manifest.root, manifest.continuations


def _all_row_specs(
    context: graph.VariableOrderGraphContextV1,
) -> tuple[
    tuple[graph.VariableGraphCatalogueV1, tuple[int, int, int]], ...
]:
    return tuple(
        (item.catalogue, item.action)
        for item in _build_structural_manifest(context).row_specs
    )


def _destination(
    row: DirectPrefixRowV1,
    atom: graph.ObservedVariableGraphAtomV1,
) -> tuple[Any, ...]:
    if atom.failure:
        return ("FAILURE",)
    if row.catalogue.remaining_horizon == 1:
        return ("SAFE_TERMINAL",)
    return ("ACTIVE", atom.next_state.state_id)


def _obligation_count(
    context: graph.VariableOrderGraphContextV1,
) -> int:
    registered = {
        "variable_target_w5_v0": 66,
        "variable_target_k6_v0": 132,
    }
    try:
        return registered[context.context_key]
    except KeyError as error:
        raise VariableGraphDirectSequentialInvariantViolation(
            "direct obligation count is not registered for this context"
        ) from error


def _manifest_obligation_count(
    manifest: _DirectStructuralManifestV1,
) -> int:
    total = 0
    for spec in manifest.row_specs:
        destinations = {
            (
                ("FAILURE",)
                if atom.failure
                else (
                    ("SAFE_TERMINAL",)
                    if spec.catalogue.remaining_horizon == 1
                    else ("ACTIVE", atom.next_state.state_id)
                )
            )
            for atom in spec.descriptors
        }
        if len(destinations) > 1:
            total += len(destinations)
    if total <= 0:
        raise VariableGraphDirectSequentialInvariantViolation(
            "direct confidence obligation family is empty"
        )
    return total


def _catalogues_from_rows(
    context: graph.VariableOrderGraphContextV1,
    rows: tuple[Any, ...],
) -> tuple[
    graph.VariableGraphCatalogueV1,
    tuple[graph.VariableGraphCatalogueV1, ...],
]:
    catalogues = {
        row.catalogue.catalogue_id: row.catalogue
        for row in rows
    }
    roots = tuple(
        item
        for item in catalogues.values()
        if item.remaining_horizon == graph.HORIZON
    )
    continuations = tuple(
        sorted(
            (
                item
                for item in catalogues.values()
                if item.remaining_horizon == 1
            ),
            key=lambda item: item.catalogue_id,
        )
    )
    if len(roots) != 1:
        raise VariableGraphDirectSequentialInvariantViolation(
            "direct rows do not contain exactly one H2 root catalogue"
        )
    root = roots[0]
    actual_keys = {
        (row.catalogue.catalogue_id, row.action)
        for row in rows
    }
    expected_keys = {
        (catalogue.catalogue_id, action)
        for catalogue in (root,) + continuations
        for action in catalogue.actions
    }
    root_successors = {
        atom.next_state.state_id
        for row in rows
        if row.catalogue.catalogue_id == root.catalogue_id
        for atom in row.atom_descriptors
        if not atom.failure
    }
    if (
        root.context_id != context.context_id
        or any(item.context_id != context.context_id for item in continuations)
        or actual_keys != expected_keys
        or {item.state.state_id for item in continuations}
        != root_successors
    ):
        raise VariableGraphDirectSequentialInvariantViolation(
            "direct rows are not the complete stored H2 closure"
        )
    return root, continuations


@dataclass(slots=True)
class _MutableRowStream:
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
    ) -> "_MutableRowStream":
        return cls(
            context,
            catalogue,
            action,
            descriptors,
            graph._row_seed(context, catalogue, action),
            [],
            [],
            [0] * (2 * (context.vertex_count - 2)),
        )

    def advance(self, draw_count: int) -> None:
        if (
            draw_count not in CHECKPOINTS
            or draw_count <= len(self.ordinals)
            or draw_count > MAX_DRAWS_PER_ROW
        ):
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct stream checkpoint is invalid"
            )
        gamma = 0x9E3779B97F4A7C15
        while len(self.ordinals) < draw_count:
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

    def freeze(self) -> DirectPrefixRowV1:
        return DirectPrefixRowV1(
            self.context.context_id,
            self.catalogue,
            self.action,
            self.descriptors,
            len(self.ordinals),
            self.random_word_index,
            self.random_word_index - len(self.ordinals),
            tuple(self.counts),
            graph._pack_three_bit_ordinals(self.ordinals),
            graph._pack_rejection_flags(self.rejection_flags),
            self.seed,
            len(self.ordinals) - 1,
        )


def _confidence_profile(
    profile: DirectSequentialProfileV1,
) -> sequential.SequentialBernoulliProfileV1:
    return sequential.SequentialBernoulliProfileV1(
        profile.per_obligation_alpha,
        Fraction(1, 140),
        profile.checkpoints,
        profile.boundary_grid_bits,
    )


def _row_intervals(
    row: DirectPrefixRowV1,
    profile: DirectSequentialProfileV1,
) -> tuple[graph.StatisticalDestinationIntervalV1, ...]:
    counts: dict[tuple[Any, ...], int] = defaultdict(int)
    ordinals: dict[tuple[Any, ...], set[int]] = defaultdict(set)
    for atom in row.atom_descriptors:
        destination = _destination(row, atom)
        counts[destination] += row.ordinal_counts[atom.ordinal]
        ordinals[destination].add(atom.ordinal)
    confidence_profile = _confidence_profile(profile)
    intervals: list[graph.StatisticalDestinationIntervalV1] = []
    for destination in sorted(counts, key=repr):
        if len(ordinals[destination]) == len(row.atom_descriptors):
            lower = upper = Fraction(1)
        else:
            checkpoint = sequential.build_anytime_bernoulli_checkpoint_v1(
                row.draw_count,
                counts[destination],
                confidence_profile,
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


class DirectSequentialAuditOutcome(str, Enum):
    CONDITIONALLY_CERTIFIED = "CONDITIONALLY_CERTIFIED"
    FAILED_AT_CHECKPOINT = "FAILED_AT_CHECKPOINT"


@dataclass(frozen=True, slots=True)
class DirectPolicyBoundV1:
    state_id: str
    remaining_horizon: int
    action: tuple[int, int, int]
    failure_upper: Fraction
    reward_lower: Fraction

    def __post_init__(self) -> None:
        _cid(self.state_id, "direct policy state")
        if (
            self.remaining_horizon not in (1, graph.HORIZON)
            or type(self.action) is not tuple
            or len(self.action) != 3
            or type(self.failure_upper) is not Fraction
            or not 0 <= self.failure_upper <= 1
            or type(self.reward_lower) is not Fraction
            or not 0 <= self.reward_lower <= 1
        ):
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct policy bound is invalid"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "failure_upper": _fdoc(self.failure_upper),
            "reward_lower": _fdoc(self.reward_lower),
        }


@dataclass(frozen=True, slots=True)
class DirectSequentialAuditV1:
    context_id: str
    profile_id: str
    row_ids: tuple[str, ...]
    checkpoint_draws_per_row: int
    outcome: DirectSequentialAuditOutcome
    root_failure_upper: Fraction
    root_reward_lower: Fraction
    normalized_regret_upper: Fraction
    policy: tuple[DirectPolicyBoundV1, ...]
    aggregate_obligations_evaluated: int

    def __post_init__(self) -> None:
        _cid(self.context_id, "direct audit context")
        _cid(self.profile_id, "direct audit profile")
        if (
            self.row_ids != tuple(sorted(set(self.row_ids)))
            or not self.row_ids
            or self.checkpoint_draws_per_row not in CHECKPOINTS
            or type(self.outcome) is not DirectSequentialAuditOutcome
            or type(self.root_failure_upper) is not Fraction
            or not 0 <= self.root_failure_upper <= 1
            or type(self.root_reward_lower) is not Fraction
            or not 0 <= self.root_reward_lower <= 1
            or type(self.normalized_regret_upper) is not Fraction
            or not 0 <= self.normalized_regret_upper <= 1
            or type(self.policy) is not tuple
            or not self.policy
            or any(type(item) is not DirectPolicyBoundV1 for item in self.policy)
            or type(self.aggregate_obligations_evaluated) is not int
            or self.aggregate_obligations_evaluated <= 0
            or (
                self.outcome
                is DirectSequentialAuditOutcome.CONDITIONALLY_CERTIFIED
                and (
                    self.root_failure_upper >= Fraction(1, 20)
                    or self.normalized_regret_upper > Fraction(1, 20)
                )
            )
        ):
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct sequential audit is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_sequential_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "profile_id": self.profile_id,
            "row_ids": list(self.row_ids),
            "checkpoint_draws_per_row": self.checkpoint_draws_per_row,
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
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


def _audit(
    context: graph.VariableOrderGraphContextV1,
    profile: DirectSequentialProfileV1,
    rows: tuple[DirectPrefixRowV1, ...],
) -> DirectSequentialAuditV1:
    by_key = {
        _row_key(row.catalogue, row.action): row for row in rows
    }
    root, continuations = _catalogues_from_rows(context, rows)
    child_decisions: dict[str, DirectPolicyBoundV1] = {}
    obligations = 0
    for catalogue in continuations:
        candidates: list[DirectPolicyBoundV1] = []
        for action in catalogue.actions:
            row = by_key[_row_key(catalogue, action)]
            intervals = _row_intervals(row, profile)
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
                DirectPolicyBoundV1(
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
    root_candidates: list[DirectPolicyBoundV1] = []
    for action in root.actions:
        row = by_key[_row_key(root, action)]
        intervals = _row_intervals(row, profile)
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
            DirectPolicyBoundV1(
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
        DirectSequentialAuditOutcome.CONDITIONALLY_CERTIFIED
        if (
            selected.failure_upper < context.risk_tolerance
            and regret <= Fraction(1, 20)
        )
        else DirectSequentialAuditOutcome.FAILED_AT_CHECKPOINT
    )
    policy = tuple(
        sorted(
            (selected,) + tuple(child_decisions.values()),
            key=lambda item: (-item.remaining_horizon, item.state_id),
        )
    )
    return DirectSequentialAuditV1(
        context.context_id,
        profile.profile_id,
        tuple(sorted(row.row_id for row in rows)),
        rows[0].draw_count,
        outcome,
        selected.failure_upper,
        selected.reward_lower,
        regret,
        policy,
        obligations,
    )


@dataclass(frozen=True, slots=True)
class DirectSequentialEvaluationV1:
    context_id: str
    audit_id: str
    exact_failure_probability: Fraction
    exact_normalized_reward: Fraction
    exact_policy_rows_evaluated: int
    evaluation_exact_kernel_calls: int
    audit_covers_exact_policy: bool
    evaluation_lane: str = "STANDALONE_EVALUATION"

    def __post_init__(self) -> None:
        _cid(self.context_id, "direct evaluation context")
        _cid(self.audit_id, "direct evaluation audit")
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
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct exact evaluation is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_sequential_evaluation.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
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

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evaluation_id": self.evaluation_id}


def _evaluate_exact_policy(
    context: graph.VariableOrderGraphContextV1,
    audit: DirectSequentialAuditV1,
) -> DirectSequentialEvaluationV1:
    assignments = {
        (item.state_id, item.remaining_horizon): item
        for item in audit.policy
    }
    kernel = graph.RelationalGraphMergeKernelV2(context)
    evaluated: set[tuple[str, int]] = set()

    def solve(
        state: graph.VariableGraphStateV1,
        remaining: int,
    ) -> tuple[Fraction, Fraction]:
        assignment = assignments[(state.state_id, remaining)]
        evaluated.add((state.state_id, remaining))
        atoms = kernel.atoms(state, assignment.action)
        immediate = atoms[0].normalized_reward
        risk = Fraction(0)
        reward = immediate
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
        return risk, reward

    risk, reward = solve(kernel.root_state(), graph.HORIZON)
    return DirectSequentialEvaluationV1(
        context.context_id,
        audit.audit_id,
        risk,
        reward,
        len(evaluated),
        len(evaluated),
        (
            risk <= audit.root_failure_upper
            and reward >= audit.root_reward_lower
        ),
    )


@dataclass(frozen=True, slots=True)
class DirectSequentialResultV1:
    context: graph.VariableOrderGraphContextV1
    profile: DirectSequentialProfileV1
    rows: tuple[DirectPrefixRowV1, ...]
    audits: tuple[DirectSequentialAuditV1, ...]
    final_audit: DirectSequentialAuditV1
    evaluation: DirectSequentialEvaluationV1
    acquired_ground_rows: int
    target_generative_draws: int
    structural_support_kernel_calls: int
    operational_exact_kernel_queries: int
    full_v0066_row_access_count: int = 0
    operational_exact_probability_reads: int = 0
    cold_occurrence_local_model: bool = True
    target_model_reused: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.context) is not graph.VariableOrderGraphContextV1
            or type(self.profile) is not DirectSequentialProfileV1
            or type(self.rows) is not tuple
            or not self.rows
            or any(type(item) is not DirectPrefixRowV1 for item in self.rows)
            or type(self.audits) is not tuple
            or not self.audits
            or any(
                type(item) is not DirectSequentialAuditV1
                for item in self.audits
            )
            or self.final_audit != self.audits[-1]
            or self.final_audit.outcome
            is not DirectSequentialAuditOutcome.CONDITIONALLY_CERTIFIED
            or type(self.evaluation) is not DirectSequentialEvaluationV1
            or self.evaluation.audit_id != self.final_audit.audit_id
            or self.acquired_ground_rows != len(self.rows)
            or self.target_generative_draws
            != sum(item.draw_count for item in self.rows)
            or len({item.draw_count for item in self.rows}) != 1
            or self.structural_support_kernel_calls
            != self.acquired_ground_rows
            or self.operational_exact_kernel_queries
            != self.structural_support_kernel_calls
            or self.full_v0066_row_access_count != 0
            or self.operational_exact_probability_reads != 0
            or self.cold_occurrence_local_model is not True
            or self.target_model_reused is not False
        ):
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct sequential result is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_sequential_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context.context_id,
            "profile_id": self.profile.profile_id,
            "row_ids": [item.row_id for item in self.rows],
            "audit_ids": [item.audit_id for item in self.audits],
            "final_audit_id": self.final_audit.audit_id,
            "evaluation_id": self.evaluation.evaluation_id,
            "acquired_ground_rows": self.acquired_ground_rows,
            "target_generative_draws": self.target_generative_draws,
            "structural_support_kernel_calls": (
                self.structural_support_kernel_calls
            ),
            "operational_exact_kernel_queries": (
                self.operational_exact_kernel_queries
            ),
            "full_v0066_row_access_count": 0,
            "operational_exact_probability_reads": 0,
            "cold_occurrence_local_model": True,
            "target_model_reused": False,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def run_direct_sequential_context_v1(
    context: graph.VariableOrderGraphContextV1,
) -> DirectSequentialResultV1:
    """Run one cold positive-context direct control from empty streams."""

    if (
        type(context) is not graph.VariableOrderGraphContextV1
        or context.context_key
        not in ("variable_target_w5_v0", "variable_target_k6_v0")
    ):
        raise VariableGraphDirectSequentialInvariantViolation(
            "direct sequential Gate accepts only the two positive contexts"
        )
    manifest = _build_structural_manifest(context)
    obligation_count = _obligation_count(context)
    if _manifest_obligation_count(manifest) != obligation_count:
        raise VariableGraphDirectSequentialInvariantViolation(
            "stored structural manifest changed the registered obligations"
        )
    family_obligation_count = POSITIVE_FAMILY_OBLIGATION_COUNT
    alpha = PER_OBLIGATION_ALPHA
    profile = DirectSequentialProfileV1(
        context.context_id,
        obligation_count,
        family_obligation_count,
        alpha,
        obligation_count * alpha,
        FAMILY_TAIL_UPPER,
    )
    streams = tuple(
        _MutableRowStream.create(
            context,
            spec.catalogue,
            spec.action,
            spec.descriptors,
        )
        for spec in manifest.row_specs
    )
    audits: list[DirectSequentialAuditV1] = []
    final_rows: tuple[DirectPrefixRowV1, ...] | None = None
    for checkpoint in CHECKPOINTS:
        for stream in streams:
            stream.advance(checkpoint)
        rows = tuple(
            sorted(
                (stream.freeze() for stream in streams),
                key=lambda item: item.row_id,
            )
        )
        audit = _audit(context, profile, rows)
        audits.append(audit)
        if (
            audit.outcome
            is DirectSequentialAuditOutcome.CONDITIONALLY_CERTIFIED
        ):
            final_rows = rows
            break
    if final_rows is None:
        raise VariableGraphDirectSequentialInvariantViolation(
            "registered positive direct control exhausted its sample cap"
        )
    evaluation = _evaluate_exact_policy(context, audits[-1])
    return DirectSequentialResultV1(
        context,
        profile,
        final_rows,
        tuple(audits),
        audits[-1],
        evaluation,
        len(final_rows),
        sum(item.draw_count for item in final_rows),
        manifest.structural_support_kernel_calls,
        manifest.structural_support_kernel_calls,
    )


@dataclass(frozen=True, slots=True)
class DirectSequentialVerificationV1:
    result_id: str
    replayed_row_ids: tuple[str, ...]
    replayed_audit_ids: tuple[str, ...]
    replayed_evaluation_id: str
    replayed_structural_support_kernel_calls: int
    replayed_operational_exact_kernel_queries: int
    evaluation_exact_kernel_calls: int
    raw_prefix_replay_passed: bool
    first_certificate_stopping_passed: bool
    no_full_evidence_access_passed: bool

    def __post_init__(self) -> None:
        _cid(self.result_id, "direct verification result")
        if (
            self.replayed_row_ids != tuple(sorted(set(self.replayed_row_ids)))
            or not self.replayed_row_ids
            or not self.replayed_audit_ids
            or not self.replayed_evaluation_id
            or self.replayed_structural_support_kernel_calls
            != len(self.replayed_row_ids)
            or self.replayed_operational_exact_kernel_queries
            != self.replayed_structural_support_kernel_calls
            or self.evaluation_exact_kernel_calls <= 0
            or self.raw_prefix_replay_passed is not True
            or self.first_certificate_stopping_passed is not True
            or self.no_full_evidence_access_passed is not True
        ):
            raise VariableGraphDirectSequentialInvariantViolation(
                "direct verification is incomplete"
            )
        for value in (
            *self.replayed_row_ids,
            *self.replayed_audit_ids,
            self.replayed_evaluation_id,
        ):
            _cid(value, "direct verification artifact")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v0067_direct_sequential_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "replayed_row_ids": list(self.replayed_row_ids),
            "replayed_audit_ids": list(self.replayed_audit_ids),
            "replayed_evaluation_id": self.replayed_evaluation_id,
            "replayed_structural_support_kernel_calls": (
                self.replayed_structural_support_kernel_calls
            ),
            "replayed_operational_exact_kernel_queries": (
                self.replayed_operational_exact_kernel_queries
            ),
            "evaluation_exact_kernel_calls": (
                self.evaluation_exact_kernel_calls
            ),
            "raw_prefix_replay_passed": True,
            "first_certificate_stopping_passed": True,
            "no_full_evidence_access_passed": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())


def verify_direct_sequential_result_v1(
    result: DirectSequentialResultV1,
) -> DirectSequentialVerificationV1:
    if type(result) is not DirectSequentialResultV1:
        raise VariableGraphDirectSequentialInvariantViolation(
            "direct verifier rejects runtime substitutions"
        )
    expected = run_direct_sequential_context_v1(result.context)
    if expected.result_id != result.result_id:
        raise VariableGraphDirectSequentialInvariantViolation(
            "direct sequential result failed full replay"
        )
    return DirectSequentialVerificationV1(
        result.result_id,
        tuple(sorted(item.row_id for item in expected.rows)),
        tuple(item.audit_id for item in expected.audits),
        expected.evaluation.evaluation_id,
        expected.structural_support_kernel_calls,
        expected.operational_exact_kernel_queries,
        expected.evaluation.evaluation_exact_kernel_calls,
        True,
        True,
        True,
    )


__all__ = [
    "CHECKPOINTS",
    "CONTRACT_VERSION",
    "DirectPolicyBoundV1",
    "DirectPrefixRowV1",
    "DirectSequentialAuditOutcome",
    "DirectSequentialAuditV1",
    "DirectSequentialEvaluationV1",
    "DirectSequentialProfileV1",
    "DirectSequentialResultV1",
    "DirectSequentialVerificationV1",
    "FAMILY_TAIL_UPPER",
    "MAX_DRAWS_PER_ROW",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "VariableGraphDirectSequentialInvariantViolation",
    "run_direct_sequential_context_v1",
    "verify_direct_sequential_result_v1",
]
