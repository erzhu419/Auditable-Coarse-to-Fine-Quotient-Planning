#!/usr/bin/env python3
"""Run matched SOURCE/current-policy new-data adaptation after the same A1 critic."""
import argparse
from acfqp.science.policy_data_v306 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output)
