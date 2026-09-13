"""Query saved kernels with BASE, late-grouped, or early-effect H2 routing."""
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def _previous():
    name = "acfqp_v74_previous_worker"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, ROOT / "scripts/query_controlled_predictive_grouped_v73.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _compiler(rule, share_successors=False):
    module = _previous()._module(
        ROOT / "src/acfqp/science/controlled_predictive_effect_contract_v74.py",
        "acfqp_v74_worker_effect")
    return (module.SharedEffectCompiler(rule) if share_successors else module.EffectCompiler(rule))


def semantic_h2(board, rule, grouping=True, work=None, *, share_successors=False):
    """Predict an EARLY/SHARED nested contract without a saved target kernel."""
    previous = _previous()
    canonical = previous._h1_worker().canonical_contract
    compiler = _compiler(rule, share_successors)
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
                child = (("H1", canonical(contract)) if child_status == "ACTIVE"
                         else ("TERMINAL", child_status))
                mass[child, Fraction(score, 2048)] += probability
            rows[action] = mass
        result = previous._row_key(rows)
    if work is not None:
        work.update(compiler.work)
    return result


def make_router(package, compiled, rule):
    previous = _previous()
    router = package["router"]
    if router["kind"] in {"LOCAL_H1", "LOCAL_H2"}:
        return previous.make_router(package, compiled, rule)
    if router["kind"] not in {"EFFECT_H2", "SHARED_EFFECT_H2"}:
        raise ValueError("unknown observation router")
    grouping = router["grouping"]
    literal = {(h, tuple(board)): cell for h, board, cell in router["labels"]}
    index_work = Counter(map_entries=len(literal))
    compiler = _compiler(rule, router["kind"] == "SHARED_EFFECT_H2")
    index_work.update(compiler.work)
    h1 = previous._h1_worker().h1_index(compiled, index_work)
    h2 = previous.h2_index(compiled, index_work)
    canonical = previous._h1_worker().canonical_contract
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
                child = h1.get(canonical(contract)) if status == "ACTIVE" else terminals.get((1, status))
                if child is None:
                    work["h2_missing_child_contracts"] += 1
                    return None
                mass[child, Fraction(score, 2048)] += probability
            rows[action] = mass
        return h2.get(previous._row_key(rows))

    def route(board, h, work):
        board = tuple(board)
        work["observations"] += 1
        before = Counter(compiler.work)
        if h == 1:
            work["h1_observation_contract_calls"] += 1
            result = h1.get(canonical(compiler.observation_contract(board)))
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
    if package["schema"] != "acfqp.observation_package.v74":
        raise ValueError("unknown observation package schema")
    contract = _previous()._module(
        ROOT / "src/acfqp/science/controlled_predictive_compositional_contract_v69.py",
        "acfqp_v74_worker_contract")
    compiled, rule = contract.load_model(package["kernel"])
    planner = contract._planner()
    load_seconds = perf_counter() - started
    load_counts = dict(kernel_cells=len(compiled.cells), kernel_rows=len(compiled.rows),
                       kernel_outcomes=sum(len(row) for row in compiled.rows.values()),
                       input_observations=len(data["observations"]), input_queries=len(data["queries"]))
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
                  load_counts=load_counts, index_seconds=index_seconds, index_counts=index_counts,
                  routing_seconds=routing_seconds, routing_counts=dict(work),
                  planning_seconds=planning_seconds, planning_counts=dict(planning_work),
                  ground_imports=imported, worker_seconds_before_write=perf_counter() - started)
    output.write_text(json.dumps(result, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.package, args.inputs, args.output)
