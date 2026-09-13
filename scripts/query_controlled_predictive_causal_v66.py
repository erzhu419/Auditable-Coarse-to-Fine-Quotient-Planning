"""Replan from saved symbolic transitions in a fresh process."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
# This pure module has no environment dependencies. Importing science.__init__
# instead would also import legacy board representations and the ground domain.
SPEC = importlib.util.spec_from_file_location('causal_pure_planner_v66',
    ROOT/'src/acfqp/science/controlled_predictive_quotient_v1.py')
RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNTIME
SPEC.loader.exec_module(RUNTIME)
Query, plan, evaluate_compiled_policy = RUNTIME.Query, RUNTIME.plan, RUNTIME.evaluate_compiled_policy


def load_model(payload):
    cells = {cell:RUNTIME.Cell(layer,status,()) for cell,layer,status in payload['cells']}
    rows = {(cell,action):tuple(RUNTIME.Outcome(p,target,reward) for p,target,reward in outcomes)
            for cell,action,outcomes in payload['rows']}
    return RUNTIME.CompiledModel(cells,rows,tuple(payload['roots']),{}, {})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--queries', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    started = perf_counter()
    model = load_model(json.loads(args.model.read_text()))
    queries = json.loads(args.queries.read_text())
    results = {}
    for name, parameters in queries.items():
        query = Query(**parameters)
        solution = plan(model, query)
        forecast = evaluate_compiled_policy(model, solution, query)
        results[name] = dict(policy=solution.policy, values=solution.values,
            planning_counts=solution.counts, prediction=asdict(forecast))
    ground_imports = sorted(name for name in sys.modules if name.startswith('acfqp.domains.'))
    if ground_imports:
        raise AssertionError('portable planner imported a ground domain')
    result = dict(schema='acfqp.causal_portable_query.v66', results=results,
        ground_domain_imports=ground_imports, ground_transition_calls=0,
        wall_seconds_before_serialization=perf_counter()-started)
    with args.output.open('x') as handle:
        json.dump(result, handle, separators=(',', ':'), allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
