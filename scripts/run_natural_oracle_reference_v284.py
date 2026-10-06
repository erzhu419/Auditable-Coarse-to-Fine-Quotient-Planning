"""Run the frozen known-law H2 reference against retained V281 games."""
import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science.natural_oracle_reference_v284 import run_replication


def run(source_summary, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    trace, summary = output/'records.jsonl.gz', output/'summary.json'
    if trace.exists() or summary.exists():
        raise FileExistsError('V284 diagnostic receipts already exist')
    runtime = output/'runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    with gzip.open(trace, 'xt', encoding='utf-8') as stream:
        def emit(row):
            stream.write(json.dumps(row, separators=(',', ':'), allow_nan=False)+'\n')
            stream.flush()
        result = run_replication(source_summary, emit, runtime)
    result['output_bytes'] = dict(records_jsonl_gz=trace.stat().st_size)
    result['accounting']['timing_scope'] = 'Source loading, complete oracle games, gzip receipts and bootstrap; final summary serialization excluded'
    summary.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'], games=result['accounting']['new_online_games'],
        trace_bytes=trace.stat().st_size, summary_bytes=summary.stat().st_size)), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-summary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.source_summary, args.output)
