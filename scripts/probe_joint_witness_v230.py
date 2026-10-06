"""Exhibit feasible conflicting worlds in the retained oracle joint regions."""
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import joint_witness_v230 as primal
from acfqp.science import scoped_route_task_v228 as task
from scripts.run_conditioned_mechanisms_v205 import save
from scripts.probe_action_gap_v230 import INPUT, rows_for, plus, constraint


def run():
    output = ROOT/'reports/action_gap_v230'
    begun, work, evidence, cases = perf_counter(), Counter(), [], []
    sources = {row['life']: row for row in json.loads((INPUT/'source_evidence.json').read_text())}
    for record in json.loads((output/'records.json').read_text()):
        method = record['methods']['ORACLE_CUMULATIVE_POOL']
        if record['role'] != 'failure' or method['query_ready']:
            continue
        query = max(method['query_certificates'],
                    key=lambda q: F(method['query_certificates'][q]['regret_upper']))
        constraints = {op: list(values) for op, values in
                       method['constraints'][str(record['true_index'])].items()}
        _, laws, identities, metadata = task.world(record['life'])
        inherited = {}
        if record['case']['context'] == 'B':
            a_index = metadata['b_to_a'][record['true_index']]
            a_source = sources[record['life']]['a'][a_index]
            a_pool = a_source
            for previous in rows_for(record['life']):
                if previous['index'] < 27 and identities[previous['index']] == a_index:
                    a_pool = plus(a_pool, previous['member'])
            for op in constraints:
                if op != metadata['changed_operator']:
                    event = f'l{record["life"]}/A/pool{a_index}/{op}'
                    inherited[op] = [constraint(counts[op], 720, event)
                                     for counts in (a_source, a_pool)]
                    constraints[op].extend(inherited[op])
        case_evidence = []
        for policy in ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY'):
            result = primal.witness(record['case'], constraints, query, policy,
                                    laws[record['index']], work)
            row = dict(life=record['life'], index=record['index'],
                       method='ORACLE_CUMULATIVE_POOL', inherited_A_constraints=inherited,
                       **result)
            evidence.append(row)
            case_evidence.append(row)
        cases.append(dict(life=record['life'], index=record['index'], query=query,
            all_pure_policies_have_counterexample=all(row['found'] for row in case_evidence)))
        save(output/'witnesses.json', evidence)
        print(f'witness {record["life"]}:{record["index"]} {query} '
              f'{sum(row["found"] for row in case_evidence)}/4', flush=True)
    summary = dict(new_observations=0, attempted=len(evidence),
                   found=sum(row['found'] for row in evidence), cases=cases,
                   elapsed_seconds=perf_counter()-begun, work=work,
                   scope='pure query policies over the specified retained joint CS regions')
    save(output/'witness_summary.json', summary)
    for name in ('src/acfqp/science/joint_witness_v230.py', 'scripts/probe_joint_witness_v230.py'):
        destination = output/'witness_source_code'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    return summary


if __name__ == '__main__':
    run()
