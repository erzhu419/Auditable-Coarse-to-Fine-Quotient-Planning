"""A source-unseen stochastic workflow with a three-key latent relation."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import random

from acfqp.domains.stochastic_relation_keyed_workflow import (
    RelationKeyedWorkflowAction,
    RelationKeyedWorkflowGenerationEvidence,
    RelationKeyedWorkflowKernel,
    RelationKeyedWorkflowRule,
    RelationKeyedWorkflowStatus,
)


def select_seeded_ternary_relation_workflow_outcome_v152(
    outcomes,
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
):
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("ternary relation workflow outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:ternary-relation-workflow-outcome:v152\x00"
        + str(seed).encode()
        + b"\x00"
        + str(episode_index).encode()
        + b"\x00"
        + str(decision_index).encode()
    ).digest()
    draw = Fraction(int.from_bytes(tape, "big"), 1 << (8 * len(tape)))
    cumulative = Fraction()
    for outcome in outcomes:
        cumulative += outcome.probability
        if draw < cumulative:
            return outcome, tape.hex()
    raise AssertionError("ternary relation workflow draw escaped unit support")


def generate_stochastic_ternary_relation_workflow_v152(*, stage_count: int, seed: int):
    if stage_count < 5:
        raise ValueError("ternary relation workflow needs at least five stages")
    rng = random.Random(seed ^ 0x152A91)
    mode_tokens = (seed * 20 + 3, seed * 20 + 11, seed * 20 + 17)
    probabilities = (Fraction(1, 6), Fraction(1, 3), Fraction(1, 2))
    rules = []
    robust_old = []
    for stage in range(stage_count - 1):
        for mode, increment in enumerate((1, 2, 3)):
            if mode == 2:
                robust_old.append(len(rules))
            rules.append(
                RelationKeyedWorkflowRule(
                    stage,
                    stage + 1,
                    mode_tokens[mode],
                    increment,
                    probabilities[(seed + stage + mode) % len(probabilities)],
                )
            )
    order = list(range(len(rules)))
    rng.shuffle(order)
    shuffled = tuple(rules[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust = tuple(old_to_new[index] for index in robust_old)
    kernel = RelationKeyedWorkflowKernel(
        stage_count,
        3 * (stage_count - 1),
        19,
        shuffled,
    )
    state = kernel.initial_distribution()[0][1]
    for key in robust:
        state = kernel.step(state, RelationKeyedWorkflowAction(key))[0].next_state
    if state.status is not RelationKeyedWorkflowStatus.SUCCESS:
        raise AssertionError("ternary relation robust path did not close")
    return kernel, RelationKeyedWorkflowGenerationEvidence(seed, robust, True)


__all__ = (
    "generate_stochastic_ternary_relation_workflow_v152",
    "select_seeded_ternary_relation_workflow_outcome_v152",
)
