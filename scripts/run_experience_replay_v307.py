"""Run the fixed-budget retained old/new factual replay control."""
import argparse
from acfqp.science.experience_replay_v307 import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--a1-summary', required=True)
parser.add_argument('--current-summary', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
run(args.a1_summary, args.current_summary, args.output)
