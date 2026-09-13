"""Direct H2 contracts with explicit geometry accounting and H1 grouping."""
from collections import Counter, defaultdict
from fractions import Fraction
import importlib.util
from pathlib import Path
import sys
from time import perf_counter


def _module(filename, name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
        value = importlib.util.module_from_spec(spec)
        sys.modules[name] = value
        spec.loader.exec_module(value)
    return sys.modules[name]


def build_model(board, horizon, rule, terminal_rule, grouping, max_states=200000):
    if horizon < 3:
        raise ValueError('V73 construction cohort uses root horizons at least three')
    started = perf_counter()
    local = _module('controlled_predictive_grouped_contract_v73.py', 'acfqp_v73_builder_compiler')
    compiler = local.GroupedCompiler(rule)
    work = Counter(h0_boards_generated=0,h1_boards_generated=0,h2_boards_generated=0,
                   concrete_successor_entries=0,unique_h2_geometries=0)
    encoding, interned, layers, statuses, exact_rows = {}, {}, {}, {}, {}
    h1_cells, h2_geometry = {}, {}
    concrete_by_h = Counter()

    def intern(key, h, status, action_rows=None):
        if key in interned:
            work['contract_reuses' if status=='ACTIVE' else 'terminal_reuses'] += 1
            return interned[key]
        state = len(interned)
        interned[key] = state
        layers[state], statuses[state] = h, status
        if action_rows is not None:
            for action, row in action_rows.items():
                exact_rows[state,action] = tuple(sorted(row))
                work['model_transition_rows'] += 1
                work['model_successor_entries'] += len(row)
        return state

    def h1(description):
        work['h1_contracts_received'] += 1
        key = tuple((a,score,tuple(sorted(terms))) for a,score,terms in description)
        if key in h1_cells:
            work['h1_cell_reuses'] += 1
            return h1_cells[key]
        rows = {}
        for action,score,terms in description:
            reward = Fraction(score,2048)
            rows[action] = tuple(sorted((intern((0,status),0,status),reward,p)
                                        for status,p in terms if p))
        cell = intern((1,tuple(sorted(rows.items()))),1,'ACTIVE',rows)
        h1_cells[key] = cell
        return cell

    def note_geometry():
        if work['concrete_states']+work['unique_h2_geometries'] >= max_states:
            error = ValueError(f'complete V73 model exceeds max_states={max_states}')
            error.counts = dict(work)
            raise error

    def h2(context):
        if context.rows in h2_geometry:
            work['h2_geometry_reuses'] += 1
            return h2_geometry[context.rows]
        note_geometry()
        work['unique_h2_geometries'] += 1
        rows = {}
        for action,score,after in compiler.actions(context):
            reward = Fraction(score,2048)
            mass = defaultdict(Fraction)
            for probability,status,description,representative,count in compiler.spawn_groups(after,grouping=grouping):
                work['h1_groups_or_entries_received'] += 1
                target = h1(description) if status=='ACTIVE' else intern((1,status),1,status)
                mass[target,reward] += probability
            rows[action] = tuple((child,r,p) for (child,r),p in sorted(mass.items()) if p)
            work['h2_action_rows_evaluated'] += 1
        cell = intern((2,tuple(sorted(rows.items()))),2,'ACTIVE',rows)
        h2_geometry[context.rows] = cell
        return cell

    def visit(current,h):
        key = h,current
        if key in encoding:
            work['concrete_memo_hits'] += 1
            return encoding[key]
        note_geometry()
        work['concrete_states'] += 1
        concrete_by_h[h] += 1
        status,moves = rule.classify(current,work)
        if status!='ACTIVE':
            cell = intern((h,status),h,status)
        else:
            work['concrete_active_states'] += 1
            rows = {}
            for action,moved,score in moves:
                mass = defaultdict(Fraction)
                work['concrete_action_rows'] += 1
                if h==3:
                    context = compiler.prepare(moved)
                    reward = Fraction(score,2048)
                    for vacancy in context.empty_cells:
                        for rank,p in rule.spawn_distribution:
                            work['h2_spawn_descriptors'] += 1
                            status = compiler.patch_status(context,vacancy,rank)
                            target = (h2(compiler.patched_context(context,vacancy,rank)) if status=='ACTIVE'
                                      else intern((2,status),2,status))
                            mass[target,reward] += p/len(context.empty_cells)
                else:
                    for p,status,child,reward in terminal_rule.successors(moved,score,h-1,work):
                        if status=='ACTIVE':
                            work['concrete_successor_entries'] += 1
                            target = visit(child,h-1)
                        else:
                            target = intern((h-1,status),h-1,status)
                        mass[target,reward] += p
                rows[action] = tuple((child,reward,p) for (child,reward),p in sorted(mass.items()) if p)
            cell = intern((h,tuple(sorted(rows.items()))),h,'ACTIVE',rows)
        encoding[key] = cell
        return cell

    root = visit(tuple(board),horizon)
    reference = _module('controlled_predictive_compositional_contract_v69.py','acfqp_v73_reference')
    v1 = reference._planner()
    rows = {key:tuple(v1.Outcome(float(p),child,float(r)) for child,r,p in value)
            for key,value in exact_rows.items()}
    model = v1.FiniteModel(layers,statuses,rows,(root,))
    cells_by_h = Counter(layers[s] for s,status in statuses.items() if status=='ACTIVE')
    work['active_states'] = sum(cells_by_h.values())
    work['terminal_states'] = len(layers)-work['active_states']
    work['registered_states'] = len(layers)
    work['geometric_active_states'] = work['concrete_active_states']+work['unique_h2_geometries']
    counts = dict(work)
    counts.update(concrete_states_by_h=dict(concrete_by_h),concrete_active_by_h=dict(concrete_by_h),
                  active_cells_by_h=dict(cells_by_h),grouped_compiler=dict(compiler.work))
    return reference.Build(model,encoding,exact_rows,rule,'COMPOSED',counts,perf_counter()-started)
