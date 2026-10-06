"""Confirm the frozen four-arm learner with new SOURCE value parents."""
import argparse
from acfqp.science.fresh_confirmation_run_v312 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
