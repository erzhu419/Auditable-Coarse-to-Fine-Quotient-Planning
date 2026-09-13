"""Load only the saved learner and kernel, with no ground-package initializer."""
from pathlib import Path
import argparse
import json
import sys
from time import perf_counter
import types
import torch

ROOT = Path(__file__).resolve().parents[1]
for name, path in [('acfqp', ROOT/'src/acfqp'), ('acfqp.science', ROOT/'src/acfqp/science')]:
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    sys.modules[name] = package
from acfqp.science.controlled_predictive_learned_model_v68 import load_model
from acfqp.science.controlled_predictive_quotient_v1 import Query, plan


def run(directory, inputs, output):
    started = perf_counter()
    torch.set_num_threads(1)
    model = load_model(directory)
    data = json.loads(inputs.read_text())
    encoded = model.batch_encode([tuple(c['board']) for c in data['cases']],
                                 [c['horizon'] for c in data['cases']])
    queries = {}
    for name, value in data['queries'].items():
        solution = plan(model.compiled, Query(**value))
        queries[name] = dict(policy=solution.policy, values=solution.values, counts=solution.counts)
    ground = [name for name in sys.modules if name.startswith('acfqp.domains')]
    if ground:
        raise AssertionError(f'Unexpected ground imports: {ground}')
    output.write_text(json.dumps(dict(encoded=encoded, queries=queries,
        inference_counts=model.inference_counts, ground_imports=ground,
        wall_seconds_before_write=perf_counter()-started), allow_nan=False)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.model, args.inputs, args.output)
