#!/usr/bin/env python3
"""Confirm frozen V301 local risk on independent B training histories."""
import argparse
from acfqp.science.local_risk_v302 import run

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-summary',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
run(args.source_summary,args.output)
