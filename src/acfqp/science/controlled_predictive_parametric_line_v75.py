"""Compile the frozen learned line rewrite before binding tile ranks.

Templates retain input-variable identity and the +1 produced by a merge.
They contain no concrete ranks; subsequent actions reclassify the bound ranks
so a newly produced rank can equal another previously distinct variable.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class LineTemplate:
    pattern: tuple[int, ...]
    outputs: tuple[tuple[int, int] | None, ...]
    reward_slots: tuple[int, ...]


class ParametricLines:
    def __init__(self, rule):
        program = rule.program
        selected = (program.pack, program.merge_relation, program.rank_increment,
                    program.consumption, program.reward_rule)
        if selected != (True, "equal", 1, "once", "output_value"):
            raise ValueError("V75 parametric lines require the frozen V69 rewrite program")
        self.templates = {}
        self.work = Counter(compiled_programs=1)

    def _compile(self, pattern):
        """Compile structure from variable IDs only, before numeric binding."""
        variables = tuple(variable for variable in pattern if variable >= 0)
        outputs, reward_slots, position = [], [], 0
        while position < len(variables):
            variable = variables[position]
            merges = False
            if position + 1 < len(variables):
                self.work["template_equality_tests"] += 1
                merges = variable == variables[position + 1]
            if merges:
                reward_slots.append(len(outputs))
                outputs.append((variable, 1))
                position += 2
            else:
                outputs.append((variable, 0))
                position += 1
        self.work["template_compilations"] += 1
        self.work["template_output_expressions"] += len(outputs)
        self.work["template_reward_expressions"] += len(reward_slots)
        outputs.extend([None] * (4 - len(outputs)))
        return LineTemplate(pattern, tuple(outputs), tuple(reward_slots))

    def template_for(self, inputs):
        """Return an equality/zero template and its ordered numeric bindings."""
        pattern, bindings, variables = [], [], {}
        for rank in inputs:
            self.work["pattern_rank_reads"] += 1
            if rank == 0:
                pattern.append(-1)
            else:
                if rank not in variables:
                    variables[rank] = len(bindings)
                    bindings.append(rank)
                pattern.append(variables[rank])
        pattern = tuple(pattern)
        self.work["pattern_constructions"] += 1
        self.work["template_lookups"] += 1
        if pattern not in self.templates:
            self.templates[pattern] = self._compile(pattern)
        else:
            self.work["template_cache_hits"] += 1
        self.work["rank_bindings"] += len(bindings)
        return self.templates[pattern], tuple(bindings)

    def bind(self, template, ranks):
        """Evaluate rank and reward expressions while preserving merge offsets."""
        self.work["template_bind_calls"] += 1
        output = []
        for expression in template.outputs:
            if expression is None:
                output.append(0)
            else:
                variable, increment = expression
                output.append(ranks[variable] + increment)
                self.work["bound_rank_expressions"] += 1
        score = 0
        for slot in template.reward_slots:
            score += 1 << output[slot]
            self.work["bound_reward_expressions"] += 1
        return tuple(output), score

    def line(self, inputs):
        self.work["line_calls"] += 1
        template, ranks = self.template_for(inputs)
        return self.bind(template, ranks)
