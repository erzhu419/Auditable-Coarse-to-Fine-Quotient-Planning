"""Build exact contracts while integrating terminal spawn outcomes symbolically."""
from collections import Counter, defaultdict
from fractions import Fraction
import importlib.util
from pathlib import Path
import sys
from time import perf_counter


def _contract():
    name = 'acfqp_v71_contract_reference'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name,
            Path(__file__).with_name('controlled_predictive_compositional_contract_v69.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def build_model(board, horizon, rule, compiled_rule, variant='COMPOSED', max_states=200000):
    """Use direct terminal mass; enumerate remaining ACTIVE observations only.

    The cell interning and exact joint rows retain V69's order and semantics.
    ``encoding`` now holds only concrete observations actually visited. Active
    support is unchanged; omitted terminal boards do not become free labels.
    """
    if variant not in {'FULL', 'COMPOSED'}:
        raise ValueError('unknown contract variant')
    started = perf_counter()
    work = Counter(h0_boards_generated=0, concrete_successor_entries=0)
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
        concrete_key = h, current
        if concrete_key in encoding:
            work['concrete_memo_hits'] += 1
            return encoding[concrete_key]
        if work['concrete_states'] >= max_states:
            error = ValueError(f'complete V71 model exceeds max_states={max_states}')
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
                outcomes = compiled_rule.successors(moved, score, h-1, work)
                work['concrete_action_rows'] += 1
                work['symbolic_emitted_outcomes'] += len(outcomes)
                for probability, child_status, child, reward in outcomes:
                    if child_status == 'ACTIVE':
                        work['concrete_successor_entries'] += 1
                        child_id = visit(child, h-1)
                    else:
                        work['direct_terminal_mass_entries'] += 1
                        child_id = intern((h-1, child_status), h-1, child_status)
                    mass[child_id, reward] += probability
                action_rows[action] = tuple((target, reward, probability)
                    for (target, reward), probability in sorted(mass.items()) if probability)
            signature = tuple((a, tuple(sorted(row))) for a, row in sorted(action_rows.items()))
            state = intern((h, signature) if variant == 'COMPOSED' else concrete_key,
                           h, 'ACTIVE', action_rows)
        encoding[concrete_key] = state
        return state

    root = visit(tuple(board), horizon)
    reference = _contract()
    v1 = reference._planner()
    rows = {key: tuple(v1.Outcome(float(p), child, float(r)) for child, r, p in row)
            for key, row in exact_rows.items()}
    model = v1.FiniteModel(layers, statuses, rows, (root,))
    cells_by_h = Counter(layers[s] for s, status in statuses.items() if status == 'ACTIVE')
    work['active_states'] = sum(cells_by_h.values())
    work['terminal_states'] = len(layers)-work['active_states']
    work['registered_states'] = len(layers)
    work['concrete_h0_states'] = concrete_by_h[0]
    counts = dict(work)
    counts.update(concrete_states_by_h=dict(sorted(concrete_by_h.items())),
                  concrete_active_by_h=dict(sorted(active_by_h.items())),
                  active_cells_by_h=dict(sorted(cells_by_h.items())))
    return reference.Build(model, encoding, exact_rows, rule, variant, counts, perf_counter()-started)
