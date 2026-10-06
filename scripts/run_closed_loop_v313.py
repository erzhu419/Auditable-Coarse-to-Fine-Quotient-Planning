"""Run the frozen two-round natural-game policy learning intervention."""
import argparse
from acfqp.science.closed_loop_run_v313 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output)
