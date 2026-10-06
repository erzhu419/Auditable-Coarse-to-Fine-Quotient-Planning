"""Run the frozen V315 reward/WIN component evaluation."""
import argparse
from pathlib import Path
from acfqp.science.component_target_run_v315 import run

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior-summary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.prior_summary,args.output)
