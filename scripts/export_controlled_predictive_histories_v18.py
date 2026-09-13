"""Export three preregistered V18 histories and compare independent replay."""

import json
import gzip
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from acfqp.science.controlled_predictive_history_io_v13 import freeze_history_payload

base = Path.cwd()
source = base / 'reports/controlled_predictive_score_cache_v18.json.gz'
with gzip.open(source, 'rt') as handle:
    report = json.load(handle)
labels = {'v6_spawn_edge_rescue_2': 'spawn', 'v6_crossing_rescue_pair_3': 'crossing_risk',
          'v6_crossing_rescue_pair_2': 'crossing_goal'}
checks = []
for example in report['history_policy_examples']:
    label = labels[example['case_name']]
    artifact = base / f'reports/controlled_predictive_history_{label}_v18.json'
    replay = base / f'reports/controlled_predictive_history_{label}_replay_v18.json'
    traces = {name: example['traces'][name] for name in example['query_order']}
    started = perf_counter()
    payload = freeze_history_payload(example['queries'], traces, {
        'case_name': example['case_name'], 'sample_seed': example['sample_seed'],
        'method': example['method'], 'source_report': source.name,
        'source_experiment': 'V18', 'observation_stream': 'V15_EXPLICIT_BATCH_INDEX',
        'total_batch_cap': report['settings']['total_batch_cap'], 'samples_per_batch': 256,
    })
    payload['scope'] = 'Replay of retained histories under the fixed V15 batch observation stream.'
    with artifact.open('x') as handle:
        json.dump(payload, handle, separators=(',', ':'), allow_nan=False)
        handle.write('\n')
    export_seconds = perf_counter() - started
    run = subprocess.run([sys.executable, 'scripts/replay_controlled_predictive_history_v13.py',
        '--artifact', str(artifact), '--output', str(replay)], check=True, capture_output=True, text=True,
        env={**os.environ, 'PYTHONPATH': 'src'})
    result = json.loads(replay.read_text())
    expected = []
    terminals = [0]
    for name, trace in traces.items():
        def visit(node, prefix):
            history = prefix + [node['key']]
            if 'action' in node:
                expected.append({'query_name': name, 'history': history, 'action': node['action']})
            else:
                terminals[0] += 1
            for edge in node.get('children', []):
                visit(edge['node'], history)
        visit(trace, [])
    tests = {
        'declared_query_order_and_weights_equal': payload['query_order'] == example['query_order'] and payload['queries'] == example['queries'],
        'all_history_actions_equal_runtime_trace': result['decisions'] == expected,
        'terminal_histories_equal_runtime_trace': result['terminal_history_count'] == terminals[0],
        'root_actions_equal_runtime_trace': result['query_root_actions'] == {name: trace['action'] for name, trace in traces.items()},
        'replay_requests_no_new_observations': result['new_planning_observations'] == 0,
        'replay_stderr_empty': not run.stderr,
    }
    checks.append({'case_name': example['case_name'], 'sample_seed': example['sample_seed'],
        'artifact': artifact.name, 'artifact_bytes': artifact.stat().st_size,
        'replay': replay.name, 'query_count': len(traces), 'decision_history_count': len(expected),
        'terminal_history_count': terminals[0], 'export_seconds': export_seconds,
        'fresh_process_load_and_replay_seconds': result['load_and_replay_seconds'],
        'checks': tests, 'all_equal': all(tests.values())})
    print(json.dumps(checks[-1]))
summary = {'status': 'PASS' if all(row['all_equal'] for row in checks) else 'FAIL',
    'examples': checks, 'fresh_process_count': len(checks),
    'scope': 'Compare every retained history action with the original paid V18 tree. Reuse the V13 recorded-history format and loader; replay performs no acquisition or new-policy evaluation.'}
with (base / 'reports/controlled_predictive_history_replay_check_v18.json').open('x') as handle:
    json.dump(summary, handle, indent=2, allow_nan=False)
    handle.write('\n')
assert summary['status'] == 'PASS', summary
