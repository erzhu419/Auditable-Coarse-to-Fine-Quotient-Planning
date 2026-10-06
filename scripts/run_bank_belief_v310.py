"""Run fresh five-stage learning with selected-bank model beliefs."""
import argparse
from acfqp.science.bank_belief_run_v310 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
