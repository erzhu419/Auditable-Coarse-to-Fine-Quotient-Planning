"""Compile a fixed soft abstraction's exact decoder Bellman operator.

Execution uses only arrays in abstract coordinates. Each successor choice set
retains its max over legal encoder rows before transition expectations are
taken. Compilation uses the original model; loading and backup do not.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import math
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CompiledOperator:
    choice_encoders: np.ndarray
    choice_offsets: np.ndarray
    transition_weights: np.ndarray
    representative_rewards: np.ndarray
    output_to_representative: np.ndarray
    discount: np.ndarray
    reward_scale: np.ndarray
    source_dimensions: np.ndarray

    def backup(self, u: np.ndarray) -> np.ndarray:
        """Evaluate L F E u, retaining successor-wise legal action maxima."""
        u = np.asarray(u, dtype=float)
        if u.shape != (self.choice_encoders.shape[1],):
            raise ValueError("u must have one entry per abstract code")
        if not np.isfinite(u).all():
            raise FloatingPointError("Non-finite entries in abstract Q iterate")
        scores = np.einsum("ij,j->i", self.choice_encoders, u, optimize=True)
        successor_values = np.maximum.reduceat(scores, self.choice_offsets[:-1])
        updated = self.representative_rewards + self.discount * np.einsum(
            "ij,j->i", self.transition_weights, successor_values
        )
        return updated[self.output_to_representative]

    def inventory(self) -> dict[str, Any]:
        arrays = {field.name: getattr(self, field.name) for field in fields(self)}
        return {
            "abstract_codes": int(self.output_to_representative.size),
            "unique_decoder_representatives": int(self.representative_rewards.size),
            "duplicate_decoder_outputs": int(self.output_to_representative.size - self.representative_rewards.size),
            "successor_choice_sets": int(self.choice_offsets.size - 1),
            "choice_encoder_rows": int(self.choice_encoders.shape[0]),
            "nonzero_transition_weights": int(np.count_nonzero(self.transition_weights)),
            "transition_weight_slots": int(self.transition_weights.size),
            "source_states": int(self.source_dimensions[0]),
            "source_legal_pairs": int(self.source_dimensions[1]),
            "source_rectangular_pairs": int(self.source_dimensions[2]),
            "supported_source_states": int(self.source_dimensions[3]),
            "reward_scale": float(self.reward_scale),
            "array_bytes": sum(array.nbytes for array in arrays.values()),
            "bytes_by_array": {name: array.nbytes for name, array in arrays.items()},
        }

    def save(self, path: str | Path) -> None:
        """Retain the complete executable operator without pickle or model objects."""
        np.savez(path, **{field.name: getattr(self, field.name) for field in fields(self)})

    @classmethod
    def load(cls, path: str | Path) -> CompiledOperator:
        with np.load(path, allow_pickle=False) as arrays:
            return cls(**{field.name: arrays[field.name] for field in fields(cls)})


def _canonical_rows(rows: np.ndarray) -> np.ndarray:
    """Exact row comparison only: order and repeated legal choices do not alter max."""
    ordered = sorted(range(rows.shape[0]), key=lambda index: tuple(rows[index]))
    distinct = []
    for index in ordered:
        if not distinct or not np.array_equal(rows[index], distinct[-1]):
            distinct.append(rows[index].copy())
    return np.stack(distinct)


def compile_operator(adapter: Any, legal_abstraction: Any, reward_scale: float = 1.) -> CompiledOperator:
    """Read decoder rows once and remove the original ground-model dependency.

    Duplicate decoder representatives share a backup. Successor states whose
    complete legal encoder choice sets are exactly equal share a max; their
    transition probabilities are summed. No approximate clustering is used.
    """
    encoder = np.asarray(legal_abstraction.encoder, dtype=float)
    decoder = np.asarray(legal_abstraction.decoder, dtype=int)
    valid = np.asarray(adapter.valid_pair_indices, dtype=int)
    if encoder.shape != (valid.size, decoder.size):
        raise ValueError("The abstraction must be fitted on the adapter's legal pairs")
    if not np.isfinite(encoder).all():
        raise FloatingPointError("Non-finite entries in abstraction encoder")
    unique_decoder = []
    output_to_representative = []
    for representative in decoder.tolist():
        if representative not in unique_decoder:
            unique_decoder.append(representative)
        output_to_representative.append(unique_decoder.index(representative))
    num_actions = adapter.mdp.num_actions
    rectangle_representatives = valid[np.asarray(unique_decoder, dtype=int)]
    original_probabilities = adapter.mdp.transitions[
        rectangle_representatives // num_actions, rectangle_representatives % num_actions
    ]
    representative_rewards = adapter.mdp.rewards[
        rectangle_representatives // num_actions, rectangle_representatives % num_actions
    ] * reward_scale
    supported_states = np.flatnonzero(np.any(original_probabilities != 0., axis=0))
    choice_sets = []
    group_members = []
    for state in supported_states.tolist():
        rows = _canonical_rows(encoder[valid // num_actions == state])
        group = next((i for i, previous in enumerate(choice_sets) if np.array_equal(rows, previous)), None)
        if group is None:
            choice_sets.append(rows)
            group_members.append([state])
        else:
            group_members[group].append(state)
    weights = np.asarray([
        [math.fsum(probabilities[state] for state in members) for members in group_members]
        for probabilities in original_probabilities
    ], dtype=float)
    offsets = np.cumsum([0] + [rows.shape[0] for rows in choice_sets], dtype=np.int64)
    return CompiledOperator(
        choice_encoders=np.concatenate(choice_sets, axis=0),
        choice_offsets=offsets,
        transition_weights=weights,
        representative_rewards=np.asarray(representative_rewards, dtype=float),
        output_to_representative=np.asarray(output_to_representative, dtype=np.int64),
        discount=np.asarray(adapter.mdp.gamma, dtype=float),
        reward_scale=np.asarray(reward_scale, dtype=float),
        source_dimensions=np.asarray([
            adapter.mdp.num_states, valid.size, adapter.mdp.num_state_action_pairs,
            supported_states.size,
        ], dtype=np.int64),
    )
