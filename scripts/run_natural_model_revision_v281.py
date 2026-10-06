"""Run the frozen V281 natural-game model revision experiment once."""
import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.natural_model_revision_v281 import run_replication, RUNTIME


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    trace, summary = output / 'records.jsonl.gz', output / 'summary.json'
    if trace.exists() or summary.exists():
        raise FileExistsError('V281 receipts already exist')
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with gzip.open(trace, 'xt', encoding='utf-8') as stream:
        def emit(row):
            stream.write(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n')
            stream.flush()
        result = run_replication(emit, RUNTIME)
    result['output_bytes'] = dict(records_jsonl_gz=trace.stat().st_size)
    summary.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(status=result['status'], primary=result['summary']['primary_result'],
        trace_bytes=trace.stat().st_size, summary_bytes=summary.stat().st_size)), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
