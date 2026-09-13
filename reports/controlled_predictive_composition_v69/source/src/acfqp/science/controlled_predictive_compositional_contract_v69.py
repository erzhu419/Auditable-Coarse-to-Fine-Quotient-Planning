"""Exact multilevel contracts composed from an identified relational program.

Construction still visits the complete concrete support. Contracts compress the
retained planning model; they do not remove that acquisition/construction cost.
The module can also be loaded directly by a portable process without importing
the science package (whose initializer imports the original ground domain).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
import importlib.util
from pathlib import Path
import sys
from time import perf_counter


def _pure_module(filename, name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _planner():
    return _pure_module('controlled_predictive_quotient_v1.py', 'acfqp_v69_pure_planner')


@dataclass(frozen=True)
class Build:
    model: object
    encoding: dict
    exact_rows: dict
    rule: object
    variant: str
    counts: dict
    elapsed_seconds: float


def _row_signature(rows):
    return tuple((action, tuple(sorted(row))) for action, row in sorted(rows.items()))


def build_model(board, horizon, rule, variant='FULL', max_states=200_000):
    """Build FULL or COMPOSED directly, retaining exact joint row signatures.

    Both arms memoize every (remaining horizon, concrete board), classify the
    same support, and generate every H0 successor. COMPOSED interns the exact
    action-labelled reward/child-contract distributions at every active layer.
    The resource cap counts concrete observations, including terminal boards.
    """
    if variant not in {'FULL', 'COMPOSED'}:
        raise ValueError('unknown V69 variant')
    if type(horizon) is not int or horizon < 0:
        raise ValueError('horizon must be a nonnegative integer')
    if type(max_states) is not int or max_states < 1:
        raise ValueError('max_states must be positive')
    started = perf_counter()
    work = Counter()
    encoding, interned, layers, statuses, exact_rows = {}, {}, {}, {}, {}
    concrete_by_h, active_by_h = Counter(), Counter()

    def intern(key, h, status, action_rows=None):
        if key in interned:
            work['contract_reuses' if status == 'ACTIVE' else 'terminal_reuses'] += 1
            return interned[key]
        state = len(interned)
        interned[key] = state
        layers[state], statuses[state] = h, status
        if action_rows is not None:
            for action, row in action_rows.items():
                exact_rows[state, action] = tuple(sorted(row))
                work['model_transition_rows'] += 1
                work['model_successor_entries'] += len(row)
        return state

    def visit(current, h):
        current = tuple(current)
        concrete_key = h, current
        if concrete_key in encoding:
            work['concrete_memo_hits'] += 1
            return encoding[concrete_key]
        if work['concrete_states'] >= max_states:
            error = ValueError(f'complete V69 model exceeds max_states={max_states}')
            error.counts = dict(work)
            error.elapsed_seconds = perf_counter() - started
            raise error
        work['concrete_states'] += 1
        concrete_by_h[h] += 1
        status, moves = rule.classify(current, work)
        if status == 'ACTIVE' and h == 0:
            status = 'CUTOFF'
        if status != 'ACTIVE':
            state = intern((h, status), h, status)
        else:
            work['concrete_active_states'] += 1
            active_by_h[h] += 1
            action_rows = {}
            for action, moved, score in moves:
                mass = defaultdict(Fraction)
                successors = rule.successors_from_afterstate(moved, score, work)
                work['concrete_action_rows'] += 1
                work['concrete_successor_entries'] += len(successors)
                if h == 1:
                    work['h0_boards_generated'] += len(successors)
                for probability, child, reward in successors:
                    if not isinstance(probability, Fraction) or not isinstance(reward, Fraction):
                        raise TypeError('V69 rules must return exact Fraction probabilities and rewards')
                    child_id = visit(child, h - 1)
                    mass[child_id, reward] += probability
                action_rows[action] = tuple((target, reward, probability)
                                            for (target, reward), probability in sorted(mass.items())
                                            if probability)
            key = (h, _row_signature(action_rows)) if variant == 'COMPOSED' else concrete_key
            state = intern(key, h, 'ACTIVE', action_rows)
        encoding[concrete_key] = state
        return state

    root = visit(tuple(board), horizon)
    v1 = _planner()
    rows = {key: tuple(v1.Outcome(float(p), child, float(r)) for child, r, p in row)
            for key, row in exact_rows.items()}
    model = v1.FiniteModel(layers, statuses, rows, (root,))
    cells_by_h = Counter(layers[state] for state, status in statuses.items() if status == 'ACTIVE')
    work['active_states'] = sum(cells_by_h.values())
    work['terminal_states'] = len(layers) - work['active_states']
    work['registered_states'] = len(layers)
    work['concrete_h0_states'] = concrete_by_h[0]
    counts = dict(work)
    counts.update(concrete_states_by_h=dict(sorted(concrete_by_h.items())),
                  concrete_active_by_h=dict(sorted(active_by_h.items())),
                  active_cells_by_h=dict(sorted(cells_by_h.items())))
    return Build(model, encoding, exact_rows, rule, variant, counts, perf_counter() - started)


def model_payload(build):
    """Save executable cells and exact kernels, with no concrete-state index."""
    return dict(schema='acfqp-compositional-contract-v69', variant=build.variant,
                rule=build.rule.to_payload(),
                cells=[[state, build.model.layers[state], build.model.terminal[state]]
                       for state in sorted(build.model.layers)],
                roots=list(build.model.roots),
                rows=[[state, action, [[p.numerator, p.denominator, target, r.numerator, r.denominator]
                                      for target, r, p in row]]
                      for (state, action), row in sorted(build.exact_rows.items())])


def load_model(payload, rule_type=None):
    """Return a portable CompiledModel and identified rule.

    Exact Fraction fields intentionally remain in Outcome: existing planning
    converts through its floating arithmetic, whereas routing can reconstruct
    the original joint contracts without decimal rounding or board members.
    """
    if payload['schema'] != 'acfqp-compositional-contract-v69':
        raise ValueError('unknown model schema')
    if rule_type is None:
        rule_type = _pure_module('controlled_predictive_relational_dynamics_v69.py',
                                 'acfqp_v69_pure_relational').LearnedDynamics
    v1 = _planner()
    cells = {state: v1.Cell(h, status, ()) for state, h, status in payload['cells']}
    rows = {(state, action): tuple(v1.Outcome(Fraction(p, q), target, Fraction(r, s))
                                   for p, q, target, r, s in row)
            for state, action, row in payload['rows']}
    compiled = v1.CompiledModel(cells, rows, tuple(payload['roots']),
                                {state: state for state in cells}, {})
    return compiled, rule_type.from_payload(payload['rule'])


def route_observation(board, h, rule, compiled, work=None):
    """Reconstruct a contract from an observation using only the saved rule.

    This is recursive encoding with concrete expansion, not a free direct
    classifier. All index-building and successor reconstruction work is exposed.
    The supplied model must be COMPOSED, whose exact contract keys are unique.
    """
    if work is None:
        work = Counter()
    index, grouped = {}, defaultdict(dict)
    for (state, action), outcomes in compiled.rows.items():
        mass = defaultdict(Fraction)
        for outcome in outcomes:
            if not isinstance(outcome.probability, Fraction) or not isinstance(outcome.reward, Fraction):
                raise TypeError('routing requires a model loaded with exact V69 payload rows')
            mass[outcome.next_state, outcome.reward] += outcome.probability
            work['routing_index_outcomes'] += 1
        grouped[state][action] = tuple((child, reward, p) for (child, reward), p in sorted(mass.items()))
        work['routing_index_rows'] += 1
    for state, cell in compiled.cells.items():
        key = ((cell.layer, _row_signature(grouped[state])) if cell.terminal == 'ACTIVE'
               else (cell.layer, cell.terminal))
        if key in index:
            raise ValueError('routing requires unique COMPOSED contracts')
        index[key] = state
        work['routing_index_cells'] += 1
    memo = {}

    def visit(current, remaining):
        current = tuple(current)
        key = remaining, current
        if key in memo:
            work['routing_concrete_memo_hits'] += 1
            return memo[key]
        work['routing_concrete_states'] += 1
        status, moves = rule.classify(current, work)
        if status == 'ACTIVE' and remaining == 0:
            status = 'CUTOFF'
        if status != 'ACTIVE':
            result = index[remaining, status]
        else:
            rows = {}
            for action, moved, score in moves:
                mass = defaultdict(Fraction)
                outcomes = rule.successors_from_afterstate(moved, score, work)
                work['routing_action_rows'] += 1
                work['routing_successor_entries'] += len(outcomes)
                if remaining == 1:
                    work['routing_h0_boards_generated'] += len(outcomes)
                for probability, child, reward in outcomes:
                    mass[visit(child, remaining - 1), reward] += probability
                rows[action] = tuple((child, reward, p) for (child, reward), p in sorted(mass.items()))
            result = index[remaining, _row_signature(rows)]
        memo[key] = result
        return result

    return visit(tuple(board), h)
