"""Run the frozen active two-table contribution comparison on fresh sequences."""
import argparse
from acfqp.science.linear_contribution_run_v311 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.source_summary, args.output)
