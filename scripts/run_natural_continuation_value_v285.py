"""Freeze V285 roots, or execute the independent continuation diagnostic."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science.natural_continuation_value_v285 import prepare, run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    selection = commands.add_parser('prepare')
    selection.add_argument('--source-summary', type=Path, required=True)
    selection.add_argument('--records', type=Path, required=True)
    selection.add_argument('--changed', type=Path, required=True)
    selection.add_argument('--output', type=Path, required=True)
    execution = commands.add_parser('run')
    execution.add_argument('--selection', type=Path, required=True)
    execution.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.source_summary, args.records, args.changed, args.output)
        print(f"Frozen {len(result['states'])} V285 roots")
    else:
        run(args.selection, args.output)
