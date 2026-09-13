"""Route H1 observations by local consequences and query a saved exact kernel."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def _load(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "src/acfqp/science" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_contract(rows):
    return tuple(sorted((action, score, tuple(sorted(masses)))
                        for action, score, masses in rows))


def h1_index(compiled, work):
    """Index executable H1 kernels by reward/terminal mass, without board keys."""
    contracts = defaultdict(list)
    for (state, action), outcomes in compiled.rows.items():
        cell = compiled.cells[state]
        if cell.layer != 1 or cell.terminal != "ACTIVE":
            continue
        work["h1_index_action_rows"] += 1
        score = outcomes[0].reward * 2048
        if score.denominator != 1:
            raise ValueError("H1 merge reward is not an integer score")
        mass = defaultdict(Fraction)
        for item in outcomes:
            if item.reward * 2048 != score:
                raise ValueError("H1 local contract requires a fixed action reward")
            mass[compiled.cells[item.next_state].terminal] += item.probability
            work["h1_index_outcomes"] += 1
        contracts[state].append((action, int(score), tuple(mass.items())))
    index = {}
    for state, rows in contracts.items():
        key = canonical_contract(rows)
        if key in index:
            raise ValueError("LOCAL_H1 requires unique composed H1 contracts")
        index[key] = state
    work["h1_index_cells"] = len(index)
    return index


def make_router(package, compiled, rule):
    """Build a direct router and return its callable plus one-time index work."""
    router = package["router"]
    literal = {(h, tuple(board)): cell for h, board, cell in router["labels"]}
    index_work = Counter(map_entries=len(literal))
    compiler = None
    if router["kind"] == "LOCAL_H1":
        local = _load("controlled_predictive_local_contract_v72.py", "acfqp_v72_worker_local")
        compiler = local.LocalCompiler(rule)
        local_index = h1_index(compiled, index_work)
        index_work.update(compiler.work)
    elif router["kind"] != "MAP":
        raise ValueError("unknown observation router")

    def route(board, h, work):
        work["observations"] += 1
        if compiler is not None and h == 1:
            work["h1_observation_contract_calls"] += 1
            before = Counter(compiler.work)
            key = canonical_contract(compiler.observation_contract(tuple(board)))
            work.update(Counter(compiler.work) - before)
            result = local_index.get(key)
        else:
            work["map_lookups"] += 1
            result = literal.get((h, tuple(board)))
        work["supported_observations" if result is not None else "unsupported_observations"] += 1
        return result

    return route, dict(index_work)


def run(package_path, inputs_path, output):
    started = perf_counter()
    package = json.loads(package_path.read_text())
    data = json.loads(inputs_path.read_text())
    if package["schema"] != "acfqp.observation_package.v72":
        raise ValueError("unknown observation package schema")
    contract = _load("controlled_predictive_compositional_contract_v69.py",
                     "acfqp_v72_worker_contract")
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

    work, routes = Counter(), []
    tick = perf_counter()
    for row in data["observations"]:
        board, h = tuple(row["board"]), row["horizon"]
        routes.append(route(board, h, work))
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
