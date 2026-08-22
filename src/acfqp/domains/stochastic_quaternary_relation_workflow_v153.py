"""A stochastic workflow with a four-key observation-derived relation."""

from __future__ import annotations

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


def select_seeded_quaternary_relation_workflow_outcome_v153(outcomes, *, seed: int, episode_index: int, decision_index: int):
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("quaternary relation workflow outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:quaternary-relation-workflow-outcome:v153\x00"
        + str(seed).encode() + b"\x00" + str(episode_index).encode() + b"\x00" + str(decision_index).encode()
    ).digest()
    draw = Fraction(int.from_bytes(tape, "big"), 1 << (8 * len(tape)))
    cumulative = Fraction()
    for outcome in outcomes:
        cumulative += outcome.probability
        if draw < cumulative:
            return outcome, tape.hex()
    raise AssertionError("quaternary relation workflow draw escaped unit support")


def generate_stochastic_quaternary_relation_workflow_v153(*, stage_count: int, seed: int):
    if stage_count < 5:
        raise ValueError("quaternary relation workflow needs at least five stages")
    rng = random.Random(seed ^ 0x153A91)
    mode_tokens = tuple(seed * 30 + value for value in (3, 11, 19, 27))
    probabilities = (Fraction(1, 7), Fraction(2, 7), Fraction(3, 7))
    rules = []
    robust_old = []
    for stage in range(stage_count - 1):
        for mode, increment in enumerate((1, 2, 3, 4)):
            if mode == 3:
                robust_old.append(len(rules))
            rules.append(RelationKeyedWorkflowRule(stage, stage + 1, mode_tokens[mode], increment, probabilities[(seed + stage + mode) % 3]))
    order = list(range(len(rules)))
    rng.shuffle(order)
    shuffled = tuple(rules[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust = tuple(old_to_new[index] for index in robust_old)
    kernel = RelationKeyedWorkflowKernel(stage_count, 4 * (stage_count - 1), 23, shuffled)
    state = kernel.initial_distribution()[0][1]
    for key in robust:
        state = kernel.step(state, RelationKeyedWorkflowAction(key))[0].next_state
    if state.status is not RelationKeyedWorkflowStatus.SUCCESS:
        raise AssertionError("quaternary relation robust path did not close")
    return kernel, RelationKeyedWorkflowGenerationEvidence(seed, robust, True)


__all__ = ("generate_stochastic_quaternary_relation_workflow_v153", "select_seeded_quaternary_relation_workflow_outcome_v153")
