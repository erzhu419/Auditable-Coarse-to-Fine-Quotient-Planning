"""Run fresh A/B/A first-context adaptation and parameter reuse."""
import argparse
from acfqp.science.first_adapt_v308 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
