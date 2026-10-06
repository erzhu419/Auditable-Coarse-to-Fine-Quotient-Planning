"""Build the four frozen fresh SOURCE parents for the V312 confirmation."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.fresh_source_v312 import DYNAMICS_CAPSULE, OUTPUT, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dynamics-capsule', type=Path, default=DYNAMICS_CAPSULE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    summary = run(args.dynamics_capsule, args.output)
    print(json.dumps(dict(event='fresh_source_complete', status=summary['status'],
        source_training_games=summary['accounting']['inherited_costs_per_arm']['SOURCE']['source_training_games'])),
        flush=True)


if __name__ == '__main__':
    main()
