"""Enter H1 contracts from local spawn descriptors without a leaf board graph."""
from collections import Counter, defaultdict
from fractions import Fraction
import importlib.util
from pathlib import Path
import sys
from time import perf_counter


def _module(filename, name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
        result = importlib.util.module_from_spec(spec)
        sys.modules[name] = result
        spec.loader.exec_module(result)
    return sys.modules[name]


def build_model(board, horizon, rule, terminal_rule, variant='COMPOSED', max_states=200000):
    if variant not in {'FULL', 'COMPOSED'} or horizon < 2:
        raise ValueError('V72 requires FULL/COMPOSED and a root horizon of at least two')
    started = perf_counter()
    local_module = _module('controlled_predictive_local_contract_v72.py', 'acfqp_v72_local_builder_compiler')
    local = local_module.LocalCompiler(rule)
    work = Counter(h0_boards_generated=0, h1_boards_generated=0, concrete_successor_entries=0)
    encoding, interned, layers, statuses, exact_rows, direct_contracts = {}, {}, {}, {}, {}, {}
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

    def note_concrete(h):
        if work['concrete_states'] >= max_states:
            error = ValueError(f'complete V72 model exceeds max_states={max_states}')
            error.counts = dict(work)
            raise error
        work['concrete_states'] += 1
        concrete_by_h[h] += 1

    def h1(context, cell, rank):
        literal_key = None
        if variant == 'FULL':
            child = list(context.base)
            child[cell] = rank
            literal_key = 1, tuple(child)
            work['h1_boards_generated'] += 1
            work['concrete_successor_entries'] += 1
            if literal_key in encoding:
                work['concrete_memo_hits'] += 1
                return encoding[literal_key]
            note_concrete(1)
            work['concrete_active_states'] += 1
            active_by_h[1] += 1
        work['direct_h1_contract_evaluations'] += 1
        description = local.contract(context, cell, rank)
        semantic_key = tuple((a, score, tuple(sorted(terms))) for a, score, terms in description)
        if variant == 'COMPOSED' and semantic_key in direct_contracts:
            work['direct_h1_contract_reuses'] += 1
            return direct_contracts[semantic_key]
        action_rows = {}
        for action, score, terms in description:
            reward = Fraction(score, 2048)
            row = [(intern((0, status), 0, status), reward, probability)
                   for status, probability in terms if probability]
            action_rows[action] = tuple(sorted(row))
            work['direct_h1_rows_registered'] += 1
        signature = tuple(sorted(action_rows.items()))
        state = intern((1, signature) if variant == 'COMPOSED' else literal_key,
                       1, 'ACTIVE', action_rows)
        if variant == 'COMPOSED':
            direct_contracts[semantic_key] = state
        else:
            encoding[literal_key] = state
        return state

    def visit(current, h):
        key = h, current
        if key in encoding:
            work['concrete_memo_hits'] += 1
            return encoding[key]
        note_concrete(h)
        status, moves = rule.classify(current, work)
        if status != 'ACTIVE':
            state = intern((h, status), h, status)
        else:
            work['concrete_active_states'] += 1
            active_by_h[h] += 1
            action_rows = {}
            for action, moved, score in moves:
                mass = defaultdict(Fraction)
                work['concrete_action_rows'] += 1
                if h == 2:
                    context = local.prepare(moved)
                    reward = Fraction(score, 2048)
                    for cell in context.empty_cells:
                        for rank, probability in rule.spawn_distribution:
                            work['boundary_spawn_candidates'] += 1
                            child_status = local.patch_status(context, cell, rank)
                            if child_status == 'ACTIVE':
                                work['active_boundary_candidates'] += 1
                                child_id = h1(context, cell, rank)
                            else:
                                child_id = intern((1, child_status), 1, child_status)
                            mass[child_id, reward] += probability/len(context.empty_cells)
                else:
                    outcomes = terminal_rule.successors(moved, score, h-1, work)
                    work['symbolic_emitted_outcomes'] += len(outcomes)
                    for probability, child_status, child, reward in outcomes:
                        if child_status == 'ACTIVE':
                            work['concrete_successor_entries'] += 1
                            child_id = visit(child, h-1)
                        else:
                            child_id = intern((h-1, child_status), h-1, child_status)
                        mass[child_id, reward] += probability
                action_rows[action] = tuple((target, reward, probability)
                    for (target, reward), probability in sorted(mass.items()) if probability)
            signature = tuple(sorted(action_rows.items()))
            state = intern((h, signature) if variant == 'COMPOSED' else key,
                           h, 'ACTIVE', action_rows)
        encoding[key] = state
        return state

    root = visit(tuple(board), horizon)
    contract = _module('controlled_predictive_compositional_contract_v69.py', 'acfqp_v72_reference')
    v1 = contract._planner()
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
        active_cells_by_h=dict(sorted(cells_by_h.items())), local_compiler=dict(local.work))
    return contract.Build(model, encoding, exact_rows, rule, variant, counts, perf_counter()-started)
