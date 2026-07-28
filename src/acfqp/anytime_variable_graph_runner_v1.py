"""No-full-data anytime graph consumer for the V0-067 construction slice.

This module is a consumer of the frozen V0-066 graph simulator and portable
grammar, but it is deliberately not a consumer of V0-066 packed full rows or
the full-data selected coordinate profile.

For each registered target context it:

1. starts every required ground-row stream at draw zero using the exact
   V0-066 row seed and rejection mapper;
2. extends raw ordinal prefixes only to checkpoints 2048, 4096, 8192, 16384;
3. preregisters every grammar-reachable aggregate destination event;
4. constructs a target-local likelihood-mixture confidence sequence for each
   aggregate count from the single ordinal transcript;
5. rebuilds the partial RAPM and complete H=2 audit after each checkpoint;
6. regenerates any refinement registry from that checkpoint's target log;
7. stops at the first certified plan, or executes the unchanged exact ground
   fallback after the hard cap.

The operational path never calls ``_acquire_row``,
``acquire_sparse_variable_graph_evidence_v1``, or
``run_variable_graph_context_v1``.  Exact dynamics are used only for the
already-frozen structural support descriptors and, after cap failure, by the
separately charged fallback authority.  Transition probabilities never enter
the statistical model.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import functools
import hashlib
import math
from typing import Any, Iterable, Mapping

import acfqp.sequential_bernoulli_acquisition_v1 as seq
import acfqp.variable_order_graph_rapm_v1 as graph
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.31.0"
PROFILE_KEY = "anytime_variable_order_graph_rapm_v0"
CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
PER_OBLIGATION_ALPHA = Fraction(1, 250_000)

DOMAIN_TAGS = {
    "row": "acfqp:anytime-variable-graph-prefix-row:v1",
    "evidence": "acfqp:anytime-variable-graph-prefix-evidence:v1",
    "checkpoint": "acfqp:anytime-variable-graph-checkpoint:v1",
    "counters": "acfqp:anytime-variable-graph-counters:v1",
    "result": "acfqp:anytime-variable-graph-result:v1",
    "verification": "acfqp:anytime-variable-graph-verification:v1",
}


class AnytimeVariableGraphInvariantViolation(ValueError):
    """A prefix, CS, program-generation, audit, or accounting invariant failed."""


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    raw_suffix: bytes = b"",
) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role].encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise AnytimeVariableGraphInvariantViolation(str(error)) from error
    body = domain + b"\x00" + encoded
    if raw_suffix:
        body += b"\x00" + raw_suffix
    return hashlib.sha256(body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise AnytimeVariableGraphInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def anytime_variable_graph_profile_v1(
) -> seq.SequentialBernoulliProfileV1:
    """Registered CS/calculation profile; stopping itself is plan-level."""

    return seq.SequentialBernoulliProfileV1(
        confidence_alpha=PER_OBLIGATION_ALPHA,
        target_half_width=Fraction(1, 140),
        checkpoints=CHECKPOINTS,
        boundary_grid_bits=24,
    )


def _seed_id(seed: int) -> str:
    return hashlib.sha256(
        b"acfqp:anytime-variable-graph-row-seed:v1\x00"
        + seed.to_bytes(8, "big")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class AnytimeVariableGraphPrefixRowV1:
    """One direct paired-seed prefix, never a slice of a full packed row."""

    context_id: str
    catalogue: graph.VariableGraphCatalogueV1
    action: tuple[int, int, int]
    atom_descriptors: tuple[graph.ObservedVariableGraphAtomV1, ...]
    sample_count: int
    random_word_count: int
    rejection_count: int
    ordinal_counts: tuple[int, ...]
    packed_ordinals: bytes
    packed_rejection_flags: bytes
    paired_seed_id: str
    direct_prefix_generation: bool = True
    full_row_materialized: bool = False

    def __post_init__(self) -> None:
        _cid(self.context_id, "prefix row context")
        _cid(self.paired_seed_id, "prefix row paired seed")
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
            or type(self.sample_count) is not int
            or not 0 < self.sample_count <= CHECKPOINTS[-1]
            or type(self.random_word_count) is not int
            or self.random_word_count < self.sample_count
            or type(self.rejection_count) is not int
            or self.rejection_count
            != self.random_word_count - self.sample_count
            or type(self.ordinal_counts) is not tuple
            or len(self.ordinal_counts) != atom_count
            or any(type(item) is not int or item < 0 for item in self.ordinal_counts)
            or sum(self.ordinal_counts) != self.sample_count
            or type(self.packed_ordinals) is not bytes
            or len(self.packed_ordinals)
            != math.ceil(3 * self.sample_count / 8)
            or type(self.packed_rejection_flags) is not bytes
            or len(self.packed_rejection_flags)
            != math.ceil(self.random_word_count / 8)
            or self.direct_prefix_generation is not True
            or self.full_row_materialized is not False
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "anytime graph prefix row is invalid"
            )
        decoded = graph._unpack_three_bit_ordinals(
            self.packed_ordinals,
            self.sample_count,
            atom_count,
        )
        replayed = [0] * atom_count
        for ordinal in decoded:
            replayed[ordinal] += 1
        if tuple(replayed) != self.ordinal_counts:
            raise AnytimeVariableGraphInvariantViolation(
                "prefix ordinal counts do not match raw transcript"
            )
        flags = graph._unpack_rejection_flags(
            self.packed_rejection_flags,
            self.random_word_count,
        )
        if sum(flags) != self.rejection_count:
            raise AnytimeVariableGraphInvariantViolation(
                "prefix rejection count does not match raw transcript"
            )

    @property
    def atom_count(self) -> int:
        return len(self.atom_descriptors)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.anytime_variable_graph_prefix_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "action": list(self.action),
            "atom_descriptors": [
                item.to_document() for item in self.atom_descriptors
            ],
            "sample_count": self.sample_count,
            "random_word_count": self.random_word_count,
            "rejection_count": self.rejection_count,
            "ordinal_counts": list(self.ordinal_counts),
            "packed_ordinals_sha256": hashlib.sha256(
                self.packed_ordinals
            ).hexdigest(),
            "packed_ordinals_byte_count": len(self.packed_ordinals),
            "packed_rejection_flags_sha256": hashlib.sha256(
                self.packed_rejection_flags
            ).hexdigest(),
            "packed_rejection_flags_byte_count": len(
                self.packed_rejection_flags
            ),
            "paired_seed_id": self.paired_seed_id,
            "prng_semantics_id": graph.REGISTERED_PRNG_SEMANTICS_ID,
            "direct_prefix_generation": True,
            "full_row_materialized": False,
        }

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


class _MutablePrefixStream:
    """Operational mutable stream; snapshots are immutable artifacts."""

    def __init__(
        self,
        context: graph.VariableOrderGraphContextV1,
        catalogue: graph.VariableGraphCatalogueV1,
        action: tuple[int, int, int],
    ) -> None:
        self.context = context
        self.catalogue = catalogue
        self.action = action
        exact_atoms = graph.RelationalGraphMergeKernelV2(context).atoms(
            catalogue.state,
            action,
        )
        # Exact probabilities are intentionally not copied or read.
        self.descriptors = tuple(
            graph.ObservedVariableGraphAtomV1(
                item.ordinal,
                item.next_state,
                item.normalized_reward,
                item.failure,
            )
            for item in exact_atoms
        )
        self.seed = graph._row_seed(context, catalogue, action)
        self.ordinals: list[int] = []
        self.rejection_flags: list[bool] = []
        self.counts = [0] * len(self.descriptors)
        self.random_word_index = 0

    def extend_to(self, target_draw_count: int) -> None:
        if (
            type(target_draw_count) is not int
            or target_draw_count < len(self.ordinals)
            or target_draw_count > CHECKPOINTS[-1]
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "prefix stream extension violates chronology or cap"
            )
        gamma = 0x9E3779B97F4A7C15
        while len(self.ordinals) < target_draw_count:
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

    def snapshot(self) -> AnytimeVariableGraphPrefixRowV1:
        return AnytimeVariableGraphPrefixRowV1(
            context_id=self.context.context_id,
            catalogue=self.catalogue,
            action=self.action,
            atom_descriptors=self.descriptors,
            sample_count=len(self.ordinals),
            random_word_count=self.random_word_index,
            rejection_count=self.random_word_index - len(self.ordinals),
            ordinal_counts=tuple(self.counts),
            packed_ordinals=graph._pack_three_bit_ordinals(self.ordinals),
            packed_rejection_flags=graph._pack_rejection_flags(
                self.rejection_flags
            ),
            paired_seed_id=_seed_id(self.seed),
        )


def verify_anytime_variable_graph_prefix_row_v1(
    context: graph.VariableOrderGraphContextV1,
    row: AnytimeVariableGraphPrefixRowV1,
) -> bool:
    """Replay a prefix directly from its seed; never construct the full row."""

    if (
        type(context) is not graph.VariableOrderGraphContextV1
        or type(row) is not AnytimeVariableGraphPrefixRowV1
        or row.context_id != context.context_id
    ):
        raise AnytimeVariableGraphInvariantViolation(
            "prefix replay binding is invalid"
        )
    stream = _MutablePrefixStream(context, row.catalogue, row.action)
    stream.extend_to(row.sample_count)
    expected = stream.snapshot()
    if (
        expected.row_id != row.row_id
        or expected.packed_ordinals != row.packed_ordinals
        or expected.packed_rejection_flags != row.packed_rejection_flags
    ):
        raise AnytimeVariableGraphInvariantViolation(
            "prefix row failed direct paired-seed replay"
        )
    return True


def _aggregate_event_subsets(
    context: graph.VariableOrderGraphContextV1,
    skeleton: graph.PortableRelationalSkeletonV1,
    row: AnytimeVariableGraphPrefixRowV1,
) -> tuple[frozenset[int], ...]:
    extras = tuple(
        item
        for item in graph.syntactic_portable_program_closure_v1()
        if item.context is graph.RelationalProgramContext.STATE
        and item.result_type
        in (
            graph.RelationalProgramType.INTEGER,
            graph.RelationalProgramType.SIGNATURE,
        )
        and item.program_id != skeleton.state_program.program_id
    )
    program_sets = ((skeleton.state_program,),) + tuple(
        (skeleton.state_program, item) for item in extras
    )
    subsets: set[frozenset[int]] = set()
    for programs in program_sets:
        grouped: dict[tuple[Any, ...], set[int]] = defaultdict(set)
        for atom in row.atom_descriptors:
            if atom.failure:
                destination = ("FAILURE",)
            elif row.catalogue.remaining_horizon == 1:
                destination = ("SAFE_TERMINAL",)
            else:
                state_ir = graph._target_state_ir(
                    context,
                    atom.next_state,
                    row.catalogue.remaining_horizon - 1,
                )
                destination = (
                    "ACTIVE",
                    *(
                        graph.evaluate_portable_state_program_v1(
                            program,
                            state_ir,
                        )
                        for program in programs
                    ),
                )
            grouped[destination].add(atom.ordinal)
        subsets.update(
            frozenset(ordinals)
            for ordinals in grouped.values()
            if 0 < len(ordinals) < row.atom_count
        )
    return tuple(
        sorted(subsets, key=lambda item: tuple(sorted(item)))
    )


@dataclass(frozen=True, slots=True)
class AnytimeVariableGraphEvidenceV1:
    context_id: str
    skeleton_id: str
    root_catalogue_id: str
    selected_root_actions: tuple[tuple[int, int, int], ...]
    root_rows: tuple[AnytimeVariableGraphPrefixRowV1, ...]
    continuation_catalogues: tuple[graph.VariableGraphCatalogueV1, ...]
    continuation_rows: tuple[AnytimeVariableGraphPrefixRowV1, ...]
    preregistered_aggregate_obligation_count: int
    checkpoint_draw_count_per_row: int
    root_selection_frozen_at_checkpoint: int = CHECKPOINTS[0]
    source_dynamics_rows_used: int = 0
    complete_target_closure_rows_used: int = 0
    full_v0066_evidence_constructor_calls: int = 0

    def __post_init__(self) -> None:
        _cid(self.context_id, "prefix evidence context")
        _cid(self.skeleton_id, "prefix evidence skeleton")
        _cid(self.root_catalogue_id, "prefix evidence root catalogue")
        rows = self.root_rows + self.continuation_rows
        if (
            type(self.selected_root_actions) is not tuple
            or not self.selected_root_actions
            or self.selected_root_actions
            != tuple(sorted(set(self.selected_root_actions)))
            or type(self.root_rows) is not tuple
            or len(self.root_rows) != 2
            or type(self.continuation_catalogues) is not tuple
            or not self.continuation_catalogues
            or type(self.continuation_rows) is not tuple
            or not self.continuation_rows
            or any(
                type(item) is not AnytimeVariableGraphPrefixRowV1
                or item.context_id != self.context_id
                for item in rows
            )
            or any(
                item.sample_count != self.checkpoint_draw_count_per_row
                for item in rows
            )
            or tuple(item.row_id for item in self.root_rows)
            != tuple(sorted({item.row_id for item in self.root_rows}))
            or tuple(item.row_id for item in self.continuation_rows)
            != tuple(sorted({item.row_id for item in self.continuation_rows}))
            or type(self.preregistered_aggregate_obligation_count) is not int
            or self.preregistered_aggregate_obligation_count <= 0
            or self.checkpoint_draw_count_per_row not in CHECKPOINTS
            or self.root_selection_frozen_at_checkpoint != CHECKPOINTS[0]
            or self.source_dynamics_rows_used != 0
            or self.complete_target_closure_rows_used != 0
            or self.full_v0066_evidence_constructor_calls != 0
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "anytime graph evidence is incomplete or leaked full data"
            )
        catalogue_ids = {
            item.catalogue_id for item in self.continuation_catalogues
        }
        if {
            item.catalogue.catalogue_id for item in self.continuation_rows
        } != catalogue_ids:
            raise AnytimeVariableGraphInvariantViolation(
                "prefix evidence does not cover its continuation catalogues"
            )
        rows_by_catalogue: dict[
            str,
            set[tuple[int, int, int]],
        ] = defaultdict(set)
        for row in self.continuation_rows:
            rows_by_catalogue[row.catalogue.catalogue_id].add(row.action)
        if any(
            rows_by_catalogue[item.catalogue_id] != set(item.actions)
            for item in self.continuation_catalogues
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "prefix continuation evidence omits a legal row"
            )

    @property
    def ground_row_count(self) -> int:
        return len(self.root_rows) + len(self.continuation_rows)

    @property
    def generative_draw_count(self) -> int:
        return sum(
            item.sample_count
            for item in self.root_rows + self.continuation_rows
        )

    @property
    def exact_local_support_row_count(self) -> int:
        return self.ground_row_count

    @property
    def random_word_count(self) -> int:
        return sum(
            item.random_word_count
            for item in self.root_rows + self.continuation_rows
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.anytime_variable_graph_prefix_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "skeleton_id": self.skeleton_id,
            "root_catalogue_id": self.root_catalogue_id,
            "selected_root_actions": [
                list(item) for item in self.selected_root_actions
            ],
            "root_row_ids": [item.row_id for item in self.root_rows],
            "continuation_catalogue_ids": [
                item.catalogue_id for item in self.continuation_catalogues
            ],
            "continuation_row_ids": [
                item.row_id for item in self.continuation_rows
            ],
            "preregistered_aggregate_obligation_count": (
                self.preregistered_aggregate_obligation_count
            ),
            "checkpoint_draw_count_per_row": (
                self.checkpoint_draw_count_per_row
            ),
            "root_selection_frozen_at_checkpoint": CHECKPOINTS[0],
            "ground_row_count": self.ground_row_count,
            "generative_draw_count": self.generative_draw_count,
            "exact_local_support_row_count": self.exact_local_support_row_count,
            "random_word_count": self.random_word_count,
            "source_dynamics_rows_used": 0,
            "complete_target_closure_rows_used": 0,
            "full_v0066_evidence_constructor_calls": 0,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())


def _root_action_selection(
    context: graph.VariableOrderGraphContextV1,
    skeleton: graph.PortableRelationalSkeletonV1,
    root_rows: tuple[AnytimeVariableGraphPrefixRowV1, ...],
    profile: seq.SequentialBernoulliProfileV1,
) -> tuple[tuple[int, int, int], ...]:
    grouped: dict[
        tuple[tuple[str, Any], ...],
        list[tuple[tuple[int, int, int], Fraction]],
    ] = defaultdict(list)
    for row in root_rows:
        state_ir = graph._target_state_ir(
            context,
            row.catalogue.state,
            row.catalogue.remaining_horizon,
        )
        coordinate = (
            graph.evaluate_portable_action_program_v1(
                skeleton.action_program,
                state_ir,
                graph._profile_action_slot(state_ir, row.action),
            ),
        )
        failure_ordinals = frozenset(
            atom.ordinal for atom in row.atom_descriptors if atom.failure
        )
        if not failure_ordinals:
            failure_upper = Fraction(0)
        elif len(failure_ordinals) == row.atom_count:
            failure_upper = Fraction(1)
        else:
            failures = sum(
                row.ordinal_counts[item] for item in failure_ordinals
            )
            failure_upper = (
                seq.build_anytime_bernoulli_checkpoint_v1(
                    row.sample_count,
                    failures,
                    profile,
                ).upper_probability
            )
        grouped[coordinate].append((row.action, failure_upper))
    summaries = tuple(
        (
            coordinate,
            tuple(sorted(action for action, _ in members)),
            sum((upper for _, upper in members), Fraction(0))
            / len(members),
        )
        for coordinate, members in grouped.items()
    )
    return min(
        summaries,
        key=lambda item: (item[2], repr(item[0])),
    )[1]


def _snapshot_evidence(
    context: graph.VariableOrderGraphContextV1,
    skeleton: graph.PortableRelationalSkeletonV1,
    root_catalogue: graph.VariableGraphCatalogueV1,
    selected_root_actions: tuple[tuple[int, int, int], ...],
    streams: Mapping[
        tuple[str, tuple[int, int, int]],
        _MutablePrefixStream,
    ],
    continuation_catalogues: tuple[graph.VariableGraphCatalogueV1, ...],
    checkpoint: int,
) -> AnytimeVariableGraphEvidenceV1:
    root_rows = tuple(
        sorted(
            (
                streams[(root_catalogue.catalogue_id, action)].snapshot()
                for action in root_catalogue.actions
            ),
            key=lambda item: item.row_id,
        )
    )
    continuation_rows = tuple(
        sorted(
            (
                streams[(catalogue.catalogue_id, action)].snapshot()
                for catalogue in continuation_catalogues
                for action in catalogue.actions
            ),
            key=lambda item: item.row_id,
        )
    )
    obligations = sum(
        len(_aggregate_event_subsets(context, skeleton, row))
        for row in root_rows + continuation_rows
    )
    return AnytimeVariableGraphEvidenceV1(
        context_id=context.context_id,
        skeleton_id=skeleton.skeleton_id,
        root_catalogue_id=root_catalogue.catalogue_id,
        selected_root_actions=selected_root_actions,
        root_rows=root_rows,
        continuation_catalogues=continuation_catalogues,
        continuation_rows=continuation_rows,
        preregistered_aggregate_obligation_count=obligations,
        checkpoint_draw_count_per_row=checkpoint,
    )


def _confidence_checkpoints(
    context: graph.VariableOrderGraphContextV1,
    skeleton: graph.PortableRelationalSkeletonV1,
    evidence: AnytimeVariableGraphEvidenceV1,
    profile: seq.SequentialBernoulliProfileV1,
) -> tuple[
    dict[
        tuple[str, tuple[int, int, int]],
        dict[frozenset[int], seq.AnytimeBernoulliCheckpointV1],
    ],
    int,
    Fraction,
]:
    cache: dict[
        tuple[int, int],
        seq.AnytimeBernoulliCheckpointV1,
    ] = {}
    result: dict[
        tuple[str, tuple[int, int, int]],
        dict[frozenset[int], seq.AnytimeBernoulliCheckpointV1],
    ] = {}
    evaluation_count = 0
    max_width = Fraction(0)
    for row in evidence.root_rows + evidence.continuation_rows:
        events: dict[
            frozenset[int],
            seq.AnytimeBernoulliCheckpointV1,
        ] = {}
        for subset in _aggregate_event_subsets(context, skeleton, row):
            count = sum(row.ordinal_counts[item] for item in subset)
            key = (row.sample_count, count)
            checkpoint = cache.get(key)
            if checkpoint is None:
                checkpoint = seq.build_anytime_bernoulli_checkpoint_v1(
                    row.sample_count,
                    count,
                    profile,
                )
                cache[key] = checkpoint
            events[subset] = checkpoint
            evaluation_count += 1
            max_width = max(max_width, checkpoint.interval_width)
        result[(row.catalogue.catalogue_id, row.action)] = events
    if evaluation_count != evidence.preregistered_aggregate_obligation_count:
        raise AnytimeVariableGraphInvariantViolation(
            "aggregate confidence family is incomplete"
        )
    return result, evaluation_count, max_width


def _build_sequential_model(
    context: graph.VariableOrderGraphContextV1,
    skeleton: graph.PortableRelationalSkeletonV1,
    coordinate_profile: graph.PortableGraphCoordinateProfileV1,
    evidence: AnytimeVariableGraphEvidenceV1,
    confidence: Mapping[
        tuple[str, tuple[int, int, int]],
        Mapping[frozenset[int], seq.AnytimeBernoulliCheckpointV1],
    ],
) -> graph.PartialStatisticalRAPMV1:
    groups: dict[
        str,
        tuple[
            tuple[int, graph.TaggedCoordinate, graph.TaggedCoordinate],
            list[
                tuple[
                    AnytimeVariableGraphPrefixRowV1,
                    dict[
                        graph.DestinationKey,
                        tuple[Fraction, Fraction],
                    ],
                    Fraction,
                ]
            ],
        ],
    ] = {}
    for row in evidence.root_rows + evidence.continuation_rows:
        support = graph._support_key(
            coordinate_profile,
            context,
            row.catalogue,
            row.action,
        )
        ordinals: dict[graph.DestinationKey, set[int]] = defaultdict(set)
        for atom in row.atom_descriptors:
            ordinals[
                graph._atom_destination(
                    coordinate_profile,
                    context,
                    row.catalogue.remaining_horizon,
                    atom,
                )
            ].add(atom.ordinal)
        bounds: dict[
            graph.DestinationKey,
            tuple[Fraction, Fraction],
        ] = {}
        event_map = confidence[(row.catalogue.catalogue_id, row.action)]
        for destination, destination_ordinals in ordinals.items():
            subset = frozenset(destination_ordinals)
            if len(subset) == row.atom_count:
                bounds[destination] = (Fraction(1), Fraction(1))
            else:
                checkpoint = event_map.get(subset)
                if checkpoint is None:
                    raise AnytimeVariableGraphInvariantViolation(
                        "model requested an unregistered destination event"
                    )
                bounds[destination] = (
                    checkpoint.lower_probability,
                    checkpoint.upper_probability,
                )
        rewards = {
            atom.normalized_reward for atom in row.atom_descriptors
        }
        if len(rewards) != 1:
            raise AnytimeVariableGraphInvariantViolation(
                "prefix support has nondeterministic immediate reward"
            )
        reward = next(iter(rewards))
        key = repr(support)
        prior = groups.get(key)
        if prior is None:
            groups[key] = (support, [(row, bounds, reward)])
        else:
            if prior[0] != support:
                raise AssertionError("support repr collision")
            prior[1].append((row, bounds, reward))

    model_rows: list[graph.PartialRAPMRowV1] = []
    for key in sorted(groups):
        support, members = groups[key]
        destinations = {
            destination
            for _, bounds, _ in members
            for destination in bounds
        }
        intervals = tuple(
            graph.StatisticalDestinationIntervalV1(
                destination,
                min(
                    bounds.get(
                        destination,
                        (Fraction(0), Fraction(0)),
                    )[0]
                    for _, bounds, _ in members
                ),
                max(
                    bounds.get(
                        destination,
                        (Fraction(0), Fraction(0)),
                    )[1]
                    for _, bounds, _ in members
                ),
            )
            for destination in sorted(destinations, key=repr)
        )
        model_rows.append(
            graph.PartialRAPMRowV1(
                support_key=support,
                intervals=intervals,
                reward_lower=min(reward for _, _, reward in members),
                reward_upper=max(reward for _, _, reward in members),
                ground_row_ids=tuple(
                    sorted(row.row_id for row, _, _ in members)
                ),
            )
        )
    return graph.PartialStatisticalRAPMV1(
        context_id=context.context_id,
        skeleton_id=skeleton.skeleton_id,
        profile_id=coordinate_profile.profile_id,
        evidence_id=evidence.evidence_id,
        epoch_index=1 + coordinate_profile.refinement_index,
        rows=tuple(model_rows),
        known_ground_row_count=evidence.ground_row_count,
        exact_local_support_rows_used=evidence.ground_row_count,
    )


def _prefix_target_log(
    context: graph.VariableOrderGraphContextV1,
    evidence: AnytimeVariableGraphEvidenceV1,
) -> graph.AnonymousRelationalObservationLogV1:
    rows: list[graph.RelationalObservedRowV1] = []
    for row in evidence.root_rows + evidence.continuation_rows:
        state = graph._target_state_ir(
            context,
            row.catalogue.state,
            row.catalogue.remaining_horizon,
        )
        slots = {
            item.opaque_action_key: item for item in state.legal_actions
        }
        outcomes = graph._canonical_relational_outcomes(
            (
                (
                    graph._target_state_ir(
                        context,
                        atom.next_state,
                        row.catalogue.remaining_horizon - 1,
                    ),
                    Fraction(
                        row.ordinal_counts[atom.ordinal],
                        row.sample_count,
                    ),
                    atom.normalized_reward,
                    atom.failure,
                    atom.failure
                    or row.catalogue.remaining_horizon == 1,
                )
                for atom in row.atom_descriptors
                if row.ordinal_counts[atom.ordinal] > 0
            )
        )
        rows.append(
            graph.RelationalObservedRowV1(
                state,
                slots[graph._action_key(row.action)],
                outcomes,
            )
        )
    return graph.AnonymousRelationalObservationLogV1(
        graph.PortableRelationalRoleSchemaV1(),
        tuple(sorted(rows, key=lambda item: item.observed_row_id)),
    )


def _generate_prefix_refinement(
    context: graph.VariableOrderGraphContextV1,
    skeleton: graph.PortableRelationalSkeletonV1,
    base_profile: graph.PortableGraphCoordinateProfileV1,
    base_model: graph.PartialStatisticalRAPMV1,
    base_audit: graph.PortableGraphAuditV1,
    evidence: AnytimeVariableGraphEvidenceV1,
    confidence: Mapping[
        tuple[str, tuple[int, int, int]],
        Mapping[frozenset[int], seq.AnytimeBernoulliCheckpointV1],
    ],
) -> tuple[
    graph.TargetGraphProgramTraceV1,
    graph.PortableGraphCoordinateProfileV1 | None,
    graph.PartialStatisticalRAPMV1 | None,
    graph.PortableGraphAuditV1 | None,
    str,
]:
    target_log = _prefix_target_log(context, evidence)
    failed_proof = graph.FailedRelationalProofRefV1(
        context.context_id,
        base_model.model_id,
        base_audit.audit_id,
        "ALIAS_WIDTH",
    )
    generation = graph.generate_target_relational_programs_v1(
        skeleton,
        failed_proof,
        target_log,
    )
    state_extras, action_extras = graph._fresh_refinement_programs(
        skeleton,
        generation,
    )
    candidate_inputs = (
        [(item, None) for item in state_extras]
        + [(None, item) for item in action_extras]
        + [
            (state_extra, action_extra)
            for state_extra in state_extras
            for action_extra in action_extras
        ]
    )
    evaluated: list[
        tuple[
            graph.GraphRefinementCandidateV1,
            graph.PortableGraphCoordinateProfileV1,
            graph.PartialStatisticalRAPMV1,
            graph.PortableGraphAuditV1,
        ]
    ] = []
    for state_extra, action_extra in candidate_inputs:
        coordinate_profile = graph.PortableGraphCoordinateProfileV1(
            skeleton.skeleton_id,
            (skeleton.state_program,)
            + (() if state_extra is None else (state_extra,)),
            (skeleton.action_program,)
            + (() if action_extra is None else (action_extra,)),
            1,
            generation.generation_id,
            base_audit.audit_id,
        )
        model = _build_sequential_model(
            context,
            skeleton,
            coordinate_profile,
            evidence,
            confidence,
        )
        audit = graph.audit_partial_statistical_rapm_v1(
            context,
            coordinate_profile,
            model,
            evidence,  # duck-typed prefix authority
        )
        node_count = (
            0 if state_extra is None else state_extra.node_count
        ) + (
            0 if action_extra is None else action_extra.node_count
        )
        evaluated.append(
            (
                graph.GraphRefinementCandidateV1(
                    state_extra,
                    action_extra,
                    coordinate_profile.profile_id,
                    model.model_id,
                    audit.audit_id,
                    audit.outcome,
                    audit.failure_upper,
                    len(model.rows),
                    node_count,
                ),
                coordinate_profile,
                model,
                audit,
            )
        )
    if not evaluated:
        raise AnytimeVariableGraphInvariantViolation(
            "prefix target grammar generated no refinement candidates"
        )
    certified = tuple(
        item
        for item in evaluated
        if item[3].outcome
        is graph.PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
    )
    selected = (
        None
        if not certified
        else min(
            certified,
            key=lambda item: (
                item[0].added_node_count,
                item[0].abstract_support_count,
                item[0].profile_id,
            ),
        )
    )
    summaries = tuple(
        sorted((item[0] for item in evaluated), key=lambda item: item.profile_id)
    )
    selected_rendered = None
    if selected is not None:
        extras = tuple(
            item
            for item in (
                selected[0].state_extra,
                selected[0].action_extra,
            )
            if item is not None
        )
        selected_rendered = " + ".join(
            item.rendered for item in extras
        )
    trace = graph.TargetGraphProgramTraceV1(
        context.context_id,
        base_audit.audit_id,
        generation,
        summaries,
        None if selected is None else selected[1].profile_id,
        selected_rendered,
        selected is not None,
        min(item.failure_upper for item in summaries),
    )
    if selected is None:
        return (
            trace,
            None,
            None,
            None,
            target_log.observation_log_id,
        )
    return (
        trace,
        selected[1],
        selected[2],
        selected[3],
        target_log.observation_log_id,
    )


@dataclass(frozen=True, slots=True)
class AnytimeVariableGraphCheckpointV1:
    context_id: str
    checkpoint_draw_count_per_row: int
    evidence_id: str
    ground_row_count: int
    target_draw_count: int
    aggregate_obligation_count: int
    aggregate_cs_evaluation_count: int
    maximum_aggregate_interval_width: Fraction
    base_model_id: str
    base_audit_id: str
    base_outcome: graph.PortableGraphAuditOutcome
    prefix_target_log_id: str | None
    program_trace: graph.TargetGraphProgramTraceV1 | None
    final_profile_id: str
    final_model_id: str
    final_audit_id: str
    final_outcome: graph.PortableGraphAuditOutcome
    plan_certified: bool
    full_data_profile_reused: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "checkpoint context"),
            (self.evidence_id, "checkpoint evidence"),
            (self.base_model_id, "checkpoint base model"),
            (self.base_audit_id, "checkpoint base audit"),
            (self.final_profile_id, "checkpoint final profile"),
            (self.final_model_id, "checkpoint final model"),
            (self.final_audit_id, "checkpoint final audit"),
        ):
            _cid(value, field)
        if self.prefix_target_log_id is not None:
            _cid(self.prefix_target_log_id, "checkpoint target log")
        if (
            self.checkpoint_draw_count_per_row not in CHECKPOINTS
            or type(self.ground_row_count) is not int
            or self.ground_row_count <= 0
            or self.target_draw_count
            != self.ground_row_count * self.checkpoint_draw_count_per_row
            or self.aggregate_obligation_count <= 0
            or self.aggregate_cs_evaluation_count
            != self.aggregate_obligation_count
            or type(self.maximum_aggregate_interval_width) is not Fraction
            or not 0 <= self.maximum_aggregate_interval_width <= 1
            or type(self.base_outcome) is not graph.PortableGraphAuditOutcome
            or type(self.final_outcome) is not graph.PortableGraphAuditOutcome
            or type(self.plan_certified) is not bool
            or self.plan_certified
            != (
                self.final_outcome
                is graph.PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
            )
            or self.full_data_profile_reused is not False
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "anytime graph checkpoint is inconsistent"
            )
        if self.program_trace is None:
            if self.prefix_target_log_id is not None:
                raise AnytimeVariableGraphInvariantViolation(
                    "checkpoint has a target log without program trace"
                )
        elif (
            self.program_trace.context_id != self.context_id
            or self.program_trace.generation.target_observation_log_id
            != self.prefix_target_log_id
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "program trace is not generated from this prefix target log"
            )

    @property
    def candidate_evaluation_count(self) -> int:
        return (
            0 if self.program_trace is None else self.program_trace.candidate_count
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.anytime_variable_graph_checkpoint.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "checkpoint_draw_count_per_row": (
                self.checkpoint_draw_count_per_row
            ),
            "evidence_id": self.evidence_id,
            "ground_row_count": self.ground_row_count,
            "target_draw_count": self.target_draw_count,
            "aggregate_obligation_count": self.aggregate_obligation_count,
            "aggregate_cs_evaluation_count": (
                self.aggregate_cs_evaluation_count
            ),
            "maximum_aggregate_interval_width": _fdoc(
                self.maximum_aggregate_interval_width
            ),
            "base_model_id": self.base_model_id,
            "base_audit_id": self.base_audit_id,
            "base_outcome": self.base_outcome.value,
            "prefix_target_log_id": self.prefix_target_log_id,
            "program_trace_id": (
                None
                if self.program_trace is None
                else self.program_trace.trace_id
            ),
            "candidate_evaluation_count": self.candidate_evaluation_count,
            "final_profile_id": self.final_profile_id,
            "final_model_id": self.final_model_id,
            "final_audit_id": self.final_audit_id,
            "final_outcome": self.final_outcome.value,
            "plan_certified": self.plan_certified,
            "full_data_profile_reused": False,
        }

    @property
    def checkpoint_id(self) -> str:
        return _content_id("checkpoint", self._payload())


@dataclass(frozen=True, slots=True)
class AnytimeVariableGraphCountersV1:
    target_ordinal_draws: int
    target_random_word_calls: int
    target_ground_rows: int
    structural_support_kernel_calls: int
    operational_exact_kernel_queries: int
    checkpoint_model_audits: int
    aggregate_cs_evaluations: int
    target_program_generations: int
    target_candidate_evaluations: int
    fallback_exact_ground_rows: int
    full_131072_rows_materialized: int = 0
    v0066_full_evidence_constructor_calls: int = 0
    v0066_full_profile_reads: int = 0

    def __post_init__(self) -> None:
        charged = (
            self.target_ordinal_draws,
            self.target_random_word_calls,
            self.target_ground_rows,
            self.structural_support_kernel_calls,
            self.operational_exact_kernel_queries,
            self.checkpoint_model_audits,
            self.aggregate_cs_evaluations,
            self.target_program_generations,
            self.target_candidate_evaluations,
            self.fallback_exact_ground_rows,
        )
        if (
            any(type(item) is not int or item < 0 for item in charged)
            or self.target_ordinal_draws <= 0
            or self.target_random_word_calls < self.target_ordinal_draws
            or self.target_ground_rows <= 0
            or self.structural_support_kernel_calls
            != self.target_ground_rows
            or self.operational_exact_kernel_queries
            != (
                self.structural_support_kernel_calls
                + self.fallback_exact_ground_rows
            )
            or self.checkpoint_model_audits <= 0
            or self.aggregate_cs_evaluations <= 0
            or self.full_131072_rows_materialized != 0
            or self.v0066_full_evidence_constructor_calls != 0
            or self.v0066_full_profile_reads != 0
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "anytime graph native counters are invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.anytime_variable_graph_counters.v1",
            "schema_version": SCHEMA_VERSION,
            "target_ordinal_draws": self.target_ordinal_draws,
            "target_random_word_calls": self.target_random_word_calls,
            "target_ground_rows": self.target_ground_rows,
            "structural_support_kernel_calls": (
                self.structural_support_kernel_calls
            ),
            "operational_exact_kernel_queries": (
                self.operational_exact_kernel_queries
            ),
            "operational_exact_probability_reads": 0,
            "checkpoint_model_audits": self.checkpoint_model_audits,
            "aggregate_cs_evaluations": self.aggregate_cs_evaluations,
            "target_program_generations": self.target_program_generations,
            "target_candidate_evaluations": self.target_candidate_evaluations,
            "fallback_exact_ground_rows": self.fallback_exact_ground_rows,
            "full_131072_rows_materialized": 0,
            "v0066_full_evidence_constructor_calls": 0,
            "v0066_full_profile_reads": 0,
        }

    @property
    def counters_id(self) -> str:
        return _content_id("counters", self._payload())


class AnytimeVariableGraphTerminal(str, Enum):
    CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE = (
        "CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE"
    )
    FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP = (
        "FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP"
    )


@dataclass(frozen=True, slots=True)
class AnytimeVariableGraphResultV1:
    context: graph.VariableOrderGraphContextV1
    sequential_profile: seq.SequentialBernoulliProfileV1
    checkpoints: tuple[AnytimeVariableGraphCheckpointV1, ...]
    final_evidence: AnytimeVariableGraphEvidenceV1
    base_profile: graph.PortableGraphCoordinateProfileV1
    base_model: graph.PartialStatisticalRAPMV1
    base_audit: graph.PortableGraphAuditV1
    program_trace: graph.TargetGraphProgramTraceV1 | None
    final_profile: graph.PortableGraphCoordinateProfileV1
    final_model: graph.PartialStatisticalRAPMV1
    final_audit: graph.PortableGraphAuditV1
    fallback_proof: graph.ExactGroundFallbackProofV1 | None
    terminal: AnytimeVariableGraphTerminal
    counters: AnytimeVariableGraphCountersV1
    conditional_family_tail_upper: Fraction
    first_certificate_stopping: bool = True
    target_local_intervals_only: bool = True
    exact_fallback_separately_charged: bool = True
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.context) is not graph.VariableOrderGraphContextV1
            or type(self.sequential_profile)
            is not seq.SequentialBernoulliProfileV1
            or type(self.checkpoints) is not tuple
            or not self.checkpoints
            or any(
                type(item) is not AnytimeVariableGraphCheckpointV1
                for item in self.checkpoints
            )
            or tuple(
                item.checkpoint_draw_count_per_row
                for item in self.checkpoints
            )
            != CHECKPOINTS[: len(self.checkpoints)]
            or any(
                item.context_id != self.context.context_id
                for item in self.checkpoints
            )
            or type(self.final_evidence)
            is not AnytimeVariableGraphEvidenceV1
            or self.final_evidence.evidence_id
            != self.checkpoints[-1].evidence_id
            or type(self.base_profile)
            is not graph.PortableGraphCoordinateProfileV1
            or type(self.base_model) is not graph.PartialStatisticalRAPMV1
            or type(self.base_audit) is not graph.PortableGraphAuditV1
            or type(self.final_profile)
            is not graph.PortableGraphCoordinateProfileV1
            or type(self.final_model) is not graph.PartialStatisticalRAPMV1
            or type(self.final_audit) is not graph.PortableGraphAuditV1
            or self.final_audit.audit_id
            != self.checkpoints[-1].final_audit_id
            or type(self.terminal) is not AnytimeVariableGraphTerminal
            or type(self.counters) is not AnytimeVariableGraphCountersV1
            or self.conditional_family_tail_upper
            != self.final_evidence.preregistered_aggregate_obligation_count
            * self.sequential_profile.confidence_alpha
            or self.conditional_family_tail_upper >= 1
            or self.first_certificate_stopping is not True
            or self.target_local_intervals_only is not True
            or self.exact_fallback_separately_charged is not True
            or self.sample_efficiency_claimed is not False
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "anytime graph result identity, chronology, or claims changed"
            )
        if any(item.plan_certified for item in self.checkpoints[:-1]):
            raise AnytimeVariableGraphInvariantViolation(
                "runner continued after its first plan certificate"
            )
        final_certified = self.checkpoints[-1].plan_certified
        if final_certified:
            if (
                self.terminal
                is not AnytimeVariableGraphTerminal.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
                or self.fallback_proof is not None
                or self.counters.fallback_exact_ground_rows != 0
            ):
                raise AnytimeVariableGraphInvariantViolation(
                    "certified prefix incorrectly used fallback"
                )
        elif (
            self.checkpoints[-1].checkpoint_draw_count_per_row
            != CHECKPOINTS[-1]
            or self.terminal
            is not AnytimeVariableGraphTerminal.FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP
            or type(self.fallback_proof)
            is not graph.ExactGroundFallbackProofV1
            or self.fallback_proof.failed_audit_id
            != self.final_audit.audit_id
            or self.counters.fallback_exact_ground_rows
            != self.fallback_proof.evaluated_state_action_rows
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "cap failure lacks separately charged exact fallback"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.anytime_variable_graph_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context.context_id,
            "sequential_profile_id": self.sequential_profile.profile_id,
            "checkpoint_ids": [
                item.checkpoint_id for item in self.checkpoints
            ],
            "final_evidence_id": self.final_evidence.evidence_id,
            "base_profile_id": self.base_profile.profile_id,
            "base_model_id": self.base_model.model_id,
            "base_audit_id": self.base_audit.audit_id,
            "program_trace_id": (
                None
                if self.program_trace is None
                else self.program_trace.trace_id
            ),
            "final_profile_id": self.final_profile.profile_id,
            "final_model_id": self.final_model.model_id,
            "final_audit_id": self.final_audit.audit_id,
            "fallback_proof_id": (
                None
                if self.fallback_proof is None
                else self.fallback_proof.proof_id
            ),
            "terminal": self.terminal.value,
            "counters_id": self.counters.counters_id,
            "conditional_family_tail_upper": _fdoc(
                self.conditional_family_tail_upper
            ),
            "first_certificate_stopping": True,
            "target_local_intervals_only": True,
            "exact_fallback_separately_charged": True,
            "sample_efficiency_claimed": False,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())


@functools.lru_cache(maxsize=3)
def run_anytime_variable_graph_context_v1(
    context: graph.VariableOrderGraphContextV1,
    skeleton: graph.PortableRelationalSkeletonV1,
) -> AnytimeVariableGraphResultV1:
    """Run one registered context without constructing any full V0-066 row."""

    if (
        type(context) is not graph.VariableOrderGraphContextV1
        or context not in graph.registered_variable_order_contexts_v1()
        or type(skeleton) is not graph.PortableRelationalSkeletonV1
    ):
        raise AnytimeVariableGraphInvariantViolation(
            "anytime graph runner requires registered context and skeleton"
        )
    cs_profile = anytime_variable_graph_profile_v1()
    kernel = graph.RelationalGraphMergeKernelV2(context)
    root_catalogue = graph._catalogue(
        context,
        kernel.root_state(),
        graph.HORIZON,
    )
    streams: dict[
        tuple[str, tuple[int, int, int]],
        _MutablePrefixStream,
    ] = {
        (root_catalogue.catalogue_id, action): _MutablePrefixStream(
            context,
            root_catalogue,
            action,
        )
        for action in root_catalogue.actions
    }
    checkpoint_artifacts: list[AnytimeVariableGraphCheckpointV1] = []
    final_objects: tuple[
        AnytimeVariableGraphEvidenceV1,
        graph.PortableGraphCoordinateProfileV1,
        graph.PartialStatisticalRAPMV1,
        graph.PortableGraphAuditV1,
        graph.TargetGraphProgramTraceV1 | None,
        graph.PortableGraphCoordinateProfileV1,
        graph.PartialStatisticalRAPMV1,
        graph.PortableGraphAuditV1,
    ] | None = None
    selected_continuation_catalogues: tuple[
        graph.VariableGraphCatalogueV1,
        ...,
    ] = ()
    frozen_root_actions: tuple[tuple[int, int, int], ...] | None = None

    for checkpoint in CHECKPOINTS:
        for action in root_catalogue.actions:
            streams[(root_catalogue.catalogue_id, action)].extend_to(
                checkpoint
            )
        root_rows = tuple(
            sorted(
                (
                    streams[
                        (root_catalogue.catalogue_id, action)
                    ].snapshot()
                    for action in root_catalogue.actions
                ),
                key=lambda item: item.row_id,
            )
        )
        if frozen_root_actions is None:
            frozen_root_actions = _root_action_selection(
                context,
                skeleton,
                root_rows,
                cs_profile,
            )
        selected_root_actions = frozen_root_actions
        successors = {
            atom.next_state
            for row in root_rows
            if row.action in selected_root_actions
            for atom in row.atom_descriptors
            if not atom.failure
        }
        selected_continuation_catalogues = tuple(
            sorted(
                (
                    graph._catalogue(context, state, 1)
                    for state in successors
                ),
                key=lambda item: item.catalogue_id,
            )
        )
        for catalogue in selected_continuation_catalogues:
            for action in catalogue.actions:
                key = (catalogue.catalogue_id, action)
                if key not in streams:
                    streams[key] = _MutablePrefixStream(
                        context,
                        catalogue,
                        action,
                    )
                streams[key].extend_to(checkpoint)

        evidence = _snapshot_evidence(
            context,
            skeleton,
            root_catalogue,
            selected_root_actions,
            streams,
            selected_continuation_catalogues,
            checkpoint,
        )
        confidence, cs_evaluations, max_width = _confidence_checkpoints(
            context,
            skeleton,
            evidence,
            cs_profile,
        )
        base_profile = graph._base_coordinate_profile(skeleton)
        base_model = _build_sequential_model(
            context,
            skeleton,
            base_profile,
            evidence,
            confidence,
        )
        base_audit = graph.audit_partial_statistical_rapm_v1(
            context,
            base_profile,
            base_model,
            evidence,  # duck-typed prefix authority
        )
        trace: graph.TargetGraphProgramTraceV1 | None = None
        prefix_target_log_id: str | None = None
        final_profile = base_profile
        final_model = base_model
        final_audit = base_audit
        if (
            base_audit.outcome
            is graph.PortableGraphAuditOutcome.FAILED_RISK_OR_ALIAS
        ):
            (
                trace,
                proposed_profile,
                proposed_model,
                proposed_audit,
                prefix_target_log_id,
            ) = _generate_prefix_refinement(
                context,
                skeleton,
                base_profile,
                base_model,
                base_audit,
                evidence,
                confidence,
            )
            if proposed_profile is not None:
                final_profile = proposed_profile
                if proposed_model is None or proposed_audit is None:
                    raise AssertionError("partial prefix proposal")
                final_model = proposed_model
                final_audit = proposed_audit
        certified = (
            final_audit.outcome
            is graph.PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
        )
        checkpoint_artifacts.append(
            AnytimeVariableGraphCheckpointV1(
                context_id=context.context_id,
                checkpoint_draw_count_per_row=checkpoint,
                evidence_id=evidence.evidence_id,
                ground_row_count=evidence.ground_row_count,
                target_draw_count=evidence.generative_draw_count,
                aggregate_obligation_count=(
                    evidence.preregistered_aggregate_obligation_count
                ),
                aggregate_cs_evaluation_count=cs_evaluations,
                maximum_aggregate_interval_width=max_width,
                base_model_id=base_model.model_id,
                base_audit_id=base_audit.audit_id,
                base_outcome=base_audit.outcome,
                prefix_target_log_id=prefix_target_log_id,
                program_trace=trace,
                final_profile_id=final_profile.profile_id,
                final_model_id=final_model.model_id,
                final_audit_id=final_audit.audit_id,
                final_outcome=final_audit.outcome,
                plan_certified=certified,
            )
        )
        final_objects = (
            evidence,
            base_profile,
            base_model,
            base_audit,
            trace,
            final_profile,
            final_model,
            final_audit,
        )
        if certified:
            break

    if final_objects is None:  # pragma: no cover
        raise AssertionError("registered checkpoint family is empty")
    (
        final_evidence,
        base_profile,
        base_model,
        base_audit,
        trace,
        final_profile,
        final_model,
        final_audit,
    ) = final_objects
    fallback = (
        None
        if final_audit.outcome
        is graph.PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
        else graph.execute_exact_ground_fallback_v1(
            context,
            final_audit,
        )
    )
    active_streams = tuple(
        streams[(row.catalogue.catalogue_id, row.action)]
        for row in (
            final_evidence.root_rows
            + final_evidence.continuation_rows
        )
    )
    counters = AnytimeVariableGraphCountersV1(
        target_ordinal_draws=sum(
            len(item.ordinals) for item in active_streams
        ),
        target_random_word_calls=sum(
            item.random_word_index for item in active_streams
        ),
        target_ground_rows=len(active_streams),
        structural_support_kernel_calls=len(active_streams),
        operational_exact_kernel_queries=(
            len(active_streams)
            + (
                0
                if fallback is None
                else fallback.evaluated_state_action_rows
            )
        ),
        checkpoint_model_audits=len(checkpoint_artifacts),
        aggregate_cs_evaluations=sum(
            item.aggregate_cs_evaluation_count
            for item in checkpoint_artifacts
        ),
        target_program_generations=sum(
            item.program_trace is not None
            for item in checkpoint_artifacts
        ),
        target_candidate_evaluations=sum(
            item.candidate_evaluation_count
            for item in checkpoint_artifacts
        ),
        fallback_exact_ground_rows=(
            0 if fallback is None else fallback.evaluated_state_action_rows
        ),
    )
    return AnytimeVariableGraphResultV1(
        context=context,
        sequential_profile=cs_profile,
        checkpoints=tuple(checkpoint_artifacts),
        final_evidence=final_evidence,
        base_profile=base_profile,
        base_model=base_model,
        base_audit=base_audit,
        program_trace=trace,
        final_profile=final_profile,
        final_model=final_model,
        final_audit=final_audit,
        fallback_proof=fallback,
        terminal=(
            AnytimeVariableGraphTerminal.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
            if fallback is None
            else AnytimeVariableGraphTerminal.FULL_GROUND_FALLBACK_AFTER_SEQUENTIAL_CAP
        ),
        counters=counters,
        conditional_family_tail_upper=(
            final_evidence.preregistered_aggregate_obligation_count
            * cs_profile.confidence_alpha
        ),
    )


@dataclass(frozen=True, slots=True)
class AnytimeVariableGraphVerificationV1:
    result_id: str
    context_id: str
    replayed_prefix_rows: int
    replayed_ordinal_draws: int
    replayed_structural_support_kernel_calls: int
    verified_operational_exact_kernel_queries: int
    actual_verifier_exact_kernel_queries: int
    paired_seed_replay_passed: bool
    prefix_generated_refinement_passed: bool
    no_full_data_leakage_passed: bool
    exact_lift_or_fallback_check_passed: bool
    exact_failure_probability: Fraction
    exact_normalized_reward: Fraction
    exact_policy_rows_evaluated: int
    evaluation_exact_kernel_calls: int
    evaluation_lane: str = "EVALUATION_ONLY"

    def __post_init__(self) -> None:
        _cid(self.result_id, "anytime result")
        _cid(self.context_id, "anytime verification context")
        if (
            self.replayed_prefix_rows <= 0
            or self.replayed_ordinal_draws <= 0
            or self.replayed_structural_support_kernel_calls
            != self.replayed_prefix_rows
            or self.verified_operational_exact_kernel_queries
            < self.replayed_structural_support_kernel_calls
            or self.actual_verifier_exact_kernel_queries
            != (
                self.replayed_structural_support_kernel_calls
                + self.evaluation_exact_kernel_calls
            )
            or self.paired_seed_replay_passed is not True
            or self.prefix_generated_refinement_passed is not True
            or self.no_full_data_leakage_passed is not True
            or self.exact_lift_or_fallback_check_passed is not True
            or type(self.exact_failure_probability) is not Fraction
            or not 0 <= self.exact_failure_probability <= 1
            or type(self.exact_normalized_reward) is not Fraction
            or not 0 <= self.exact_normalized_reward <= 1
            or type(self.exact_policy_rows_evaluated) is not int
            or self.exact_policy_rows_evaluated <= 0
            or self.evaluation_exact_kernel_calls
            != self.exact_policy_rows_evaluated
            or self.evaluation_lane != "EVALUATION_ONLY"
        ):
            raise AnytimeVariableGraphInvariantViolation(
                "anytime graph verification is incomplete"
            )

    @property
    def verification_id(self) -> str:
        return _content_id(
            "verification",
            {
                "schema": "acfqp.anytime_variable_graph_verification.v1",
                "schema_version": SCHEMA_VERSION,
                "result_id": self.result_id,
                "context_id": self.context_id,
                "replayed_prefix_rows": self.replayed_prefix_rows,
                "replayed_ordinal_draws": self.replayed_ordinal_draws,
                "replayed_structural_support_kernel_calls": (
                    self.replayed_structural_support_kernel_calls
                ),
                "verified_operational_exact_kernel_queries": (
                    self.verified_operational_exact_kernel_queries
                ),
                "actual_verifier_exact_kernel_queries": (
                    self.actual_verifier_exact_kernel_queries
                ),
                "paired_seed_replay_passed": True,
                "prefix_generated_refinement_passed": True,
                "no_full_data_leakage_passed": True,
                "exact_lift_or_fallback_check_passed": True,
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
                "evaluation_lane": self.evaluation_lane,
            },
        )


def _evaluate_exact_lift_with_counter(
    result: AnytimeVariableGraphResultV1,
) -> tuple[Fraction, Fraction, int]:
    """Evaluation-only exact lift replay with explicit kernel-call accounting."""

    context = result.context
    coordinate_profile = result.final_profile
    kernel = graph.RelationalGraphMergeKernelV2(context)
    assignments = {
        (item.remaining_horizon, item.state_coordinate): item
        for item in result.final_audit.policy_assignments
    }
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
        state_ir = graph._target_state_ir(context, state, remaining)
        state_coordinate = graph._state_coordinate(
            coordinate_profile,
            state_ir,
        )
        assignment = assignments.get((remaining, state_coordinate))
        if assignment is None:
            raise AnytimeVariableGraphInvariantViolation(
                "exact lift lacks a reachable abstract assignment"
            )
        entry = next(
            (
                item
                for item in assignment.concretizer_entries
                if item.state_id == state.state_id
            ),
            None,
        )
        if entry is None:
            raise AnytimeVariableGraphInvariantViolation(
                "exact lift lacks a reachable ground concretizer"
            )
        action_weight = Fraction(
            1,
            len(entry.distinct_ground_actions),
        )
        risk = Fraction(0)
        reward = Fraction(0)
        for action in entry.distinct_ground_actions:
            atoms = kernel.atoms(state, action)
            exact_kernel_calls += 1
            immediate = atoms[0].normalized_reward
            action_risk = Fraction(0)
            action_future_reward = Fraction(0)
            for atom in atoms:
                if atom.failure:
                    action_risk += atom.probability
                elif remaining > 1:
                    child_risk, child_reward = solve(
                        atom.next_state,
                        remaining - 1,
                    )
                    action_risk += atom.probability * child_risk
                    action_future_reward += (
                        atom.probability * child_reward
                    )
            risk += action_weight * action_risk
            reward += action_weight * (
                immediate + action_future_reward
            )
        memo[key] = (risk, reward)
        return risk, reward

    risk, reward = solve(kernel.root_state(), graph.HORIZON)
    return risk, reward, exact_kernel_calls


def verify_anytime_variable_graph_result_v1(
    result: AnytimeVariableGraphResultV1,
) -> AnytimeVariableGraphVerificationV1:
    """Standalone evaluation: raw replay plus exact lift/fallback comparison."""

    if type(result) is not AnytimeVariableGraphResultV1:
        raise AnytimeVariableGraphInvariantViolation(
            "verifier requires an exact anytime graph result"
        )
    expected = run_anytime_variable_graph_context_v1(
        result.context,
        graph.portable_graph_source_skeleton_v1(),
    )
    if expected.result_id != result.result_id:
        raise AnytimeVariableGraphInvariantViolation(
            "checkpoint/model/refinement/first-stop replay changed result identity"
        )
    rows = (
        result.final_evidence.root_rows
        + result.final_evidence.continuation_rows
    )
    for row in rows:
        verify_anytime_variable_graph_prefix_row_v1(
            result.context,
            row,
        )
    prefix_generated = all(
        item.program_trace is None
        or item.program_trace.generation.target_observation_log_id
        == item.prefix_target_log_id
        for item in result.checkpoints
    )
    no_leak = (
        result.counters.full_131072_rows_materialized == 0
        and result.counters.v0066_full_evidence_constructor_calls == 0
        and result.counters.v0066_full_profile_reads == 0
        and all(
            not item.full_row_materialized for item in rows
        )
    )
    if result.fallback_proof is None:
        (
            exact_failure,
            exact_reward,
            exact_policy_rows,
        ) = _evaluate_exact_lift_with_counter(
            result
        )
        exact_passed = (
            exact_failure <= result.final_audit.failure_upper
            and exact_reward
            >= result.final_audit.normalized_reward_lower
            and exact_failure < result.context.risk_tolerance
        )
    else:
        exact_search = graph._exact_ground_search_v1(result.context)
        exact_failure = exact_search.root_failure_probability
        exact_reward = exact_search.root_normalized_reward
        exact_policy_rows = exact_search.evaluated_state_action_rows
        exact_passed = (
            exact_failure < result.context.risk_tolerance
            and result.fallback_proof.failed_audit_id
            == result.final_audit.audit_id
            and exact_failure
            == result.fallback_proof.exact_failure_probability
            and exact_reward
            == result.fallback_proof.exact_normalized_reward
            and exact_policy_rows
            == result.fallback_proof.evaluated_state_action_rows
        )
    if not (prefix_generated and no_leak and exact_passed):
        raise AnytimeVariableGraphInvariantViolation(
            "anytime graph standalone verification failed"
        )
    return AnytimeVariableGraphVerificationV1(
        result_id=result.result_id,
        context_id=result.context.context_id,
        replayed_prefix_rows=len(rows),
        replayed_ordinal_draws=sum(item.sample_count for item in rows),
        replayed_structural_support_kernel_calls=len(rows),
        verified_operational_exact_kernel_queries=(
            result.counters.operational_exact_kernel_queries
        ),
        actual_verifier_exact_kernel_queries=(
            len(rows) + exact_policy_rows
        ),
        paired_seed_replay_passed=True,
        prefix_generated_refinement_passed=True,
        no_full_data_leakage_passed=True,
        exact_lift_or_fallback_check_passed=True,
        exact_failure_probability=exact_failure,
        exact_normalized_reward=exact_reward,
        exact_policy_rows_evaluated=exact_policy_rows,
        evaluation_exact_kernel_calls=exact_policy_rows,
    )


def run_registered_anytime_variable_graph_family_v1(
) -> tuple[AnytimeVariableGraphResultV1, ...]:
    skeleton = graph.portable_graph_source_skeleton_v1()
    return tuple(
        run_anytime_variable_graph_context_v1(context, skeleton)
        for context in graph.registered_variable_order_contexts_v1()
    )


__all__ = [
    "AnytimeVariableGraphCheckpointV1",
    "AnytimeVariableGraphCountersV1",
    "AnytimeVariableGraphEvidenceV1",
    "AnytimeVariableGraphInvariantViolation",
    "AnytimeVariableGraphPrefixRowV1",
    "AnytimeVariableGraphResultV1",
    "AnytimeVariableGraphTerminal",
    "AnytimeVariableGraphVerificationV1",
    "CHECKPOINTS",
    "CONTRACT_VERSION",
    "PER_OBLIGATION_ALPHA",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "anytime_variable_graph_profile_v1",
    "run_anytime_variable_graph_context_v1",
    "run_registered_anytime_variable_graph_family_v1",
    "verify_anytime_variable_graph_prefix_row_v1",
    "verify_anytime_variable_graph_result_v1",
]
