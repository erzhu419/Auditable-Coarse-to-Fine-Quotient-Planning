"""Share action effects before evaluating scores and terminal predicates.

Legality is evaluated on the current input. Cached effects contain no input
board labels: they retain either shared output-line references, or only scores
and goal flags when the existing vacancy proof excludes failure.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _grouped_module():
    name = "acfqp_v74_grouped_base"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name,
            Path(__file__).with_name("controlled_predictive_grouped_contract_v73.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


_grouped = _grouped_module()


class EffectCompiler(_grouped.GroupedCompiler):
    def __init__(self, rule):
        super().__init__(rule)
        self.effect_cache = {}
        self.work.update(effect_key_constructions=0, effect_cache_lookups=0,
            effect_cache_hits=0, effect_cache_entries=0, effect_score_aggregations=0,
            effect_output_line_references=0, effect_vacancy_keys=0,
            effect_exact_output_keys=0)

    def _predicate_key(self, summaries, guaranteed_vacancies=False):
        self.work["predicate_calls"] += 1
        result = []
        for action, lines in zip(_grouped.ACTION_ORDER, summaries):
            self.work["candidate_action_changed_tests"] += 1
            if not any(line.changed for line in lines):
                continue
            self.work["effect_key_constructions"] += 1
            if guaranteed_vacancies:
                # The V73 proof guarantees >=2 vacancies after this action.
                # Only reward and goal attainment can affect its H0 contract.
                key = ("VACANT", tuple((line.score, line.maximum >= self.rule.goal_rank)
                                       for line in lines))
                self.work["effect_vacancy_keys"] += 1
            else:
                key = ("EXACT", tuple((line.output, line.score) for line in lines))
                self.work["effect_exact_output_keys"] += 1
                self.work["effect_output_line_references"] += 4
            self.work["effect_cache_lookups"] += 1
            if key in self.effect_cache:
                self.work["effect_cache_hits"] += 1
                score, vector = self.effect_cache[key]
            else:
                self.work["candidate_action_predicate_evaluations"] += 1
                self.work["effect_score_aggregations"] += 1
                score = sum(line.score for line in lines)
                vector = self._terminal_vector(lines, guaranteed_vacancies)
                self.effect_cache[key] = score, vector
                self.work["effect_cache_entries"] += 1
            result.append((action, score, vector))
        self.work["predicate_materializations"] += 1
        return tuple(result)


class SharedEffectCompiler(EffectCompiler):
    """Reuse complete spawn groups for identical action-afterstate geometry."""
    def __init__(self, rule):
        super().__init__(rule)
        self.successor_group_cache = {}
        self.work.update(successor_group_cache_lookups=0, successor_group_cache_hits=0,
            successor_group_materializations=0, successor_group_cached_groups=0)

    def spawn_groups(self, context, grouping=True):
        self.work["successor_group_cache_lookups"] += 1
        key = context.rows, grouping
        if key in self.successor_group_cache:
            # The inherited miss path records its own request. A hit performs
            # no candidate scan or probability/predicate work.
            self.work["spawn_group_requests"] += 1
            self.work["successor_group_cache_hits"] += 1
            return self.successor_group_cache[key]
        result = super().spawn_groups(context, grouping=grouping)
        self.successor_group_cache[key] = result
        self.work["successor_group_materializations"] += 1
        self.work["successor_group_cached_groups"] += len(result)
        return result
