#!/usr/bin/env python3
"""Run observed-context persistent A/B/A reward/risk learning."""
import argparse
from acfqp.science.context_continual_v305 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--history-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.history_summary,args.output)
