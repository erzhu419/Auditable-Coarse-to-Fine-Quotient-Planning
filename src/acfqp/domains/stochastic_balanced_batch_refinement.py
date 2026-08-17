"""Balanced fresh successor of the V54 batch-refinement ground family.

All paths that reach the goal produce the same target units.  This removes an
accidental symmetry between opaque constant columns without exposing semantic
column names to the constructor.
"""

from __future__ import annotations

from fractions import Fraction
import random

from acfqp.domains.stochastic_batch_refinement import (
    BatchRefinementAction,
    BatchRefinementGenerationEvidence,
    BatchRefinementKernel,
    BatchRefinementRule,
    BatchRefinementStatus,
)


def generate_stochastic_balanced_batch_refinement(
    *, stage_count: int, unit_base: int, seed: int
) -> tuple[BatchRefinementKernel, BatchRefinementGenerationEvidence]:
    if stage_count < 5 or unit_base < 2:
        raise ValueError("balanced batch-refinement specification changed")
    rng = random.Random(seed)
    probabilities = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
    advance_tokens = {1: 17 + 6 * (seed % 5), 2: 43 + 6 * (seed % 5)}
    primary_units = [unit_base + rng.randrange(3) for _ in range(stage_count - 1)]
    primary_risks = [1 + rng.randrange(3) for _ in range(stage_count - 1)]
    rules = []
    robust_path = []
    for stage in range(stage_count - 1):
        robust_path.append(len(rules))
        rules.append(
            BatchRefinementRule(
                stage,
                stage + 1,
                advance_tokens[1],
                primary_units[stage],
                primary_risks[stage],
                probabilities[(seed + stage) % len(probabilities)],
            )
        )
        if stage + 2 < stage_count:
            rules.append(
                BatchRefinementRule(
                    stage,
                    stage + 2,
                    advance_tokens[2],
                    primary_units[stage] + primary_units[stage + 1],
                    primary_risks[stage] + primary_risks[stage + 1] + 2,
                    probabilities[(seed + stage + 1) % len(probabilities)],
                )
            )
    kernel = BatchRefinementKernel(
        stage_count=stage_count,
        risk_capacity=sum(primary_risks) + 1,
        target_units=sum(primary_units),
        checksum_modulus=11 + 2 * (seed % 3),
        rules=tuple(rules),
    )
    state = kernel.initial_distribution()[0][1]
    for rule_index in robust_path:
        outcomes = kernel.step(state, BatchRefinementAction(rule_index))
        state = max(outcomes, key=lambda row: row.next_state.risk).next_state
    if state.status is not BatchRefinementStatus.SUCCESS:
        raise AssertionError("balanced batch-refinement witness changed")
    return kernel, BatchRefinementGenerationEvidence(seed, tuple(robust_path), True)


__all__ = ("generate_stochastic_balanced_batch_refinement",)
