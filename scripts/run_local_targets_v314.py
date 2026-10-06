"""Run the frozen V314 fixed-policy local target development experiment."""
import argparse
from pathlib import Path
from acfqp.science.local_target_run_v314 import run


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-summary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.source_summary,args.output)
