"""Route observations and plan using only exported compositional dynamics."""
from collections import Counter
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v69_contract_worker', ROOT/'src/acfqp/science/controlled_predictive_compositional_contract_v69.py')
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)


def run(model_path, inputs_path, output):
    started=perf_counter(); payload=json.loads(model_path.read_text()); data=json.loads(inputs_path.read_text())
    compiled,rule=module.load_model(payload)
    planner=module._planner()
    work=Counter();tick=perf_counter()
    routed=[module.route_observation(tuple(row['board']),row['horizon'],rule,compiled,work) for row in data['observations']]
    routing_seconds=perf_counter()-tick
    tick=perf_counter();full_payload=json.loads(model_path.with_name('FULL.model.json').read_text())
    full,_=module.load_model(full_payload);full_load_seconds=perf_counter()-tick
    tick=perf_counter()
    literal_index={(h,tuple(board)):state for h,board,state in full_payload['literal_boards']}
    full_routed=[literal_index[row['horizon'],tuple(row['board'])] for row in data['observations']]
    full_routing_seconds=perf_counter()-tick
    queries={}
    for name,value in data['queries'].items():
        solution=planner.plan(compiled,planner.Query(**value))
        queries[name]=dict(policy=solution.policy,values=solution.values,counts=solution.counts)
    imported=[name for name in sys.modules if name.startswith('acfqp.domains')]
    if imported:raise AssertionError(f'ground imported: {imported}')
    output.write_text(json.dumps(dict(routed=routed,full_routed=full_routed,routing_counts=dict(work),routing_seconds=routing_seconds,
        full_routing_seconds=full_routing_seconds,full_load_seconds=full_load_seconds,
        full_routing_counts=dict(index_entries=len(literal_index),observations=len(full_routed)),
        queries=queries,ground_imports=imported,worker_seconds_before_write=perf_counter()-started),allow_nan=False)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True);parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    run(args.model,args.inputs,args.output)
