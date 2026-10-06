#!/usr/bin/env python3
"""Diagnose model-to-action conversion on the complete frozen V281 carrier."""
import argparse
import json
from pathlib import Path

from acfqp.science.natural_action_value_v283 import run_replay


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--source-summary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run_replay(args.input, args.source_summary, args.output)
    print(json.dumps(dict(status=result['status'], accounting=result['accounting'],
        summary=str((args.output/'summary.json').resolve()))), flush=True)
