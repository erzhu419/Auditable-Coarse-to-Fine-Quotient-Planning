"""Route H2 observations through compositional consequences and a saved kernel."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def _module(path, name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _h1_worker():
    return _module(ROOT / "scripts/query_controlled_predictive_local_v72.py",
                   "acfqp_v73_h1_worker")


def _compiler(rule):
    module = _module(ROOT / "src/acfqp/science/controlled_predictive_grouped_contract_v73.py",
                     "acfqp_v73_worker_grouped")
    return module.GroupedCompiler(rule)


def _row_key(rows):
    return tuple(sorted((action, tuple((child, reward, probability)
                        for (child, reward), probability in sorted(mass.items()) if probability))
                        for action, mass in rows.items()))


def semantic_h2(board, rule, grouping=True, work=None):
    """Return an exact nested contract without using any saved target kernel.

    Leaves are ('H1', canonical_action_contract) or ('TERMINAL', status).
    Probability and reward values remain Fraction; callers may serialize them
    explicitly. The optional Counter includes this call's compiler work.
    """
    compiler = _compiler(rule)
    context = compiler.prepare(tuple(board))
    status = compiler.status(context)
    if status != "ACTIVE":
        result = ("TERMINAL", status)
    else:
        rows = {}
        for action, score, after in compiler.actions(context):
            mass = defaultdict(Fraction)
            for probability, child_status, contract, _, _ in compiler.spawn_groups(
                    after, grouping=grouping):
                child = (("H1", _h1_worker().canonical_contract(contract))
                         if child_status == "ACTIVE" else ("TERMINAL", child_status))
                mass[child, Fraction(score, 2048)] += probability
            rows[action] = mass
        result = _row_key(rows)
    if work is not None:
        work.update(compiler.work)
    return result


def h2_index(compiled, work):
    rows = defaultdict(dict)
    for (state, action), outcomes in compiled.rows.items():
        cell = compiled.cells[state]
        if cell.layer != 2 or cell.terminal != "ACTIVE":
            continue
        work["h2_index_action_rows"] += 1
        mass = defaultdict(Fraction)
        for item in outcomes:
            mass[item.next_state, item.reward] += item.probability
            work["h2_index_outcomes"] += 1
        rows[state][action] = mass
    index = {}
    for state, action_rows in rows.items():
        key = _row_key(action_rows)
        if key in index:
            raise ValueError("LOCAL_H2 requires unique composed H2 contracts")
        index[key] = state
    work["h2_index_cells"] = len(index)
    return index


def make_router(package, compiled, rule):
    """Build H1/H2 semantic indices plus the remaining literal high-layer map."""
    router = package["router"]
    if router["kind"] == "LOCAL_H1":
        return _h1_worker().make_router(package, compiled, rule)
    if router["kind"] != "LOCAL_H2":
        raise ValueError("unknown observation router")
    grouping = router["grouping"]
    literal = {(h, tuple(board)): cell for h, board, cell in router["labels"]}
    index_work = Counter(map_entries=len(literal))
    compiler = _compiler(rule)
    index_work.update(compiler.work)
    h1 = _h1_worker().h1_index(compiled, index_work)
    h2 = h2_index(compiled, index_work)
    terminals = {(cell.layer, cell.terminal): state for state, cell in compiled.cells.items()
                 if cell.terminal != "ACTIVE"}
    index_work["terminal_index_cells"] = len(terminals)

    def route_h2(board, work):
        context = compiler.prepare(board)
        if compiler.status(context) != "ACTIVE":
            return None
        rows = {}
        for action, score, after in compiler.actions(context):
            mass = defaultdict(Fraction)
            for probability, status, contract, _, _ in compiler.spawn_groups(after, grouping=grouping):
                work["h2_child_contract_lookups"] += 1
                if status == "ACTIVE":
                    child = h1.get(_h1_worker().canonical_contract(contract))
                else:
                    child = terminals.get((1, status))
                if child is None:
                    work["h2_missing_child_contracts"] += 1
                    return None
                mass[child, Fraction(score, 2048)] += probability
            rows[action] = mass
        return h2.get(_row_key(rows))

    def route(board, h, work):
        board = tuple(board)
        work["observations"] += 1
        before = Counter(compiler.work)
        if h == 1:
            work["h1_observation_contract_calls"] += 1
            result = h1.get(_h1_worker().canonical_contract(compiler.observation_contract(board)))
        elif h == 2:
            work["h2_observation_contract_calls"] += 1
            result = route_h2(board, work)
        else:
            work["map_lookups"] += 1
            result = literal.get((h, board))
        work.update(Counter(compiler.work) - before)
        work["supported_observations" if result is not None else "unsupported_observations"] += 1
        return result

    return route, dict(index_work)


def run(package_path, inputs_path, output):
    started = perf_counter()
    package = json.loads(package_path.read_text())
    data = json.loads(inputs_path.read_text())
    if package["schema"] != "acfqp.observation_package.v73":
        raise ValueError("unknown observation package schema")
    contract = _module(ROOT / "src/acfqp/science/controlled_predictive_compositional_contract_v69.py",
                       "acfqp_v73_worker_contract")
    compiled, rule = contract.load_model(package["kernel"])
    planner = contract._planner()
    load_seconds = perf_counter() - started
    load_counts = dict(kernel_cells=len(compiled.cells), kernel_rows=len(compiled.rows),
                       kernel_outcomes=sum(len(row) for row in compiled.rows.values()),
                       input_observations=len(data["observations"]),
                       input_queries=len(data["queries"]))
    tick = perf_counter()
    route, index_counts = make_router(package, compiled, rule)
    index_seconds = perf_counter() - tick
    work = Counter()
    tick = perf_counter()
    routes = [route(row["board"], row["horizon"], work) for row in data["observations"]]
    routing_seconds = perf_counter() - tick

    tick = perf_counter()
    queries, planning_work = {}, Counter()
    for name, arguments in data["queries"].items():
        query_started = perf_counter()
        solution = planner.plan(compiled, planner.Query(**arguments))
        elapsed = perf_counter() - query_started
        planning_work.update(solution.counts)
        queries[name] = dict(policy=solution.policy, values=solution.values,
                             counts=solution.counts, planning_seconds=elapsed)
    planning_seconds = perf_counter() - tick
    imported = [name for name in sys.modules if name.startswith("acfqp.domains")]
    if imported:
        raise AssertionError(f"ground imported: {imported}")
    result = dict(routes=routes, queries=queries, load_seconds=load_seconds,
                  load_counts=load_counts, index_seconds=index_seconds,
                  index_counts=index_counts, routing_seconds=routing_seconds,
                  routing_counts=dict(work), planning_seconds=planning_seconds,
                  planning_counts=dict(planning_work), ground_imports=imported,
                  worker_seconds_before_write=perf_counter() - started)
    output.write_text(json.dumps(result, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.package, args.inputs, args.output)
