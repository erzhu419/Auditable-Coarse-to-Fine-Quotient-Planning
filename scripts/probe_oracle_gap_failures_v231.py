"""Zero-draw exact countermodels for prespecified oracle lifecycle failures."""
from collections import Counter
from fractions import Fraction as F
import gzip
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

OUTPUT = ROOT/'reports/oracle_gap_lifecycle_v231'


def run():
    started, work, selected = perf_counter(), Counter(), {}
    for path in sorted(OUTPUT.glob('records_life_*.jsonl.gz')):
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                index = row['index']
                phase = 'late_B' if 42 <= index < 54 else ('A_RETURN' if index >= 54 else None)
                if phase is None or row['spent'] != 384 or row['terminal_plan']['query_ready']:
                    continue
                key = row['life'], row['arm'], phase, row['identity']
                if key not in selected:
                    selected[key] = row
    results, case_results = [], []
    for (life, arm, phase, identity), row in sorted(selected.items()):
        plan = row['terminal_plan']
        query = max(plan['query_certificates'],
                    key=lambda name: F(plan['query_certificates'][name]['regret_upper']))
        _, laws, _, _ = task.world(life)
        evidence = []
        for policy in ('WAIT', 'SHORT', 'DETOUR_RETURN', 'DETOUR_RETRY'):
            witness = primal.witness(row['case'], plan['joint_constraints'], query,
                                     policy, laws[row['index']], work)
            saved = dict(life=life, index=row['index'], arm=arm, phase=phase,
                         identity=identity, **witness)
            results.append(saved)
            evidence.append(saved)
        case_results.append(dict(life=life, index=row['index'], arm=arm, phase=phase,
            identity=identity, query=query, verified_policies=sum(r['found'] for r in evidence),
            no_pure_query_certificate=all(r['found'] for r in evidence)))
        save(OUTPUT/'countermodels.json', results)
        print(f'countermodel {life}:{row["index"]} {arm} {query} '
              f'{sum(r["found"] for r in evidence)}/4', flush=True)
    save(OUTPUT/'countermodels.json', results)
    summary = dict(selected_targets=len(selected), attempted=len(results),
        found=sum(row['found'] for row in results),
        no_pure_query_certificate=sum(row['no_pure_query_certificate'] for row in case_results),
        cases=case_results, new_observations=0, elapsed_seconds=perf_counter()-started,
        work=work, scope='specified joint confidence region and pure query grammar')
    save(OUTPUT/'countermodel_summary.json', summary)
    for name in ('scripts/probe_oracle_gap_failures_v231.py',
                 'src/acfqp/science/joint_witness_v230.py'):
        destination = OUTPUT/'countermodel_source_code'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    return summary


if __name__ == '__main__':
    run()
