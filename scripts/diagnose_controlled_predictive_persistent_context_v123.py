"""Post-run explanation of V123's remaining identity failures; no rule selection."""
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'reports/controlled_predictive_persistent_context_v123'


def diagnose(directory=OUTPUT):
    started = perf_counter()
    run = json.loads((directory/'run.json').read_text())
    streams = []
    blocks_read = source_bytes = 0
    for stream in run['streams']:
        path = directory/f"life_{stream['life']}"/stream['query']/'blocks.jsonl.gz'
        source_bytes += path.stat().st_size
        switches, births, return_fours, phases = [], [], 0, stream['phases']
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                blocks_read += 1
                value = row['methods']['PERSISTENT']
                event = value['event']
                if row['phase'] == 'A_RETURN':
                    return_fours += value['fours']
                    if event['kind'] != 'updated':
                        switches.append(dict(end=row['phase_end'], kind=event['kind'],
                            previous=event['previous_module_id'], active=event['module_id'],
                            fours=event['block_fours'],
                            source_probability=value['source_probability']))
                if event['kind'] == 'created':
                    births.append(dict(phase=row['phase'], end=row['phase_end'],
                        fours=event['block_fours'], previous=event['previous_module_id'],
                        active=event['module_id'], pre_probability=value['pre_probability'],
                        raw_existing_scores=event['existing_log_scores'],
                        adjusted_existing_scores=event['adjusted_existing_log_scores'],
                        new_score=event['new_log_score']))
        b, a = (phases[p]['PERSISTENT']['final_router']['modules'] for p in ('B','A_RETURN'))
        source_n = a[0]['alpha']+a[0]['beta']-b[0]['alpha']-b[0]['beta']
        source_fours = a[0]['alpha']-b[0]['alpha']
        streams.append(dict(life=stream['life'], query=stream['query'],
            return_actual_four_fraction=return_fours/524288,
            return_source_assigned_ranks=source_n,
            return_source_assigned_four_fraction=source_fours/source_n if source_n else None,
            births=births, return_switches=switches,
            final_modules=[dict(id=m['id'], probability=m['alpha']/(m['alpha']+m['beta']),
                observations=m['alpha']+m['beta']-2) for m in a]))
    totals = {}
    for method in ('BASELINE','PERSISTENT'):
        values = [s['phases'][phase][method] for s in run['streams'] for phase in ('B','A_RETURN')]
        totals[method] = {key: sum(v[key] for v in values)
            for key in ('switches','creations','reactivations')}
    result = dict(scope='Post hoc description of all eight fixed streams; no new method or tuning.',
        totals=totals, streams=streams,
        costs=dict(retained_blocks_read=blocks_read, source_trace_bytes=source_bytes,
            new_environment_transitions=0, td_updates=0),
        seconds=perf_counter()-started)
    (directory/'posthoc_diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(totals=totals,seconds=result['seconds'])))
    return result


if __name__ == '__main__':
    diagnose()
