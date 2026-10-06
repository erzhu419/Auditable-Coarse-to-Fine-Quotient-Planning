#!/usr/bin/env python3
"""Run fixed-fact SOURCE versus A1-history B adaptation controls."""
import argparse
from acfqp.science.history_control_v304 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output)
