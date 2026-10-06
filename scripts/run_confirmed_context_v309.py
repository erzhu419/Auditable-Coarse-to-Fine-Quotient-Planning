"""Run new five-stage confirmed-context adaptation and reuse sequences."""
import argparse
from acfqp.science.confirmed_context_run_v309 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
