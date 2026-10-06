import argparse
from acfqp.science.reward_targets_run_v321 import run

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-summary',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    run(args.source_summary,args.output)
