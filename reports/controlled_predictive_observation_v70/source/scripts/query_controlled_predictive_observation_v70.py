"""Route observations through a saved index and query its saved abstract kernel."""
from collections import Counter
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]


def _load(filename, module_name):
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / "src/acfqp/science" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(package_path, inputs_path, output):
    started = perf_counter()
    package = json.loads(package_path.read_text())
    data = json.loads(inputs_path.read_text())
    if package["schema"] != "acfqp.observation_package.v70":
        raise ValueError("unknown observation package schema")
    contract = _load("controlled_predictive_compositional_contract_v69.py",
                     "acfqp_v70_worker_contract")
    compiled, _ = contract.load_model(package["kernel"])
    planner = contract._planner()
    load_seconds = perf_counter() - started
    load_counts = dict(kernel_cells=len(compiled.cells), kernel_rows=len(compiled.rows),
                       kernel_outcomes=sum(len(row) for row in compiled.rows.values()),
                       input_observations=len(data["observations"]),
                       input_queries=len(data["queries"]))

    router = package["router"]
    tick = perf_counter()
    if router["kind"] == "MAP":
        index = {(h, tuple(board)): cell for h, board, cell in router["labels"]}
        index_counts = dict(map_entries=len(index))
    elif router["kind"] == "DAG":
        dag = _load("controlled_predictive_observation_dag_v70.py",
                    "acfqp_v70_worker_dag")
        encoder = dag.Encoder.from_payload(router["data"])
        index_counts = dict(dag_nodes=len(router["data"]["nodes"]),
                            dag_roots=len(router["data"]["roots"]))
    else:
        raise ValueError("unknown observation router")
    index_seconds = perf_counter() - tick

    work = Counter()
    tick = perf_counter()
    routes = []
    for row in data["observations"]:
        board, h = tuple(row["board"]), row["horizon"]
        if router["kind"] == "MAP":
            result = index.get((h, board))
            work["observations"] += 1
            work["map_lookups"] += 1
            work["supported_observations" if result is not None else
                 "unsupported_observations"] += 1
        else:
            result = encoder.encode(board, h, work)
        routes.append(result)
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
